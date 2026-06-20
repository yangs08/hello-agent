from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Literal

from app.config import DB_PATH
from app.schemas import ImageAsset, MessageRecord, SessionSummary


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_type TEXT,
                storage_path TEXT NOT NULL,
                url TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        image_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(images)").fetchall()
        }
        if "url" not in image_columns:
            conn.execute("ALTER TABLE images ADD COLUMN url TEXT")
            conn.execute("UPDATE images SET url = '/images/' || id WHERE url IS NULL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL DEFAULT 'default',
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                content_type TEXT NOT NULL DEFAULT 'text',
                content_text TEXT NOT NULL DEFAULT '',
                url TEXT,
                image_analysis TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(messages)").fetchall()
        }
        if "session_id" not in columns:
            conn.execute(
                "ALTER TABLE messages ADD COLUMN session_id TEXT NOT NULL DEFAULT 'default'"
            )
            columns.add("session_id")
        if "content_type" not in columns:
            conn.execute("ALTER TABLE messages ADD COLUMN content_type TEXT NOT NULL DEFAULT 'text'")
            columns.add("content_type")
        if "content_text" not in columns:
            conn.execute("ALTER TABLE messages ADD COLUMN content_text TEXT NOT NULL DEFAULT ''")
            conn.execute("UPDATE messages SET content_text = content WHERE content_text = ''")
            columns.add("content_text")
        if "url" not in columns:
            conn.execute("ALTER TABLE messages ADD COLUMN url TEXT")
            columns.add("url")
        if "user_id" in columns:
            conn.execute(
                """
                CREATE TABLE messages_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL DEFAULT 'default',
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_type TEXT NOT NULL DEFAULT 'text',
                    content_text TEXT NOT NULL DEFAULT '',
                    url TEXT,
                    image_analysis TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT INTO messages_new (
                    id, session_id, role, content, content_type, content_text,
                    url, image_analysis, created_at
                )
                SELECT
                    id, session_id, role, content, content_type, content_text,
                    url, image_analysis, created_at
                FROM messages
                """
            )
            conn.execute("DROP TABLE messages")
            conn.execute("ALTER TABLE messages_new RENAME TO messages")


def create_image(
    session_id: str,
    filename: str,
    content_type: str | None,
    storage_path: str,
    size_bytes: int,
    url: str | None = None,
) -> ImageAsset:
    created_at = utc_now()
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO images (session_id, filename, content_type, storage_path, url, size_bytes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, filename, content_type, storage_path, url or "", size_bytes, created_at),
        )
        image_id = cursor.lastrowid
        image_url = url or f"/images/{image_id}"
        conn.execute(
            "UPDATE images SET url = ? WHERE id = ?",
            (image_url, image_id),
        )

    return ImageAsset(
        id=image_id,
        session_id=session_id,
        filename=filename,
        content_type=content_type,
        storage_path=storage_path,
        url=image_url,
        size_bytes=size_bytes,
        created_at=created_at,
    )


def append_message(
    session_id: str,
    role: Literal["user", "assistant"],
    content_text: str,
    content_type: Literal["text", "image", "mixed"] = "text",
    url: str | None = None,
    image_analysis: str | None = None,
) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO messages (
                session_id, role, content, content_type, content_text,
                url, image_analysis, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                role,
                content_text,
                content_type,
                content_text,
                url,
                image_analysis,
                utc_now(),
            ),
        )
        return cursor.lastrowid


def update_image_analysis_by_url(url: str, image_analysis: str) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE messages
            SET image_analysis = ?
            WHERE url = ? AND image_analysis IS NULL
            """,
            (image_analysis, url),
        )


def list_sessions() -> list[SessionSummary]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT session_id, COUNT(*) AS message_count, MAX(created_at) AS last_message_at
            FROM messages
            GROUP BY session_id
            ORDER BY last_message_at DESC
            """
        ).fetchall()

    return [
        SessionSummary(
            session_id=row["session_id"],
            message_count=row["message_count"],
            last_message_at=row["last_message_at"],
        )
        for row in rows
    ]


def list_messages(session_id: str) -> list[MessageRecord]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                m.id,
                m.session_id,
                m.role,
                m.content_type,
                m.content_text,
                m.url,
                i.filename AS image_filename,
                i.content_type AS image_content_type,
                i.storage_path AS image_storage_path,
                m.image_analysis,
                m.created_at
            FROM messages m
            LEFT JOIN images i ON i.url = m.url
            WHERE m.session_id = ?
            ORDER BY m.id ASC
            """,
            (session_id,),
        ).fetchall()

    return [
        MessageRecord(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content_type=row["content_type"],
            content_text=row["content_text"],
            url=row["url"],
            image_filename=row["image_filename"],
            image_content_type=row["image_content_type"],
            image_storage_path=row["image_storage_path"],
            image_analysis=row["image_analysis"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def get_image(image_id: int) -> ImageAsset | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, session_id, filename, content_type, storage_path, url, size_bytes, created_at
            FROM images
            WHERE id = ?
            """,
            (image_id,),
        ).fetchone()

    if not row:
        return None

    return ImageAsset(
        id=row["id"],
        session_id=row["session_id"],
        filename=row["filename"],
        content_type=row["content_type"],
        storage_path=row["storage_path"],
        url=row["url"],
        size_bytes=row["size_bytes"],
        created_at=row["created_at"],
    )


def get_image_by_url(url: str) -> ImageAsset | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, session_id, filename, content_type, storage_path, url, size_bytes, created_at
            FROM images
            WHERE url = ?
            """,
            (url,),
        ).fetchone()

    if not row:
        return None

    return ImageAsset(
        id=row["id"],
        session_id=row["session_id"],
        filename=row["filename"],
        content_type=row["content_type"],
        storage_path=row["storage_path"],
        url=row["url"],
        size_bytes=row["size_bytes"],
        created_at=row["created_at"],
    )

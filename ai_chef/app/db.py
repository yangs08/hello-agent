from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Literal

from app.config import DB_PATH
from app.schemas import ChefMemory


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                image_analysis TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                user_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def append_message(
    user_id: str,
    role: Literal["user", "assistant"],
    content: str,
    image_analysis: str | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO messages (user_id, role, content, image_analysis, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, role, content, image_analysis, utc_now()),
        )


def load_memory(user_id: str) -> ChefMemory:
    with connect() as conn:
        row = conn.execute(
            "SELECT data FROM memories WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if not row:
        return ChefMemory()

    try:
        return ChefMemory.model_validate_json(row["data"])
    except Exception:
        return ChefMemory()


def save_memory(user_id: str, memory: ChefMemory) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO memories (user_id, data, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                data = excluded.data,
                updated_at = excluded.updated_at
            """,
            (user_id, memory.model_dump_json(ensure_ascii=False), utc_now()),
        )


def recent_context(user_id: str, limit: int = 8) -> list[dict[str, str]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content, image_analysis
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    history: list[dict[str, str]] = []
    for row in reversed(rows):
        content = row["content"]
        if row["image_analysis"]:
            content = f"{content}\n图片分析：{row['image_analysis']}"
        history.append({"role": row["role"], "content": content})
    return history

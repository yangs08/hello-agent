from __future__ import annotations

import json
import base64
import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.config import (
    ALIYUN_OSS_ACCESS_KEY_ID,
    ALIYUN_OSS_ACCESS_KEY_SECRET,
    ALIYUN_OSS_BUCKET,
    ALIYUN_OSS_ENDPOINT,
    ALIYUN_OSS_OBJECT_PREFIX,
    ALIYUN_OSS_PUBLIC_BASE_URL,
    ALIYUN_OSS_ROLE_ARN,
    ALIYUN_OSS_SECURITY_TOKEN,
    ALIYUN_OSS_STS_DURATION_SECONDS,
    ALIYUN_OSS_STS_ENDPOINT,
    MAX_IMAGE_SIZE,
    STORAGE_BACKEND,
    UPLOAD_DIR,
)


@dataclass(frozen=True)
class StoredUpload:
    storage_path: str
    url: str | None = None


@dataclass(frozen=True)
class OssUploadToken:
    access_key_id: str
    access_key_secret: str
    security_token: str
    expiration: str
    policy: str
    signature: str
    bucket: str
    endpoint: str
    object_key: str
    url: str


def _safe_ext(filename: str) -> str:
    return Path(filename).suffix.lower()


def _object_key(filename: str) -> str:
    ext = _safe_ext(filename)
    prefix = ALIYUN_OSS_OBJECT_PREFIX.strip("/")
    object_name = f"{uuid4().hex}{ext}"
    return f"{prefix}/{object_name}" if prefix else object_name


def _oss_public_url(object_key: str) -> str:
    if ALIYUN_OSS_PUBLIC_BASE_URL:
        return f"{ALIYUN_OSS_PUBLIC_BASE_URL.rstrip('/')}/{object_key}"

    endpoint = ALIYUN_OSS_ENDPOINT.removeprefix("https://").removeprefix("http://")
    return f"https://{ALIYUN_OSS_BUCKET}.{endpoint}/{object_key}"


def _require_oss_config(require_role: bool = False) -> None:
    required = {
        "ALIYUN_OSS_ENDPOINT": ALIYUN_OSS_ENDPOINT,
        "ALIYUN_OSS_BUCKET": ALIYUN_OSS_BUCKET,
        "ALIYUN_OSS_ACCESS_KEY_ID": ALIYUN_OSS_ACCESS_KEY_ID,
        "ALIYUN_OSS_ACCESS_KEY_SECRET": ALIYUN_OSS_ACCESS_KEY_SECRET,
    }
    if require_role:
        required["ALIYUN_OSS_ROLE_ARN"] = ALIYUN_OSS_ROLE_ARN

    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"OSS 配置缺失：{', '.join(missing)}")


def create_oss_upload_token(filename: str) -> OssUploadToken:
    _require_oss_config(require_role=True)

    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdksts.request.v20150401.AssumeRoleRequest import AssumeRoleRequest
    except ImportError as exc:
        raise RuntimeError("请先安装 oss2 依赖：uv add oss2") from exc

    object_key = _object_key(filename)
    policy = {
        "Version": "1",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["oss:PutObject"],
                "Resource": [f"acs:oss:*:*:{ALIYUN_OSS_BUCKET}/{object_key}"],
            }
        ],
    }

    client = AcsClient(
        ALIYUN_OSS_ACCESS_KEY_ID,
        ALIYUN_OSS_ACCESS_KEY_SECRET,
        region_id="cn-hangzhou",
    )
    request = AssumeRoleRequest()
    request.set_accept_format("json")
    request.set_endpoint(ALIYUN_OSS_STS_ENDPOINT)
    request.set_RoleArn(ALIYUN_OSS_ROLE_ARN)
    request.set_RoleSessionName("ai-chef-upload")
    request.set_DurationSeconds(ALIYUN_OSS_STS_DURATION_SECONDS)
    request.set_Policy(json.dumps(policy))

    try:
        response = client.do_action_with_exception(request)
    except Exception as exc:
        raise RuntimeError(f"生成 OSS 临时上传凭证失败：{exc}") from exc
    data = json.loads(response.decode("utf-8"))
    credentials = data["Credentials"]
    post_policy = {
        "expiration": credentials["Expiration"],
        "conditions": [
            {"bucket": ALIYUN_OSS_BUCKET},
            ["eq", "$key", object_key],
            ["content-length-range", 1, MAX_IMAGE_SIZE],
        ],
    }
    encoded_policy = base64.b64encode(json.dumps(post_policy).encode("utf-8")).decode("utf-8")
    signature = base64.b64encode(
        hmac.new(
            credentials["AccessKeySecret"].encode("utf-8"),
            encoded_policy.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("utf-8")

    return OssUploadToken(
        access_key_id=credentials["AccessKeyId"],
        access_key_secret=credentials["AccessKeySecret"],
        security_token=credentials["SecurityToken"],
        expiration=credentials["Expiration"],
        policy=encoded_policy,
        signature=signature,
        bucket=ALIYUN_OSS_BUCKET,
        endpoint=ALIYUN_OSS_ENDPOINT,
        object_key=object_key,
        url=_oss_public_url(object_key),
    )


def _save_to_oss(filename: str, content: bytes, content_type: str | None) -> StoredUpload:
    try:
        import oss2
    except ImportError as exc:
        raise RuntimeError("请先安装 oss2 依赖：uv add oss2") from exc

    _require_oss_config()

    if ALIYUN_OSS_SECURITY_TOKEN:
        auth = oss2.StsAuth(
            ALIYUN_OSS_ACCESS_KEY_ID,
            ALIYUN_OSS_ACCESS_KEY_SECRET,
            ALIYUN_OSS_SECURITY_TOKEN,
        )
    else:
        auth = oss2.Auth(ALIYUN_OSS_ACCESS_KEY_ID, ALIYUN_OSS_ACCESS_KEY_SECRET)

    bucket = oss2.Bucket(auth, ALIYUN_OSS_ENDPOINT, ALIYUN_OSS_BUCKET)
    object_key = _object_key(filename)
    headers = {"Content-Type": content_type} if content_type else None
    bucket.put_object(object_key, content, headers=headers)

    return StoredUpload(storage_path=object_key, url=_oss_public_url(object_key))


def _save_to_local(filename: str, content: bytes) -> StoredUpload:
    ext = Path(filename).suffix.lower()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{uuid4().hex}{ext}"
    path.write_bytes(content)
    return StoredUpload(storage_path=str(path))


def save_upload(filename: str, content: bytes, content_type: str | None = None) -> StoredUpload:
    if STORAGE_BACKEND == "oss":
        return _save_to_oss(filename, content, content_type)
    return _save_to_local(filename, content)

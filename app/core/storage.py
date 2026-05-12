"""MinIO object storage helpers.

Aşama A için minimum altyapı:
- Bucket lazy oluşturulur ve public-read policy uygulanır.
- Backend proxy upload (presigned URL yok) — basit demo akışı.
- Public URL doğrudan `MINIO_PUBLIC_URL`/bucket/key.
"""

from __future__ import annotations

import json
from io import BytesIO
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.core.config import settings


_client: Optional[Minio] = None
_bucket_ready: bool = False


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
    return _client


def _public_policy(bucket: str) -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket}/*"],
                }
            ],
        }
    )


def ensure_bucket() -> None:
    """Bucket varsa atla, yoksa oluştur ve public-read policy uygula."""
    global _bucket_ready
    if _bucket_ready:
        return
    c = get_client()
    bucket = settings.MINIO_BUCKET
    if not c.bucket_exists(bucket):
        c.make_bucket(bucket)
    try:
        c.set_bucket_policy(bucket, _public_policy(bucket))
    except S3Error:
        # policy zaten setlenmişse veya yetki problemi varsa sessizce geç
        pass
    _bucket_ready = True


def upload_bytes(object_key: str, data: bytes, content_type: str) -> None:
    """Bytes'i bucket'a yazar."""
    ensure_bucket()
    c = get_client()
    c.put_object(
        settings.MINIO_BUCKET,
        object_key,
        BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def delete_object(object_key: str) -> None:
    """Object'i sil — yoksa sessizce geç."""
    c = get_client()
    try:
        c.remove_object(settings.MINIO_BUCKET, object_key)
    except S3Error:
        pass


def public_url(object_key: str) -> str:
    return (
        f"{settings.MINIO_PUBLIC_URL.rstrip('/')}/{settings.MINIO_BUCKET}/{object_key}"
    )

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.constants import ALLOWED_REPORT_EXTENSIONS

_CONTENT_TYPES = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _s3_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        region_name=settings.s3_region,
        config=Config(connect_timeout=3, read_timeout=5, retries={"max_attempts": 1}),
    )


def _validated_payload(upload: UploadFile) -> tuple[str, bytes]:
    filename = upload.filename or "upload.bin"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_REPORT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {suffix or '(none)'} is not allowed",
        )
    payload = upload.file.read(settings.max_upload_bytes + 1)
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(payload) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File exceeds the 5 MB upload limit",
        )
    return suffix, payload


def save_report_file(upload: UploadFile) -> str:
    backend = settings.storage_backend.lower()
    suffix, payload = _validated_payload(upload)
    stored_name = f"{uuid4().hex}{suffix}"

    if backend == "s3":
        if not settings.s3_bucket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3_BUCKET is not configured",
            )
        key = f"reports/{stored_name}"
        _s3_client().put_object(
            Bucket=settings.s3_bucket,
            Key=key,
            Body=payload,
            ContentType=_CONTENT_TYPES[suffix],
        )
        return key

    if backend != "local":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unknown STORAGE_BACKEND '{settings.storage_backend}'",
        )

    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    (upload_root / stored_name).write_bytes(payload)
    return f"/uploads/{stored_name}"


def public_file_url(stored: str) -> str:
    if stored.startswith(("http://", "https://", "/")):
        return stored
    if settings.storage_backend.lower() != "s3":
        return stored
    return _s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket, "Key": stored},
        ExpiresIn=settings.s3_presign_seconds,
    )

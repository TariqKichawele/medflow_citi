from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.constants import ALLOWED_REPORT_EXTENSIONS


def save_report_file(upload: UploadFile) -> str:
    if settings.storage_backend.lower() == "s3":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="S3 storage is not configured in this phase. Set STORAGE_BACKEND=local.",
        )
    if settings.storage_backend.lower() != "local":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unknown STORAGE_BACKEND '{settings.storage_backend}'",
        )

    filename = upload.filename or "upload.bin"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_REPORT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {suffix or '(none)'} is not allowed",
        )

    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{suffix}"
    dest = upload_root / stored_name
    dest.write_bytes(upload.file.read())
    return f"/uploads/{stored_name}"

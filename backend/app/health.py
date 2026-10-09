from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.services import storage

_OK = "ok"
_UNAVAILABLE = "unavailable"
_NOT_CONFIGURED = "not_configured"


def database_status(db: Session) -> str:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return _UNAVAILABLE
    return _OK


def s3_status() -> str:
    if settings.storage_backend.lower() != "s3" or not settings.s3_bucket:
        return _NOT_CONFIGURED
    try:
        storage._s3_client().head_bucket(Bucket=settings.s3_bucket)
    except Exception:
        return _UNAVAILABLE
    return _OK


def detail_status(database: str, s3: str) -> str:
    if database != _OK or s3 == _UNAVAILABLE:
        return "degraded"
    return _OK

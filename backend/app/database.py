import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings


class Base(DeclarativeBase):
    pass


# Bound the TCP handshake so an unreachable database fails promptly instead of
# hanging for the whole Lambda timeout. Applies to every session, including readiness.
_engine_kwargs: dict = {"pool_pre_ping": True}
if settings.database_url.startswith("postgresql"):
    _engine_kwargs["connect_args"] = {"connect_timeout": 3}
if os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    _engine_kwargs["poolclass"] = NullPool

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import User


def run_migrate(force_seed: bool = False) -> dict:
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    config = Config(str(root / "alembic.ini"))
    command.upgrade(config, "head")

    db = SessionLocal()
    try:
        existing = db.scalar(select(func.count()).select_from(User)) or 0
    finally:
        db.close()

    if existing and not force_seed:
        return {"migrated": True, "seeded": False, "users": int(existing)}

    os.environ["SEED_FORCE"] = "1"
    from app.seed import seed

    seed(reset=bool(force_seed))
    return {"migrated": True, "seeded": True}

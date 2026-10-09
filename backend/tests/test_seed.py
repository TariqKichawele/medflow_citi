import os
import shutil
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import StaticPool, create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from app.config import Settings, settings
from app.constants import ACTIVE_WORK_ORDER_STATUSES, EQUIPMENT_MAINTENANCE
from app.database import Base
from app.models import Equipment, Hospital, User, WorkOrder
from app.seed import apply_seed, assert_seed_target_allowed, main, open_engine, require_database_url


def _empty_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)()
    return engine, session


def _counts(db) -> tuple[int, int, int, int]:
    return tuple(
        db.scalar(select(func.count()).select_from(model)) or 0
        for model in (Hospital, User, Equipment, WorkOrder)
    )


def test_apply_seed_twice_does_not_duplicate() -> None:
    engine, db = _empty_session()
    try:
        assert apply_seed(db, reset=False) == "seeded"
        db.commit()
        first = _counts(db)
        assert all(count > 0 for count in first)

        hospital = db.scalar(select(Hospital).where(Hospital.name == "Halcyon Metro General"))
        assert hospital is not None
        hospital.name = "Renamed During Test"
        db.commit()

        assert apply_seed(db, reset=False) == "unchanged"
        db.commit()
        assert _counts(db) == first
        assert db.scalar(select(Hospital).where(Hospital.name == "Renamed During Test")) is not None
    finally:
        db.close()
        engine.dispose()


def test_apply_seed_reset_reloads_without_duplicating() -> None:
    engine, db = _empty_session()
    try:
        assert apply_seed(db, reset=False) == "seeded"
        db.commit()
        first = _counts(db)
        hospital = db.scalar(select(Hospital).where(Hospital.name == "Halcyon Metro General"))
        assert hospital is not None
        hospital.name = "Renamed During Test"
        db.commit()

        assert apply_seed(db, reset=True) == "reset"
        db.commit()
        assert _counts(db) == first
        assert db.scalar(select(Hospital).where(Hospital.name == "Renamed During Test")) is None
        assert db.scalar(select(Hospital).where(Hospital.name == "Halcyon Metro General")) is not None
    finally:
        db.close()
        engine.dispose()


def test_seed_data_covers_business_edge_cases() -> None:
    engine, db = _empty_session()
    try:
        apply_seed(db, reset=False)
        db.commit()

        low_charge = db.scalars(
            select(Equipment).where(
                Equipment.charge_level < 20,
                Equipment.status.in_(("available", "in_use")),
            )
        ).all()
        assert low_charge
        assert all(item.serial_number != "OFF-001" for item in low_charge)
        offline = db.scalar(select(Equipment).where(Equipment.serial_number == "OFF-001"))
        assert offline is not None
        assert offline.charge_level < 20
        assert offline.status == "offline"

        mismatches = db.execute(
            select(WorkOrder.id)
            .join(Equipment, Equipment.id == WorkOrder.equipment_id)
            .join(User, User.id == WorkOrder.technician_id)
            .where(
                WorkOrder.status.in_(ACTIVE_WORK_ORDER_STATUSES),
                User.facility_id != Equipment.facility_id,
            )
        ).all()
        assert mismatches

        devices = db.scalars(select(Equipment)).all()
        totals: dict[int, list[int]] = {}
        for device in devices:
            bucket = totals.setdefault(device.facility_id, [0, 0])
            bucket[0] += 1
            if device.status == EQUIPMENT_MAINTENANCE:
                bucket[1] += 1
        assert any(maintenance / total > 0.30 for total, maintenance in totals.values())

        statuses = set(db.scalars(select(WorkOrder.status)).all())
        assert statuses == {"pending", "in_progress", "completed", "failed"}
    finally:
        db.close()
        engine.dispose()


def test_require_database_url_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setattr("app.seed.dotenv_path", lambda: tmp_path / "missing.env")
    with pytest.raises(SystemExit, match="DATABASE_URL"):
        require_database_url()


def test_require_database_url_prefers_environment(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('DATABASE_URL="postgresql+psycopg://127.0.0.1:9/from-file"\n', encoding="utf-8")
    monkeypatch.setattr("app.seed.dotenv_path", lambda: env_file)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://127.0.0.1:9/from-env")
    assert require_database_url().endswith("/from-env")


def test_require_database_url_reads_dotenv_when_unset(monkeypatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("export DATABASE_URL=postgresql+psycopg://127.0.0.1:9/from-file\n", encoding="utf-8")
    monkeypatch.setattr("app.seed.dotenv_path", lambda: env_file)
    monkeypatch.setenv("DATABASE_URL", "")
    assert require_database_url().endswith("/from-file")


def test_refuses_nonlocal_database(monkeypatch) -> None:
    monkeypatch.delenv("SEED_FORCE", raising=False)
    monkeypatch.setattr(settings, "seed_force", "0")
    with pytest.raises(SystemExit, match="not local"):
        assert_seed_target_allowed("postgresql+psycopg://db.internal:5432/medflow")


def test_seed_force_allows_nonlocal_database(monkeypatch) -> None:
    monkeypatch.setenv("SEED_FORCE", "1")
    assert_seed_target_allowed("postgresql+psycopg://db.internal:5432/medflow")


def test_check_fails_when_database_is_unreachable() -> None:
    with pytest.raises(SystemExit, match="unreachable"):
        open_engine("postgresql+psycopg://127.0.0.1:1/medflow")


def test_main_check_requires_database_url(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setattr("app.seed.dotenv_path", lambda: tmp_path / "missing.env")
    with pytest.raises(SystemExit, match="DATABASE_URL"):
        main(["--check"])


def test_blank_env_values_keep_defaults(monkeypatch, tmp_path: Path) -> None:
    for name in ("DATABASE_URL", "JWT_EXPIRE_MINUTES", "S3_PRESIGN_SECONDS", "MAX_UPLOAD_BYTES"):
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=\nJWT_EXPIRE_MINUTES=\nS3_PRESIGN_SECONDS=\nMAX_UPLOAD_BYTES=\n",
        encoding="utf-8",
    )
    loaded = Settings(_env_file=env_file)
    assert loaded.database_url == Settings.model_fields["database_url"].default
    assert loaded.jwt_expire_minutes == 480
    assert loaded.s3_presign_seconds == 3600
    assert loaded.max_upload_bytes == 5 * 1024 * 1024


def test_quoted_database_url_is_read(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL='postgresql+psycopg://127.0.0.1:9/quoted'\n",
        encoding="utf-8",
    )
    loaded = Settings(_env_file=env_file)
    assert loaded.database_url.endswith("/quoted")


def test_seed_script_missing_database_url_from_other_directory(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    bash = shutil.which("bash")
    assert bash
    env = os.environ.copy()
    env["DATABASE_URL"] = ""
    result = subprocess.run(
        [bash, str(root / "bin" / "seed.sh")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr
    assert "postgresql" not in result.stderr.lower()


def test_setup_script_names_missing_python(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    bash = shutil.which("bash")
    assert bash
    env = os.environ.copy()
    env["PATH"] = str(tmp_path)
    result = subprocess.run(
        [bash, str(root / "bin" / "setup.sh")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode != 0
    assert "python3" in result.stderr


def test_shell_scripts_are_strict_and_contain_no_credentials() -> None:
    root = Path(__file__).resolve().parents[2]
    for name in ("setup.sh", "seed.sh"):
        text = (root / "bin" / name).read_text(encoding="utf-8")
        header = "\n".join(text.splitlines()[:4])
        assert "set -euo pipefail" in header
        assert "BASH_SOURCE" in text
        lowered = text.lower()
        assert "postgresql" not in lowered
        assert "://" not in text
        assert "password=" not in lowered
        assert "localhost" not in lowered

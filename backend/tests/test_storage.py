from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile

from app.config import settings
from app.services.storage import public_file_url, save_report_file


def _upload(name: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(data))


def test_local_save_returns_uploads_path(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "max_upload_bytes", 5 * 1024 * 1024)

    stored = save_report_file(_upload("notes.txt", b"pump checked"))

    assert stored.startswith("/uploads/")
    assert stored.endswith(".txt")
    assert (tmp_path / stored.removeprefix("/uploads/")).read_bytes() == b"pump checked"
    assert public_file_url(stored) == stored


def test_s3_save_puts_object_and_presigns(monkeypatch) -> None:
    calls: dict = {}

    class FakeS3:
        def put_object(self, **kwargs):
            calls["put"] = kwargs

        def generate_presigned_url(self, operation, Params, ExpiresIn):
            calls["presign"] = {"operation": operation, "Params": Params, "ExpiresIn": ExpiresIn}
            return "https://reports.example/signed"

    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_bucket", "medflow-reports")
    monkeypatch.setattr(settings, "s3_region", "us-east-1")
    monkeypatch.setattr(settings, "s3_presign_seconds", 900)
    monkeypatch.setattr(settings, "max_upload_bytes", 5 * 1024 * 1024)
    monkeypatch.setattr("app.services.storage._s3_client", lambda: FakeS3())

    stored = save_report_file(_upload("log.pdf", b"%PDF-1.4"))

    assert stored.startswith("reports/")
    assert stored.endswith(".pdf")
    assert calls["put"]["Bucket"] == "medflow-reports"
    assert calls["put"]["Key"] == stored
    assert calls["put"]["Body"] == b"%PDF-1.4"
    assert calls["put"]["ContentType"] == "application/pdf"
    assert public_file_url(stored) == "https://reports.example/signed"
    assert calls["presign"]["Params"] == {"Bucket": "medflow-reports", "Key": stored}
    assert calls["presign"]["ExpiresIn"] == 900


def test_rejects_oversize_and_unknown_type(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "max_upload_bytes", 4)

    with pytest.raises(HTTPException) as too_big:
        save_report_file(_upload("notes.txt", b"12345"))
    assert too_big.value.status_code == 413

    with pytest.raises(HTTPException) as bad_type:
        save_report_file(_upload("notes.exe", b"1234"))
    assert bad_type.value.status_code == 400

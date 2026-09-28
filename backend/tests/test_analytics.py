from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from tests.conftest import auth_header


def test_low_charge_excludes_offline(client: TestClient) -> None:
    headers = auth_header(client, "auditor@halcyon.health")
    response = client.get("/api/v1/analytics/low-charge", headers=headers)
    assert response.status_code == 200
    body = response.json()
    serials = {item["serial_number"] for item in body["items"]}
    assert "OFF-001" not in serials
    assert {"INF-001", "INF-002", "INF-003", "INF-005", "MON-005"} <= serials
    assert all(item["charge_level"] < 20 for item in body["items"])
    assert all(item["status"] in {"available", "in_use"} for item in body["items"])


def test_colocation_count(client: TestClient) -> None:
    headers = auth_header(client, "auditor@halcyon.health")
    response = client.get("/api/v1/analytics/colocation-discrepancies", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["serial_number"] == "INF-003"


def test_reliability_by_model(client: TestClient) -> None:
    headers = auth_header(client, "auditor@halcyon.health")
    response = client.get("/api/v1/analytics/reliability", headers=headers)
    assert response.status_code == 200
    by_model = {item["model"]: item for item in response.json()["items"]}
    assert by_model["Infusion Pump"]["completed"] == 3
    assert by_model["Infusion Pump"]["failed"] == 1
    assert by_model["Ventilator"]["completed"] == 1
    assert by_model["Ventilator"]["failed"] == 3
    assert by_model["Patient Monitor"]["completed"] == 2
    assert by_model["Patient Monitor"]["failed"] == 2
    assert by_model["Imaging Cart"]["completed"] == 4
    assert by_model["Imaging Cart"]["failed"] == 0
    assert by_model["Imaging Cart"]["completion_rate"] == 1.0


def test_maintenance_flags_threshold(client: TestClient) -> None:
    headers = auth_header(client, "auditor@halcyon.health")
    response = client.get("/api/v1/analytics/maintenance-flags", headers=headers)
    assert response.status_code == 200
    names = {item["hospital_name"] for item in response.json()["items"]}
    assert "Halcyon Metro General" in names
    assert "Halcyon Riverside Clinic" not in names


def test_reporting_lines(client: TestClient, db: Session) -> None:
    headers = auth_header(client, "auditor@halcyon.health")
    east = db.scalar(select(User).where(User.email == "supervisor.east@halcyon.health"))
    west = db.scalar(select(User).where(User.email == "supervisor.west@halcyon.health"))
    assert east is not None and west is not None

    east_resp = client.get(
        f"/api/v1/analytics/reporting-lines?supervisor_id={east.id}",
        headers=headers,
    )
    west_resp = client.get(
        f"/api/v1/analytics/reporting-lines?supervisor_id={west.id}",
        headers=headers,
    )
    assert east_resp.status_code == 200
    assert west_resp.status_code == 200
    assert east_resp.json()["items"][0]["technicians_with_active_orders"] == 2
    assert west_resp.json()["items"] == []

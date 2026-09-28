from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WorkOrder
from tests.conftest import auth_header


def test_technician_cannot_create_equipment(client: TestClient) -> None:
    headers = auth_header(client, "tech.metro@halcyon.health")
    response = client.post(
        "/api/v1/equipment",
        headers=headers,
        json={
            "serial_number": "INF-999",
            "model": "Infusion Pump",
            "status": "available",
            "charge_level": 50,
            "facility_id": 1,
        },
    )
    assert response.status_code == 403


def test_auditor_cannot_create_hospital(client: TestClient) -> None:
    headers = auth_header(client, "auditor@halcyon.health")
    response = client.post(
        "/api/v1/hospitals",
        headers=headers,
        json={
            "name": "Shadow Site",
            "location_region": "Midwest",
            "capacity": 10,
        },
    )
    assert response.status_code == 403


def test_admin_can_create_equipment(client: TestClient) -> None:
    headers = auth_header(client, "admin@halcyon.health")
    hospitals = client.get("/api/v1/hospitals", headers=headers)
    facility_id = hospitals.json()["items"][0]["id"]
    response = client.post(
        "/api/v1/equipment",
        headers=headers,
        json={
            "serial_number": "INF-999",
            "model": "Infusion Pump",
            "status": "available",
            "charge_level": 50,
            "facility_id": facility_id,
        },
    )
    assert response.status_code == 201
    assert response.json()["serial_number"] == "INF-999"


def test_technician_cannot_update_another_technicians_work_order(
    client: TestClient, db: Session
) -> None:
    metro_headers = auth_header(client, "tech.metro@halcyon.health")
    riverside_order = db.scalar(
        select(WorkOrder).where(WorkOrder.title == "Riverside ventilator check")
    )
    assert riverside_order is not None
    response = client.patch(
        f"/api/v1/work-orders/{riverside_order.id}",
        headers=metro_headers,
        json={"status": "completed"},
    )
    assert response.status_code == 403


def test_technician_can_advance_own_work_order(client: TestClient, db: Session) -> None:
    headers = auth_header(client, "tech.metro@halcyon.health")
    order = db.scalar(select(WorkOrder).where(WorkOrder.title == "Metro low-charge pump swap"))
    assert order is not None
    response = client.patch(
        f"/api/v1/work-orders/{order.id}",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_technician_cannot_reassign_work_order(client: TestClient, db: Session) -> None:
    headers = auth_header(client, "tech.metro@halcyon.health")
    order = db.scalar(select(WorkOrder).where(WorkOrder.title == "Metro low-charge pump swap"))
    assert order is not None
    response = client.patch(
        f"/api/v1/work-orders/{order.id}",
        headers=headers,
        json={"status": "in_progress", "technician_id": 1},
    )
    assert response.status_code == 403


def test_auditor_can_read_analytics(client: TestClient) -> None:
    headers = auth_header(client, "auditor@halcyon.health")
    response = client.get("/api/v1/analytics/summary", headers=headers)
    assert response.status_code == 200

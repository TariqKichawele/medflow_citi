import sqlalchemy.event as sa_event
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Equipment
from app.services.query import apply_sort, paginate
from tests.conftest import auth_header


def _get(client: TestClient, path: str, headers: dict[str, str], **params):
    response = client.get(path, headers=headers, params=params)
    return response


def _hospital_id(client: TestClient, headers: dict[str, str], name: str) -> int:
    response = _get(client, "/api/v1/hospitals", headers, search=name, page_size=20)
    assert response.status_code == 200, response.text
    matches = [row for row in response.json()["items"] if row["name"] == name]
    assert matches, response.json()
    return matches[0]["id"]


def test_equipment_default_page_is_stable(client: TestClient) -> None:
    headers = auth_header(client, "admin@halcyon.health")
    response = _get(client, "/api/v1/equipment", headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert body["total"] > body["page_size"]
    assert len(body["items"]) == body["page_size"]
    ids = [row["id"] for row in body["items"]]
    assert ids == sorted(ids)


def test_equipment_page_boundaries_do_not_overlap(client: TestClient) -> None:
    headers = auth_header(client, "admin@halcyon.health")
    first = _get(client, "/api/v1/equipment", headers, page=1, page_size=10).json()
    second = _get(client, "/api/v1/equipment", headers, page=2, page_size=10).json()
    last_page = (first["total"] + 9) // 10
    last = _get(client, "/api/v1/equipment", headers, page=last_page, page_size=10).json()
    beyond = _get(client, "/api/v1/equipment", headers, page=last_page + 1, page_size=10).json()

    assert len(first["items"]) == 10
    assert len(second["items"]) == 10
    assert first["total"] == second["total"] == last["total"] == beyond["total"]
    assert set(row["id"] for row in first["items"]).isdisjoint(row["id"] for row in second["items"])
    assert 0 < len(last["items"]) <= 10
    assert beyond["items"] == []


def test_equipment_sort_directions_are_global(client: TestClient) -> None:
    headers = auth_header(client, "admin@halcyon.health")
    everything = _get(client, "/api/v1/equipment", headers, page_size=100, sort_by="id", sort_dir="asc").json()
    ranked = sorted(everything["items"], key=lambda row: (-row["charge_level"], row["id"]))
    descending = _get(
        client,
        "/api/v1/equipment",
        headers,
        page=1,
        page_size=5,
        sort_by="charge_level",
        sort_dir="desc",
    ).json()
    ascending = _get(
        client,
        "/api/v1/equipment",
        headers,
        page=1,
        page_size=5,
        sort_by="charge_level",
        sort_dir="asc",
    ).json()

    assert [row["id"] for row in descending["items"]] == [row["id"] for row in ranked[:5]]
    assert descending["items"][0]["charge_level"] == max(row["charge_level"] for row in everything["items"])
    assert [row["charge_level"] for row in ascending["items"]] == sorted(
        row["charge_level"] for row in everything["items"]
    )[:5]


def test_equipment_filters_combine(client: TestClient) -> None:
    headers = auth_header(client, "admin@halcyon.health")
    metro_id = _hospital_id(client, headers, "Halcyon Metro General")
    desert_id = _hospital_id(client, headers, "Halcyon Desert Outpatient")

    by_status = _get(client, "/api/v1/equipment", headers, status="offline", page_size=100).json()
    assert by_status["total"] >= 1
    assert {row["status"] for row in by_status["items"]} == {"offline"}

    by_site = _get(client, "/api/v1/equipment", headers, facility_id=metro_id, page_size=100).json()
    assert by_site["total"] >= 1
    assert {row["facility_id"] for row in by_site["items"]} == {metro_id}

    by_serial = _get(client, "/api/v1/equipment", headers, search="INF-001", page_size=100).json()
    assert [row["serial_number"] for row in by_serial["items"]] == ["INF-001"]

    by_model = _get(client, "/api/v1/equipment", headers, search="ventilator", page_size=100).json()
    assert by_model["total"] >= 1
    assert all("ventilator" in row["model"].lower() or "ventilator" in row["serial_number"].lower() for row in by_model["items"])

    combined = _get(
        client,
        "/api/v1/equipment",
        headers,
        status="maintenance",
        facility_id=metro_id,
        search="Ventilator",
        page_size=100,
    ).json()
    serials = {row["serial_number"] for row in combined["items"]}
    assert serials == {"VNT-001", "VNT-002"}
    assert combined["total"] == 2

    excluded = _get(
        client,
        "/api/v1/equipment",
        headers,
        status="maintenance",
        facility_id=desert_id,
        search="Ventilator",
        page_size=100,
    ).json()
    assert excluded["total"] == 0
    assert excluded["items"] == []


def test_invalid_sort_and_page_size_are_rejected(client: TestClient) -> None:
    headers = auth_header(client, "admin@halcyon.health")
    bad_sort = _get(client, "/api/v1/equipment", headers, sort_by="hashed_password")
    assert bad_sort.status_code == 422
    bad_direction = _get(client, "/api/v1/equipment", headers, sort_by="id", sort_dir="sideways")
    assert bad_direction.status_code == 422
    too_big = _get(client, "/api/v1/equipment", headers, page_size=101)
    assert too_big.status_code == 422
    too_small = _get(client, "/api/v1/equipment", headers, page_size=0)
    assert too_small.status_code == 422
    still_there = _get(client, "/api/v1/equipment", headers, page_size=1)
    assert still_there.status_code == 200
    assert still_there.json()["total"] > 1


def test_technician_filters_stay_inside_role_scope(client: TestClient) -> None:
    admin_headers = auth_header(client, "admin@halcyon.health")
    tech_headers = auth_header(client, "tech.metro@halcyon.health")
    desert_id = _hospital_id(client, admin_headers, "Halcyon Desert Outpatient")
    me = client.get("/api/v1/auth/me", headers=tech_headers).json()

    scoped = _get(client, "/api/v1/equipment", tech_headers, page_size=100, status="available").json()
    assert scoped["total"] == len(scoped["items"])
    assert scoped["items"]
    assert all(row["status"] == "available" for row in scoped["items"])
    assert "INF-006" not in {row["serial_number"] for row in scoped["items"]}

    desert = _get(client, "/api/v1/equipment", tech_headers, facility_id=desert_id, page_size=100).json()
    assert desert["total"] == 0

    orders = _get(client, "/api/v1/work-orders", tech_headers, page_size=100, status="completed").json()
    assert orders["items"]
    assert all(row["technician_id"] == me["id"] for row in orders["items"])
    assert all(row["status"] == "completed" for row in orders["items"])
    assert "Riverside ventilator check" not in {row["title"] for row in orders["items"]}


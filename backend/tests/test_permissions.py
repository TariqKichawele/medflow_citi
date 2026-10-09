import ast
from pathlib import Path

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.main import app
from app.models import Equipment, Role, User, WorkOrder
from app.permissions import BUILTIN_ROLES, Permission
from tests.conftest import auth_header

ADMIN = "admin@halcyon.health"
TECH = "tech.metro@halcyon.health"
AUDITOR = "auditor@halcyon.health"
ROLES = (ADMIN, TECH, AUDITOR)

PUBLIC_PATHS = {"/api/v1/auth/login", "/health", "/health/ready"}


def _headers(client: TestClient) -> dict[str, dict[str, str]]:
    return {email: auth_header(client, email) for email in ROLES}


def _call(client: TestClient, headers: dict[str, str], method: str, path: str, **kwargs):
    return client.request(method, path, headers=headers, **kwargs)


def test_me_returns_permissions_resolved_from_the_role(client: TestClient) -> None:
    admin = client.get("/api/v1/auth/me", headers=auth_header(client, ADMIN))
    auditor = client.get("/api/v1/auth/me", headers=auth_header(client, AUDITOR))
    technician = client.get("/api/v1/auth/me", headers=auth_header(client, TECH))

    assert admin.status_code == 200
    assert "equipment:write" in admin.json()["permissions"]
    assert "equipment:read_assigned" not in admin.json()["permissions"]
    assert "user:manage" not in auditor.json()["permissions"]
    assert "user:read" in auditor.json()["permissions"]
    assert "work_order:status" in technician.json()["permissions"]
    assert "user:read" not in technician.json()["permissions"]
    assert "hospital:write" not in technician.json()["permissions"]


def test_builtin_roles_match_seeded_grants(db: Session) -> None:
    roles = list(db.scalars(select(Role)).all())
    stored = {}
    for role in roles:
        stored[role.name] = {grant.permission for grant in role.grants}
    assert set(stored) == set(BUILTIN_ROLES)
    for name, spec in BUILTIN_ROLES.items():
        assert stored[name] == {permission.value for permission in spec.permissions}


def test_each_role_against_each_permission_boundary(
    client: TestClient, db: Session, tmp_path, monkeypatch
) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "storage_backend", "local")
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    headers = _headers(client)
    facility_id = client.get("/api/v1/hospitals", headers=headers[ADMIN]).json()["items"][0]["id"]
    technician = db.scalar(select(User).where(User.email == TECH))
    assert technician is not None
    own_order = db.scalar(
        select(WorkOrder).where(
            WorkOrder.technician_id == technician.id,
            WorkOrder.status == "pending",
        )
    )
    other_order = db.scalar(select(WorkOrder).where(WorkOrder.technician_id != technician.id))
    assigned_ids = select(WorkOrder.equipment_id).where(WorkOrder.technician_id == technician.id)
    hidden_equipment = db.scalar(
        select(Equipment).where(
            Equipment.facility_id != technician.facility_id,
            Equipment.id.not_in(assigned_ids),
        )
    )
    assert own_order is not None
    assert other_order is not None
    assert hidden_equipment is not None
    equipment_id = db.scalar(select(Equipment.id))
    assert equipment_id is not None

    hospital_body = {"name": "Permission Site", "location_region": "Northeast", "capacity": 12}
    equipment_body = {
        "serial_number": "PERM-001",
        "model": "Infusion Pump",
        "status": "available",
        "charge_level": 80,
        "facility_id": facility_id,
    }
    order_body = {
        "title": "Permission order",
        "priority": "low",
        "status": "pending",
        "equipment_id": equipment_id,
        "technician_id": technician.id,
    }
    user_body = {
        "email": "perm.user@halcyon.health",
        "full_name": "Permission User",
        "role": "auditor",
        "password": "Medflow123!",
        "is_active": True,
    }
    role_body = {"name": "matrix_observer", "description": "Reads hospitals", "permissions": ["hospital:read"]}
    report_files = {"file": ("notes.txt", b"checked", "text/plain")}

    cases = [
        ("hospital:read", "GET", "/api/v1/hospitals", {}, {ADMIN: 200, TECH: 200, AUDITOR: 200}),
        ("hospital:write", "POST", "/api/v1/hospitals", {"json": hospital_body}, {ADMIN: 201, TECH: 403, AUDITOR: 403}),
        ("equipment:read", "GET", f"/api/v1/equipment/{hidden_equipment.id}", {}, {ADMIN: 200, TECH: 403, AUDITOR: 200}),
        ("equipment:read_assigned", "GET", "/api/v1/equipment", {}, {ADMIN: 200, TECH: 200, AUDITOR: 200}),
        ("equipment:write", "POST", "/api/v1/equipment", {"json": equipment_body}, {ADMIN: 201, TECH: 403, AUDITOR: 403}),
        ("work_order:read", "GET", f"/api/v1/work-orders/{other_order.id}", {}, {ADMIN: 200, TECH: 403, AUDITOR: 200}),
        (
            "work_order:read_assigned",
            "GET",
            f"/api/v1/work-orders/{own_order.id}",
            {},
            {ADMIN: 200, TECH: 200, AUDITOR: 200},
        ),
        ("work_order:write", "POST", "/api/v1/work-orders", {"json": order_body}, {ADMIN: 201, TECH: 403, AUDITOR: 403}),
        (
            "work_order:status",
            "PATCH",
            f"/api/v1/work-orders/{own_order.id}",
            {"json": {"status": "in_progress"}},
            {TECH: 200, ADMIN: 200, AUDITOR: 403},
        ),
        (
            "report:read",
            "GET",
            f"/api/v1/work-orders/{own_order.id}/reports",
            {},
            {ADMIN: 200, TECH: 200, AUDITOR: 200},
        ),
        (
            "report:upload",
            "POST",
            f"/api/v1/work-orders/{own_order.id}/reports",
            {"files": report_files},
            {ADMIN: 201, TECH: 201, AUDITOR: 403},
        ),
        ("analytics:read", "GET", "/api/v1/analytics/summary", {}, {ADMIN: 200, TECH: 200, AUDITOR: 200}),
        ("user:read", "GET", "/api/v1/users", {}, {ADMIN: 200, TECH: 403, AUDITOR: 200}),
        ("user:manage", "POST", "/api/v1/users", {"json": user_body}, {ADMIN: 201, TECH: 403, AUDITOR: 403}),
        ("role:read", "GET", "/api/v1/roles", {}, {ADMIN: 200, TECH: 403, AUDITOR: 403}),
        ("role:manage", "POST", "/api/v1/roles", {"json": role_body}, {ADMIN: 201, TECH: 403, AUDITOR: 403}),
        ("health:read", "GET", "/health/detail", {}, {ADMIN: 200, TECH: 403, AUDITOR: 403}),
    ]

    covered = {permission.value for permission in Permission}
    assert {case[0] for case in cases} == covered
    scope_denials = {"equipment:read": {TECH}, "work_order:read": {TECH}}

    for permission, method, path, options, expected in cases:
        for email, status_code in expected.items():
            response = _call(client, headers[email], method, path, **options)
            assert response.status_code == status_code, (
                f"{email} {method} {path}: {response.status_code} {response.text}"
            )
            if status_code != 403:
                continue
            detail = response.json()["detail"]
            if email in scope_denials.get(permission, set()):
                assert detail == "Insufficient permissions"
            else:
                assert permission in detail


def test_technician_can_read_own_profile_without_user_read(client: TestClient, db: Session) -> None:
    technician = db.scalar(select(User).where(User.email == TECH))
    assert technician is not None
    headers = auth_header(client, TECH)
    own = client.get(f"/api/v1/users/{technician.id}", headers=headers)
    other = client.get("/api/v1/users/1", headers=headers)
    assert own.status_code == 200
    if technician.id != 1:
        assert other.status_code == 403
        assert other.json()["detail"] == "Missing permission: user:read"


def test_new_role_is_data_and_applies_without_a_new_token(client: TestClient) -> None:
    admin = auth_header(client, ADMIN)
    created = client.post(
        "/api/v1/roles",
        headers=admin,
        json={
            "name": "intake_clerk",
            "description": "Reads hospitals only",
            "permissions": ["hospital:read"],
        },
    )
    assert created.status_code == 201, created.text
    role_id = created.json()["id"]
    assert created.json()["permissions"] == ["hospital:read"]

    user = client.post(
        "/api/v1/users",
        headers=admin,
        json={
            "email": "clerk@halcyon.health",
            "full_name": "Casey Clerk",
            "role": "intake_clerk",
            "password": "Medflow123!",
            "is_active": True,
        },
    )
    assert user.status_code == 201, user.text

    headers = auth_header(client, "clerk@halcyon.health")
    assert client.get("/api/v1/hospitals", headers=headers).status_code == 200
    denied = client.post(
        "/api/v1/hospitals",
        headers=headers,
        json={"name": "Blocked Site", "location_region": "West", "capacity": 5},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Missing permission: hospital:write"
    equipment = client.get("/api/v1/equipment", headers=headers)
    assert equipment.status_code == 403
    assert "equipment:read" in equipment.json()["detail"]
    orders = client.get("/api/v1/work-orders", headers=headers)
    assert orders.status_code == 403
    assert "work_order:read" in orders.json()["detail"]
    assert "work_order:read_assigned" in orders.json()["detail"]

    cleared = client.patch(f"/api/v1/roles/{role_id}", headers=admin, json={"permissions": []})
    assert cleared.status_code == 200
    assert cleared.json()["permissions"] == []
    again = client.get("/api/v1/hospitals", headers=headers)
    assert again.status_code == 403
    assert again.json()["detail"] == "Missing permission: hospital:read"


def test_every_business_endpoint_declares_authorization() -> None:
    missing: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if route.path in PUBLIC_PATHS or route.path in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}:
            continue
        if not _declares_authorization(route.dependant):
            methods = ",".join(sorted(route.methods or []))
            missing.append(f"{methods} {route.path}")
    assert missing == []


def test_endpoints_do_not_name_roles_or_permission_literals() -> None:
    root = Path(__file__).resolve().parents[1]
    files = list((root / "app" / "routers").glob("*.py"))
    files.append(root / "app" / "main.py")
    for path in files:
        source = path.read_text(encoding="utf-8")
        assert "require_roles" not in source
        assert "require_admin" not in source
        assert "ROLE_CLINICAL_ADMIN" not in source
        assert "ROLE_FIELD_TECHNICIAN" not in source
        assert "ROLE_AUDITOR" not in source
        assert "clinical_admin" not in source
        assert "field_technician" not in source
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert node.value not in {permission.value for permission in Permission}


def _declares_authorization(dependant) -> bool:
    call = getattr(dependant, "call", None)
    if call is get_current_user or getattr(call, "permission_dependency", False):
        return True
    return any(_declares_authorization(child) for child in getattr(dependant, "dependencies", ()))

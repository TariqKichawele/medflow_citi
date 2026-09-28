from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.constants import DEMO_PASSWORD
from app.models import User
from tests.conftest import auth_header, login


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_rejects_bad_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@halcyon.health", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_protected_route_requires_token(client: TestClient) -> None:
    response = client.get("/api/v1/equipment")
    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    headers = auth_header(client, "admin@halcyon.health")
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@halcyon.health"
    assert body["role"] == "clinical_admin"


def test_inactive_user_cannot_login(client: TestClient, db: Session) -> None:
    token = login(client, "admin@halcyon.health")
    from sqlalchemy import select

    user = db.scalar(select(User).where(User.email == "auditor@halcyon.health"))
    assert user is not None
    user.is_active = False
    db.commit()
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "auditor@halcyon.health", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 401
    assert token

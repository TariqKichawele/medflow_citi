from fastapi.testclient import TestClient

from app.config import settings
from app.deps import db_session
from app.main import app
from tests.conftest import auth_header


def test_health_is_liveness_only(client: TestClient) -> None:
    def _override():
        raise AssertionError("liveness check must not open a database session")
        yield

    app.dependency_overrides[db_session] = _override
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_when_database_is_reachable(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_503_when_database_is_unavailable(client: TestClient) -> None:
    class _Down:
        def execute(self, *_args, **_kwargs):
            raise RuntimeError("could not connect to db.internal:5432")

    def _override():
        yield _Down()

    app.dependency_overrides[db_session] = _override
    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "db.internal" not in response.text
    assert "5432" not in response.text


def test_public_health_endpoints_need_no_token(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
    assert client.get("/health/ready").status_code == 200
    assert client.get("/health/detail").status_code == 401

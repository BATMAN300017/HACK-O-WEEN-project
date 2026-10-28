import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_db
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("app.main.init_db", lambda: None)
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    def override_get_db():
        yield connection

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    connection.close()


def test_health_endpoint_starts_and_responds(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_user_endpoint_requires_authentication(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401

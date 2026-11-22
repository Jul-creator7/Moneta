from pathlib import Path
from secrets import token_hex

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "head")
    with TestClient(create_app(Settings(database_url=url, jwt_secret=token_hex(32)))) as test_client:
        yield test_client


def register(client, username="saver", email=None):
    return client.post(
        "/api/auth/register",
        json={"email": email or f"{username}@example.com", "username": username, "password": "safe-password"},
    )


def login(client, username="saver", password="safe-password"):
    return client.post("/api/auth/login", json={"email": f"{username}@example.com", "password": password})


def test_registration(client):
    response = register(client)
    assert response.status_code == 201
    assert response.json() == {"id": 1, "email": "saver@example.com", "username": "saver"}


def test_duplicate_email(client):
    assert register(client).status_code == 201
    assert register(client, "other", "SAVER@example.com").status_code == 409


def test_duplicate_username(client):
    assert register(client).status_code == 201
    assert register(client, "Saver", "other@example.com").status_code == 409


def test_login(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_invalid_password(client):
    register(client)
    assert login(client, password="incorrect").status_code == 401


def test_protected_endpoint(client):
    assert client.get("/api/users/me").status_code == 401
    assert client.get("/api/users/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_user_isolation(client):
    users = {name: register(client, name).json() for name in ("saver", "planner")}
    for name, expected in users.items():
        token = login(client, name).json()["access_token"]
        response = client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        assert response.json() == expected


def test_invalid_input_does_not_echo_password(client):
    response = client.post(
        "/api/auth/register", json={"email": "saver@example.com", "username": "saver", "password": "short"}
    )
    assert response.status_code == 422
    assert "short" not in response.text


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}

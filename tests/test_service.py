import os

import pytest
from fastapi.testclient import TestClient

from agent import credentials as creds_mod
from agent.service import app

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "Z7vQ9X2mP5kA8rT1yU4wS6xL0cV3bN8nM7qR2tW5yZ8=")

client = TestClient(app)


@pytest.fixture(autouse=True)
def init_store(tmp_path):
    db_path = str(tmp_path / "test.db")
    creds_mod.credential_store = None
    creds_mod.init_credential_store(db_path)
    yield
    store = creds_mod.credential_store
    if store is not None:
        store.close()
    creds_mod.credential_store = None


@pytest.fixture
def account_id() -> str:
    store = creds_mod.credential_store
    assert store is not None
    return store.create_account("testuser", "testpass", "testkey")


def _auth_headers(
    user_name="testuser", password="testpass", access_key="testkey"
) -> dict[str, str]:
    resp = client.post(
        "/auth/login", json={"user_name": user_name, "password": password, "access_key": access_key}
    )
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_login_creates_account_and_returns_token(init_store) -> None:
    store = creds_mod.credential_store
    assert store is not None
    store.create_account("testuser", "testpass", "testkey")
    headers = _auth_headers("testuser", "testpass", "testkey")
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["user_name"] == "testuser"


def test_login_invalid_credentials(init_store) -> None:
    store = creds_mod.credential_store
    assert store is not None
    store.create_account("testuser", "testpass", "testkey")
    resp = client.post(
        "/auth/login", json={"user_name": "testuser", "password": "wrong", "access_key": "testkey"}
    )
    assert resp.status_code == 401


def test_login_missing_account(init_store) -> None:
    resp = client.post(
        "/auth/login", json={"user_name": "nouser", "password": "nopass", "access_key": "nokey"}
    )
    assert resp.status_code == 401


def test_protected_route_no_token(init_store) -> None:
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_create_and_list_session(init_store, account_id: str) -> None:
    headers = _auth_headers("testuser", "testpass", "testkey")
    resp = client.post("/sessions", json={"label": "Chat 1"}, headers=headers)
    assert resp.status_code == 200
    thread_id = resp.json()["thread_id"]

    resp = client.get("/sessions", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["thread_id"] == thread_id


def test_delete_session(init_store, account_id: str) -> None:
    headers = _auth_headers("testuser", "testpass", "testkey")
    resp = client.post("/sessions", json={"label": "ToDelete"}, headers=headers)
    assert resp.status_code == 200
    thread_id = resp.json()["thread_id"]

    resp = client.delete(f"/sessions/{thread_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ended"

    resp = client.get("/sessions", headers=headers)
    assert len(resp.json()["sessions"]) == 0


def test_chat_requires_session(init_store, account_id: str) -> None:
    headers = _auth_headers("testuser", "testpass", "testkey")
    resp = client.post("/chat", json={"thread_id": "missing", "message": "hi"}, headers=headers)
    assert resp.status_code == 404

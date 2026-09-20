import pytest
from fastapi.testclient import TestClient

import agent.credentials as creds_mod
from agent.credentials import EncryptedCredentialStore
from agent.service import app

SERVICE_HEADERS = {"X-Service-Api-Key": "test-key"}


@pytest.fixture(autouse=True)
def fresh_store(tmp_path: pytest.TempPathFactory) -> EncryptedCredentialStore:
    db = str(tmp_path / "creds.db")
    creds_mod.credential_store = EncryptedCredentialStore(db)
    return creds_mod.credential_store


@pytest.fixture
def client(fresh_store: EncryptedCredentialStore) -> TestClient:
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_session_create_and_end(client: TestClient) -> None:
    resp = client.post(
        "/account/session",
        json={"thread_id": "t1", "user_name": "u", "password": "p", "access_key": "a"},
        headers=SERVICE_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "created"

    resp = client.post("/session/end", json={"thread_id": "t1"}, headers=SERVICE_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ended"


def test_chat_requires_session(client: TestClient) -> None:
    resp = client.post(
        "/chat",
        json={"thread_id": "missing", "message": "hi"},
        headers=SERVICE_HEADERS,
    )
    assert resp.status_code == 404

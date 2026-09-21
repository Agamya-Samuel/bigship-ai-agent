import os

import pytest

from agent import credentials as creds_mod
from agent.credentials import EncryptedCredentialStore, SessionNotFoundError

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-only")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "Z7vQ9X2mP5kA8rT1yU4wS6xL0cV3bN8nM7qR2tW5yZ8=")


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
def store() -> EncryptedCredentialStore:
    return creds_mod.credential_store


@pytest.fixture
def account_id(store: EncryptedCredentialStore) -> str:
    return store.create_account("u", "p", "a")


def test_create_and_get_session(store: EncryptedCredentialStore, account_id: str) -> None:
    store.create_session(account_id, "t1")
    client = store.get_or_create_client("t1")
    assert client is not None


def test_remove_session(store: EncryptedCredentialStore, account_id: str) -> None:
    store.create_session(account_id, "t1")
    store.delete_session("t1")
    with pytest.raises(SessionNotFoundError):
        store.get_or_create_client("t1")


def test_missing_session_raises(store: EncryptedCredentialStore) -> None:
    with pytest.raises(SessionNotFoundError):
        store.get_or_create_client("missing")


def test_login_verification(store: EncryptedCredentialStore) -> None:
    account_id = store.create_account("user1", "pass1", "key1")
    assert account_id is not None
    found_id = store.verify_login("user1", "pass1")
    assert found_id == account_id
    assert store.verify_login("user1", "wrong") is None
    assert store.verify_login("nouser", "pass1") is None


def test_list_sessions(store: EncryptedCredentialStore, account_id: str) -> None:
    store.create_session(account_id, "t1", "Session 1")
    store.create_session(account_id, "t2", "Session 2")
    sessions = store.get_sessions(account_id)
    assert len(sessions) == 2
    thread_ids = {s["thread_id"] for s in sessions}
    assert "t1" in thread_ids
    assert "t2" in thread_ids

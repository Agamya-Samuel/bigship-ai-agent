import pytest

import agent.credentials as creds_mod
from agent.credentials import EncryptedCredentialStore, SessionNotFoundError


@pytest.fixture
def store(tmp_path: pytest.TempPathFactory) -> EncryptedCredentialStore:
    db = str(tmp_path / "creds.db")
    creds_mod.credential_store = EncryptedCredentialStore(db)
    return creds_mod.credential_store


def test_create_and_get_session(store: EncryptedCredentialStore) -> None:
    store.create_session("t1", "u", "p", "a")
    client = store.get_or_create_client("t1")
    assert client is not None


def test_remove_session(store: EncryptedCredentialStore) -> None:
    store.create_session("t1", "u", "p", "a")
    store.delete_session("t1")
    with pytest.raises(SessionNotFoundError):
        store.get_or_create_client("t1")


def test_missing_session_raises(store: EncryptedCredentialStore) -> None:
    with pytest.raises(SessionNotFoundError):
        store.get_or_create_client("missing")

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
import time
from datetime import UTC, datetime
from typing import Any

import bcrypt as _bcrypt
from bigship_sdk import BigshipClient
from bigship_sdk.config import BigshipConfig
from cryptography.fernet import Fernet

from agent.config import settings


class SessionNotFoundError(Exception):
    pass


class EncryptionKeyMissingError(Exception):
    pass


class EncryptedCredentialStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._fernet = _make_fernet(settings.credential_encryption_key)
        self._client_cache: dict[str, BigshipClient] = {}
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_db()

    def _init_db(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                user_name TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                access_key_encrypted TEXT NOT NULL,
                password_encrypted TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                thread_id TEXT UNIQUE NOT NULL,
                label TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_used_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_account_id
                ON sessions(account_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_thread_id
                ON sessions(thread_id);
            """
        )
        self._conn.commit()

    def _encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except Exception as exc:
            raise ValueError("Failed to decrypt credential") from exc

    def _now(self) -> str:
        return datetime.now(UTC).isoformat(timespec="seconds")

    def _generate_id(self) -> str:
        return hashlib.sha256(os.urandom(16)).hexdigest()[:32]

    def create_account(self, user_name: str, password: str, access_key: str) -> str:
        password_hash = _hash_password(password)
        access_key_encrypted = self._encrypt(access_key)
        password_encrypted = self._encrypt(password)
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM accounts WHERE user_name = ?",
                (user_name,),
            ).fetchone()
            if row is None:
                account_id = self._generate_id()
                self._conn.execute(
                    "INSERT INTO accounts "
                    "(id, user_name, password_hash, access_key_encrypted, "
                    "password_encrypted) VALUES (?, ?, ?, ?, ?)",
                    (
                        account_id,
                        user_name,
                        password_hash,
                        access_key_encrypted,
                        password_encrypted,
                    ),
                )
            else:
                account_id = row["id"]
                self._conn.execute(
                    "UPDATE accounts SET password_hash = ?, "
                    "access_key_encrypted = ?, password_encrypted = ? "
                    "WHERE id = ?",
                    (password_hash, access_key_encrypted, password_encrypted, account_id),
                )
            self._conn.commit()
        self._evict_account_client(account_id)
        return account_id

    def verify_login(self, user_name: str, password: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, password_hash FROM accounts WHERE user_name = ?",
                (user_name,),
            ).fetchone()
        if row is None:
            return None
        if not _verify_password(password, row["password_hash"]):
            return None
        return str(row["id"])

    def get_account(self, account_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, user_name, created_at FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            raise SessionNotFoundError(f"Account not found: {account_id}")
        return dict(row)

    def create_session(self, account_id: str, thread_id: str, label: str = "") -> None:
        with self._lock:
            session_id = self._generate_id()
            self._conn.execute(
                "INSERT INTO sessions (id, account_id, thread_id, label) VALUES (?, ?, ?, ?)",
                (session_id, account_id, thread_id, label),
            )
            self._conn.commit()
        self._touch_session(thread_id)

    def get_sessions(self, account_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, thread_id, label, created_at, last_used_at "
                "FROM sessions WHERE account_id = ? ORDER BY last_used_at DESC",
                (account_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_session(self, thread_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT id, account_id, thread_id, label, created_at, "
                "last_used_at FROM sessions WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        return dict(row) if row else None

    def delete_session(self, thread_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM sessions WHERE thread_id = ?", (thread_id,))
            self._conn.commit()
        self._evict_thread_client(thread_id)

    def _evict_thread_client(self, thread_id: str) -> None:
        client = self._client_cache.pop(thread_id, None)
        if client is not None:
            self._close_client(client)

    def _evict_account_client(self, account_id: str) -> None:
        client = self._client_cache.pop(f"account:{account_id}", None)
        if client is not None:
            self._close_client(client)

    @staticmethod
    def _close_client(client: BigshipClient) -> None:
        try:
            client.close()
        except Exception:
            pass

    def _get_account_credentials(self, account_id: str) -> tuple[str, str, str]:
        with self._lock:
            row = self._conn.execute(
                "SELECT user_name, access_key_encrypted, password_encrypted "
                "FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            raise SessionNotFoundError(f"Account not found: {account_id}")
        user_name = str(row["user_name"])
        access_key = self._decrypt(row["access_key_encrypted"])
        password = self._decrypt(row["password_encrypted"])
        return user_name, access_key, password

    def get_or_create_client(self, thread_id: str) -> BigshipClient:
        with self._lock:
            cached = self._client_cache.get(thread_id)
        if cached is not None:
            self._touch_session(thread_id)
            return cached

        session = self.get_session(thread_id)
        if session is None:
            raise SessionNotFoundError(f"No active session for thread_id: {thread_id}")

        account_id = session["account_id"]
        user_name, access_key, password = self._get_account_credentials(account_id)
        client = BigshipClient(_bigship_config(user_name, password, access_key))

        with self._lock:
            existing = self._client_cache.get(thread_id)
            if existing is not None:
                self._close_client(client)
                client = existing
            else:
                self._client_cache[thread_id] = client
        self._touch_session(thread_id)
        return client

    def build_client_from_credentials(
        self, user_name: str, password: str, access_key: str
    ) -> BigshipClient:
        """Build a fresh BigshipClient from raw credentials (for login validation)."""
        return BigshipClient(_bigship_config(user_name, password, access_key))

    def _touch_session(self, thread_id: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE sessions SET last_used_at = ? WHERE thread_id = ?",
                (self._now(), thread_id),
            )
            self._conn.commit()

    def cleanup_stale_clients(self, max_idle_seconds: int = 1800) -> None:
        cutoff = time.time() - max_idle_seconds
        with self._lock:
            rows = self._conn.execute("SELECT thread_id, last_used_at FROM sessions").fetchall()
            to_evict: list[str] = []
            for row in rows:
                try:
                    last_used = datetime.fromisoformat(row["last_used_at"]).timestamp()
                except Exception:
                    continue
                if last_used < cutoff:
                    to_evict.append(row["thread_id"])
        for thread_id in to_evict:
            self._evict_thread_client(thread_id)

    def close(self) -> None:
        with self._lock:
            for client in self._client_cache.values():
                self._close_client(client)
            self._client_cache.clear()
        self._conn.close()


def _make_fernet(key: str) -> Fernet:
    if not key:
        raise EncryptionKeyMissingError("CREDENTIAL_ENCRYPTION_KEY is required")
    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise EncryptionKeyMissingError(
            "CREDENTIAL_ENCRYPTION_KEY must be a valid base64-encoded 32-byte key"
        ) from exc


def _hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:72]
    return _bcrypt.hashpw(pw_bytes, _bcrypt.gensalt()).decode()


def _verify_password(password: str, password_hash: str) -> bool:
    pw_bytes = password.encode("utf-8")[:72]
    try:
        return _bcrypt.checkpw(pw_bytes, password_hash.encode())
    except (ValueError, TypeError):
        return False


def _bigship_config(user_name: str, password: str, access_key: str) -> BigshipConfig:
    return BigshipConfig(
        base_url="https://api.bigship.direct",
        user_name=user_name,
        password=password,
        access_key=access_key,
    )


credential_store: EncryptedCredentialStore | None = None


def init_credential_store(db_path: str) -> EncryptedCredentialStore:
    global credential_store
    if credential_store is None:
        credential_store = EncryptedCredentialStore(db_path)
    return credential_store


def get_credential_store() -> EncryptedCredentialStore:
    if credential_store is None:
        raise RuntimeError("Credential store not initialized")
    return credential_store

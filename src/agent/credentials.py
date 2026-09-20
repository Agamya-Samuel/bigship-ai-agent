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


class SessionNotFoundError(Exception):
    pass


class EncryptionKeyMissingError(Exception):
    pass


def _hash_password(password: str) -> str:
    pw_bytes = password.encode()[:72]
    return _bcrypt.hashpw(pw_bytes, _bcrypt.gensalt()).decode()


def _verify_password(password: str, password_hash: str) -> bool:
    pw_bytes = password.encode()[:72]
    try:
        return _bcrypt.checkpw(pw_bytes, password_hash.encode())
    except (ValueError, TypeError):
        return False


def _get_fernet() -> Fernet:
    key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
    if not key:
        raise EncryptionKeyMissingError("CREDENTIAL_ENCRYPTION_KEY env var is required")
    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise EncryptionKeyMissingError(
            "CREDENTIAL_ENCRYPTION_KEY must be a valid base64-encoded 32-byte key"
        ) from exc


class EncryptedCredentialStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._fernet = _get_fernet()
        self._client_cache: dict[str, BigshipClient] = {}
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_db()
        self._last_touch: dict[str, float] = {}
        self._touch_interval = 60.0

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
        with self._lock:
            account_id = self._generate_id()
            password_hash = _hash_password(password)
            access_key_encrypted = self._encrypt(access_key)
            password_encrypted = self._encrypt(password)
            try:
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
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"Account with user_name '{user_name}' already exists") from exc
            self._conn.commit()
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

    def _get_account_id(self, user_name: str) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM accounts WHERE user_name = ?",
                (user_name,),
            ).fetchone()
        if row is None:
            raise SessionNotFoundError(f"Account not found: {user_name}")
        return str(row["id"])

    def _upsert_account(self, user_name: str, password: str, access_key: str) -> str:
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
                    "access_key_encrypted = ?, password_encrypted = ? WHERE id = ?",
                    (password_hash, access_key_encrypted, password_encrypted, account_id),
                )
            self._conn.commit()
        return account_id

    def create_session(self, thread_id: str, user_name: str, password: str, access_key: str) -> str:
        account_id = self._upsert_account(user_name, password, access_key)
        with self._lock:
            session_id = self._generate_id()
            self._conn.execute(
                "INSERT INTO sessions (id, account_id, thread_id, label) VALUES (?, ?, ?, ?)",
                (session_id, account_id, thread_id, ""),
            )
            self._conn.commit()
        self._touch_session(thread_id)
        return session_id

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
        self._evict_client(thread_id)

    def _evict_client(self, thread_id: str) -> None:
        client = self._client_cache.pop(thread_id, None)
        if client is not None:
            try:
                client.close()
            except Exception:
                pass

    def _get_account_credentials(self, account_id: str) -> tuple[str, str]:
        with self._lock:
            row = self._conn.execute(
                "SELECT access_key_encrypted, password_encrypted FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            raise SessionNotFoundError(f"Account not found: {account_id}")
        access_key = self._decrypt(row["access_key_encrypted"])
        password = self._decrypt(row["password_encrypted"])
        return access_key, password

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
        access_key, password = self._get_account_credentials(account_id)
        user_name = self._get_user_name(account_id)

        config = BigshipConfig(
            base_url="https://api.bigship.direct",
            user_name=user_name,
            password=password,
            access_key=access_key,
        )
        client = BigshipClient(config)

        with self._lock:
            self._client_cache[thread_id] = client
        self._touch_session(thread_id)
        return client

    def _get_user_name(self, account_id: str) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT user_name FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            raise SessionNotFoundError(f"Account not found: {account_id}")
        return str(row["user_name"])

    def _touch_session(self, thread_id: str) -> None:
        now = time.time()
        last_touch = self._last_touch.get(thread_id, 0.0)
        if now - last_touch < self._touch_interval:
            return
        self._last_touch[thread_id] = now
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
            to_evict = []
            for row in rows:
                try:
                    last_used = datetime.fromisoformat(row["last_used_at"]).timestamp()
                except Exception:
                    continue
                if last_used < cutoff:
                    to_evict.append(row["thread_id"])
        for thread_id in to_evict:
            self._evict_client(thread_id)

    def close(self) -> None:
        with self._lock:
            for client in self._client_cache.values():
                try:
                    client.close()
                except Exception:
                    pass
            self._client_cache.clear()
        self._conn.close()


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

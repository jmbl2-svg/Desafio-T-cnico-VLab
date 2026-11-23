"""Contas e sessões da interface web, persistidas em SQLite."""

import hashlib
import hmac
import secrets
import sqlite3
import time
from contextlib import closing
from pathlib import Path

SESSION_SECONDS = 8 * 60 * 60
COOKIE_NAME = "vlab_session"


class WebAuth:
    def __init__(self, data_dir: str):
        self.path = Path(data_dir) / "web_auth.sqlite3"

    def connect(self):
        db = sqlite3.connect(self.path)
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, salt BLOB NOT NULL, password_hash BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires_at INTEGER NOT NULL
            );
        """)
        return db

    @staticmethod
    def hash_password(password: str, salt: bytes) -> bytes:
        return hashlib.scrypt(password.encode(), salt=salt, n=2**15, r=8, p=1, maxmem=64 * 1024**2)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def register(self, username: str, password: str) -> bool:
        salt = secrets.token_bytes(16)
        with closing(self.connect()) as db, db:
            result = db.execute(
                "INSERT OR IGNORE INTO users VALUES (?, ?, ?)",
                (username, salt, self.hash_password(password, salt)),
            )
            return result.rowcount == 1

    def login(self, username: str, password: str) -> str | None:
        with closing(self.connect()) as db, db:
            row = db.execute(
                "SELECT salt, password_hash FROM users WHERE username = ?", (username,)
            ).fetchone()
            salt, expected = row or (bytes(16), bytes(64))
            supplied = self.hash_password(password, salt)
            if not hmac.compare_digest(supplied, expected) or row is None:
                return None
            token = secrets.token_urlsafe(32)
            now = int(time.time())
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
            db.execute(
                "INSERT INTO sessions VALUES (?, ?, ?)",
                (self.hash_token(token), username, now + SESSION_SECONDS),
            )
            return token

    def user_for(self, token: str) -> str | None:
        if not token:
            return None
        with closing(self.connect()) as db:
            row = db.execute(
                "SELECT username FROM sessions WHERE token_hash = ? AND expires_at > ?",
                (self.hash_token(token), int(time.time())),
            ).fetchone()
        return row[0] if row else None

    def logout(self, token: str) -> None:
        with closing(self.connect()) as db, db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (self.hash_token(token),))

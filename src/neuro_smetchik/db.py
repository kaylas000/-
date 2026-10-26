"""Хранилище: SQLite для MVP, схема совместима с PostgreSQL 15+ (ТЗ 4.3)."""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .config import settings
from .models import utcnow

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

ROLE_SEED = [
    ("client", "Клиент — чтение своих смет", '["estimate:read", "request:create"]'),
    ("estimator", "Сметчик — создание и правка смет", '["estimate:read", "estimate:write", "estimate:approve", "request:create", "catalog:read"]'),
    ("manager", "Руководитель — четырёх глаз, метрики", '["estimate:read", "estimate:approve:second", "metrics:read", "audit:read"]'),
    ("admin", "Администратор — полный доступ", '["*"]'),
]

USER_SEED = [
    ("u-001", "ivanov", "Иванов И.И. (сметчик)", "estimator", 0),
    ("u-002", "petrova", "Петрова А.С. (руководитель)", "manager", 1),
    ("u-003", "admin", "Администратор", "admin", 1),
    ("u-004", "client", "Клиент", "client", 0),
]


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or settings.db_path)
        self._write_lock = threading.RLock()
        self._local = threading.local()
        self._local.in_tx = False

    def connect(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        with self._write_lock:
            self._local.in_tx = True
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                self._local.in_tx = False

    def execute(self, sql: str, params: tuple | list = ()) -> list[sqlite3.Row]:
        conn = self.connect()
        # Флаг транзакции привязан к потоку: TestClient работает в отдельном потоке,
        # и его BEGIN IMMEDIATE не должен блокировать commit в основном потоке.
        in_tx = getattr(self._local, "in_tx", False)
        try:
            cur = conn.execute(sql, params)
            if not in_tx:
                conn.commit()
            return cur.fetchall()
        except Exception:
            if not in_tx:
                conn.rollback()
            raise

    def one(self, sql: str, params: tuple | list = ()) -> dict[str, Any] | None:
        rows = self.execute(sql, params)
        return dict(rows[0]) if rows else None

    def all(self, sql: str, params: tuple | list = ()) -> list[dict[str, Any]]:
        return [dict(r) for r in self.execute(sql, params)]

    def insert(self, table: str, values: dict[str, Any]) -> None:
        cols = ", ".join(values)
        placeholders = ", ".join("?" for _ in values)
        self.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", tuple(values.values()))

    def init_schema(self) -> None:
        conn = self.connect()
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
        with self.transaction() as tx:
            for role, desc, perms in ROLE_SEED:
                tx.execute("INSERT OR IGNORE INTO roles(role, description, permissions) VALUES (?,?,?)", (role, desc, perms))
            for uid, username, display, role, mfa in USER_SEED:
                tx.execute(
                    "INSERT OR IGNORE INTO users(id, username, display_name, role, mfa_enabled, active, created_at) "
                    "VALUES (?,?,?,?,?,1,?)", (uid, username, display, role, mfa, utcnow()),
                )


db = Database()

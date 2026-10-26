"""Фикстуры: изолированная тестовая БД, локальный контур, TestClient."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
TEST_DB = ROOT / "data" / "test_neuro_smetchik.db"
os.environ["DB_PATH"] = str(TEST_DB)
os.environ["APP_ENV"] = "test"
os.environ["LLM_ENABLED"] = "false"
os.environ["AUDIT_ENABLED"] = "true"

for suffix in ("", "-wal", "-shm"):
    Path(str(TEST_DB) + suffix).unlink(missing_ok=True)

from neuro_smetchik.scripts_init import ensure_initialized  # noqa: E402

ensure_initialized()


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from neuro_smetchik.api import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def estimator_headers():
    return {"X-User": "ivanov", "X-Role": "estimator", "X-MFA": "0"}


@pytest.fixture
def manager_headers():
    return {"X-User": "petrova", "X-Role": "manager", "X-MFA": "1"}


@pytest.fixture
def sample_estimate(client, estimator_headers):
    r = client.post("/api/v1/requests", headers=estimator_headers,
                    json={"text": "Ванная 9 м²: плитка на стены, замена сантехники", "client": "ООО Тест"})
    assert r.status_code == 200, r.text
    return r.json()

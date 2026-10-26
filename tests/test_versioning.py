"""Integration: immutable-версии, Revision Service, four eyes, Prompt Version Control."""
from __future__ import annotations

import sqlite3

import pytest

from neuro_smetchik.db import db
from neuro_smetchik.prompts import resolve
from neuro_smetchik.security import verify_audit_chain


def test_positions_and_versions_are_immutable(client, sample_estimate):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE smeta_positions SET name='подмена' WHERE id=?", (sample_estimate["positions"][0]["id"],))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM smeta_versions WHERE smeta_id=?", (sample_estimate["id"],))


def test_audit_log_is_append_only_and_chain_valid():
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM security_audit_log WHERE id>0")
    ok, length = verify_audit_chain()
    assert ok and length > 0


def test_revision_creates_new_version_and_diff(client, sample_estimate):
    sid = sample_estimate["id"]
    pid = sample_estimate["positions"][0]["id"]
    r = client.post(f"/api/v1/estimates/{sid}/revisions", json={"operations": [
        {"op": "update", "position_id": pid, "field": "quantity", "value": "2.5"},
        {"op": "add", "catalog_id": "CAT-007", "quantity": "1"},
    ], "reason": "тест"})
    assert r.status_code == 200, r.text
    est = r.json()
    assert est["version_no"] == sample_estimate["version_no"] + 1
    assert est["checksum"] != sample_estimate["checksum"]
    assert est["totals"]["verification"] == "ok"
    assert all(op["ok"] for op in est["applied_operations"])
    d = client.get(f"/api/v1/estimates/{sid}/diff?from_version=1&to_version=2").json()
    assert d["added"] and d["changed"] and d["totals"]["delta"] != "0"


def test_unknown_catalog_id_cannot_be_added(client, sample_estimate):
    sid = sample_estimate["id"]
    r = client.post(f"/api/v1/estimates/{sid}/revisions", json={"operations": [
        {"op": "add", "catalog_id": "CAT-HALLUCINATED", "quantity": 1}]})
    assert r.status_code == 200
    assert r.json()["applied_operations"][0]["ok"] is False


def test_four_eyes_approval_requires_manager_with_mfa(client, estimator_headers, manager_headers):
    est = client.post("/api/v1/requests", headers=estimator_headers,
                      json={"text": "Коммерческое помещение 900 м² под ключ: демонтаж, штукатурка, вентиляция, электрика, стяжка"}).json()
    sid = est["id"]
    first = client.post(f"/api/v1/estimates/{sid}/approve", headers=estimator_headers)
    assert first.json()["status"] == "pending_second_approval"
    no_mfa = client.post(f"/api/v1/estimates/{sid}/approve",
                         headers={**manager_headers, "X-MFA": "0"})
    assert no_mfa.status_code == 403
    second = client.post(f"/api/v1/estimates/{sid}/approve", headers=manager_headers)
    assert second.json()["status"] == "approved"
    assert client.get(f"/api/v1/estimates/{sid}").json()["second_approver"] == "petrova"


def test_prompt_rollback_without_deploy(client, manager_headers):
    before = client.get("/api/v1/prompts").json()["active"]["parser"]
    r = client.post("/api/v1/prompts", headers=manager_headers, json={
        "service": "parser", "author": "manager", "activate": True,
        "body": "Тестовый промпт версии для проверки отката без деплоя кода. Отвечай JSON по схеме."})
    assert r.status_code == 200
    new = r.json()["version"]
    assert client.get("/api/v1/prompts").json()["active"]["parser"] == new
    back = client.post("/api/v1/prompts/activate", headers=manager_headers,
                       json={"service": "parser", "version": before})
    assert back.status_code == 200
    assert resolve("parser", "trace-fixed").version == before

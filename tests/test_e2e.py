"""E2E: полный пользовательский сценарий 3.1 + циклы обратной связи."""
from __future__ import annotations

from neuro_smetchik.calculation import verify_independent
from neuro_smetchik.loops import evaluate_golden
from neuro_smetchik.models import EstimateTotals
from neuro_smetchik.repository import load_estimate
from neuro_smetchik.revision import _to_positions


def test_full_user_flow(client, estimator_headers, manager_headers):
    # 1. Запрос с неполными данными -> Clarification Loop
    r = client.post("/api/v1/requests", headers=estimator_headers,
                    json={"text": "Хотим отремонтировать кухню, плитка на пол и покраска стен, площадь не знаем",
                          "client": "ООО «Заказчик»"})
    assert r.status_code == 200
    draft = r.json()
    assert draft["status"] == "needs_clarification"
    assert draft["questions"] and draft["questions"][0]["field"] == "area_m2"
    assert draft["clarification_session_id"]
    assert draft["totals"]["verification"] == "ok"

    # 2. Ответ на уточнение -> новая версия с актуальной площадью
    sid = draft["clarification_session_id"]
    a = client.post(f"/api/v1/clarification/{sid}/answer", headers=estimator_headers,
                    json={"answer": "22 м²"})
    assert a.status_code == 200 and a.json()["status"] == "completed"
    est = a.json()["estimate"]
    assert est["version_no"] == 2 and est["params"]["area_m2"] == 22.0

    # 3. Проверка человеком + правки (Revision Loop)
    changed = client.post(f"/api/v1/estimates/{est['id']}/revisions", headers=estimator_headers,
                          json={"operations": [{"op": "update", "position_id": est["positions"][0]["id"],
                                                "field": "quantity", "value": "4"}],
                                "reason": "Уточнение объёма сметчиком"})
    assert changed.status_code == 200
    approved_draft = changed.json()
    assert approved_draft["version_no"] == 3
    positions, mapping = _to_positions(approved_draft)
    assert mapping[approved_draft["positions"][0]["id"]].quantity == 4

    # 4. Утверждение (ниже порога — одна подпись)
    ap = client.post(f"/api/v1/estimates/{est['id']}/approve", headers=estimator_headers)
    assert ap.status_code == 200 and ap.json()["status"] == "approved"

    # 5. Документы
    for fmt in ("xlsx", "pdf", "csv"):
        assert client.get(f"/api/v1/estimates/{est['id']}/documents/{fmt}").status_code == 200

    # 6. Обратные связи
    assert client.post(f"/api/v1/estimates/{est['id']}/feedback", headers=estimator_headers,
                       json={"rating": 5, "comment": "всё ок"}).status_code == 200
    assert client.post(f"/api/v1/estimates/{est['id']}/plan-fact", headers=estimator_headers,
                       json={"fact_total": "100000"}).status_code == 200
    assert client.post("/api/v1/admin/drift", headers=manager_headers).status_code == 200
    assert client.post("/api/v1/admin/freshness", headers=manager_headers).status_code == 200

    # 7. Трассировка и аудит
    tr = client.get(f"/api/v1/admin/trace/{est['trace_id']}")
    assert tr.status_code == 200 and tr.json()["step_count"] > 0
    assert client.get("/api/v1/admin/audit", headers=manager_headers).json()["chain_valid"]


def test_golden_acceptance_criteria():
    report = evaluate_golden()
    assert report["total"] >= 100
    assert report["parser_accuracy"] >= 0.90
    assert report["matching_top1_accuracy"] >= 0.85
    assert report["auto_precision"] >= 0.85
    assert report["search_latency_p95_ms"] <= 500
    assert report["pass"]


def test_calculations_independent_recheck_on_persisted_version(client, sample_estimate):
    est = load_estimate(sample_estimate["id"])
    positions, _ = _to_positions(est)
    totals = EstimateTotals(
        subtotal=__import__("decimal").Decimal(est["totals"]["subtotal"]),
        overhead=__import__("decimal").Decimal(est["totals"]["overhead"]),
        profit=__import__("decimal").Decimal(est["totals"]["profit"]),
        vat=__import__("decimal").Decimal(est["totals"]["vat"]),
        grand_total=__import__("decimal").Decimal(est["totals"]["grand_total"]),
    )
    assert verify_independent(positions, totals)

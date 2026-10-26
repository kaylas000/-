"""Циклы обратной связи (ТЗ 3.3): Feedback / Model Drift / Plan-Fact / Data Freshness."""
from __future__ import annotations

import statistics
import uuid
from decimal import Decimal
from typing import Any

from .catalog import get_catalog
from .config import settings
from .db import db
from .matching import match_query
from .models import ParsedRequest, dumps, loads, utcnow
from .notifications import notify
from .parser_service import deterministic_parse
from .repository import log_step
from .security import audit, verify_audit_chain

BASELINE_KEY = "baseline-golden-accuracy"


def evaluate_golden(*, limit: int | None = None, trace_id: str = "golden-eval") -> dict[str, Any]:
    """Регрессионное тестирование качества на фиксированном golden test set (ТЗ 8.5)."""
    rows = db.all("SELECT * FROM golden_examples ORDER BY id" + (" LIMIT ?" if limit else ""),
                  (limit,) if limit else ())
    if not rows:
        return {"error": "golden_examples пуст: выполните scripts/init_db.py"}
    parsed_ok = 0
    matched_ok = 0
    auto_total = 0
    auto_correct = 0
    probe_correct = 0
    probe_total = 0
    search_latencies: list[float] = []
    failures: list[dict[str, Any]] = []
    for row in rows:
        expected_params = loads(row["expected_params"], {})
        expected_ids = set(loads(row["expected_catalog_ids"], []))
        parsed = ParsedRequest.model_validate(deterministic_parse(row["query"]))
        params_correct = (
            (not expected_params.get("room_type") or parsed.room_type == expected_params["room_type"])
            and (expected_params.get("area_m2") is None or
                 (parsed.area_m2 is not None and abs(parsed.area_m2 - expected_params["area_m2"]) < 0.01))
        )
        parsed_ok += int(params_correct)
        matched_ids: set[str] = set()
        for hint in parsed.work_scope[:16]:
            m = match_query(hint, trace_id=trace_id, persist_log=False)
            if m.catalog_id:
                matched_ids.add(m.catalog_id)
                search_latencies.append(m.latency_ms)
        # Probe = эталонная формулировка запроса. По ней измеряется top-1 точность
        # и precision авто-принятых совпадений (критерий приёмки №2, ≥85%).
        probe = row["probe"] or row["query"]
        pm = match_query(probe, trace_id=trace_id, persist_log=False)
        probe_total += 1
        probe_correct += int(pm.catalog_id in expected_ids)
        if pm.status == "auto_accepted":
            auto_total += 1
            auto_correct += int(pm.catalog_id in expected_ids)
        ok = expected_ids.issubset(matched_ids)
        matched_ok += int(ok)
        if not ok or not params_correct:
            failures.append({"id": row["id"], "query": row["query"], "expected": sorted(expected_ids),
                             "matched": sorted(matched_ids), "params_correct": params_correct})
    total = len(rows)
    result = {
        "total": total,
        "parser_accuracy": round(parsed_ok / total, 4),
        "matching_top1_accuracy": round(probe_correct / probe_total, 4),
        "matching_recall": round(matched_ok / total, 4),
        "auto_accepted": auto_total,
        "auto_precision": round(auto_correct / auto_total, 4) if auto_total else 0.0,
        "search_latency_p95_ms": round(sorted(search_latencies)[int(len(search_latencies) * 0.95)] if search_latencies else 0, 2),
        "failures": failures[:20], "failures_count": len(failures),
        "thresholds": {"parser_accuracy": 0.90, "auto_precision": 0.85, "regression_pct": -2.0},
        "checked_at": utcnow(),
    }
    result["pass"] = (result["parser_accuracy"] >= 0.90
                      and result["matching_top1_accuracy"] >= 0.85
                      and (result["auto_precision"] >= 0.85 or auto_total == 0)
                      and result["search_latency_p95_ms"] <= settings.search_sla_ms)
    return result


def drift_check() -> dict[str, Any]:
    """Model Drift Loop (ежедневно): качество на golden set против baseline."""
    report = evaluate_golden(trace_id="drift-check")
    model = db.one("SELECT * FROM model_versions WHERE status='active' ORDER BY loaded_at DESC LIMIT 1")
    baseline_missing = not model or model["golden_accuracy"] is None
    baseline = float(model["golden_accuracy"]) if model and model["golden_accuracy"] is not None else report["matching_top1_accuracy"]
    delta = round((report["matching_top1_accuracy"] - baseline) * 100, 2)
    verdict = "baseline_set" if baseline_missing else ("ok" if delta >= -2.0 else "degraded")
    if baseline_missing:
        if model:
            db.execute("UPDATE model_versions SET golden_accuracy=? WHERE id=?", (report["matching_top1_accuracy"], model["id"]))
        else:
            db.insert("model_versions", {"id": str(uuid.uuid4()), "name": "rules-fallback-v1",
                                        "weights_hash": "n/a", "license": "internal", "loaded_at": utcnow(),
                                        "golden_accuracy": report["matching_top1_accuracy"], "status": "active"})
    db.insert("drift_checks", {
        "id": str(uuid.uuid4()), "checked_at": utcnow(),
        "model_version": model["name"] if model else "rules-fallback-v1",
        "golden_accuracy": report["matching_top1_accuracy"], "baseline": baseline,
        "delta_pct": delta, "verdict": verdict,
    })
    if verdict == "degraded":
        notify(event="drift_alert", subject="Model drift обнаружен",
               body=f"Точность на golden set снизилась на {abs(delta)}% относительно baseline. Релизы промптов/моделей заморозить.",
               trace_id="drift-check")
    log_step("drift-check", "drift", 1, verdict, utcnow(), 0, None, None, report)
    return {"report": report, "baseline": baseline, "delta_pct": delta, "verdict": verdict}


def plan_fact(smeta_id: str, fact_total: str | float, *, actor: dict[str, Any],
              notes: str = "") -> dict[str, Any]:
    """Plan-Fact Loop: калибровка коэффициентов на реальных данных."""
    from .repository import load_estimate
    estimate = load_estimate(smeta_id)
    if not estimate:
        raise ValueError("Смета не найдена")
    planned = Decimal(estimate["totals"]["grand_total"])
    fact = Decimal(str(fact_total))
    deviation = (fact - planned) / planned * 100 if planned else Decimal("0")
    db.insert("plan_fact_comparison", {
        "id": str(uuid.uuid4()), "smeta_id": smeta_id, "version_no": estimate["version_no"],
        "planned_total": str(planned), "fact_total": str(fact),
        "deviation_pct": str(deviation.quantize(Decimal("0.01"))), "created_at": utcnow(), "notes": notes,
    })
    factor = (fact / planned).quantize(Decimal("0.0001")) if planned else Decimal("1")
    db.insert("historical_correction_factors", {
        "id": str(uuid.uuid4()), "category": "ALL", "region": estimate["region"],
        "factor": str(factor), "period": utcnow()[:7], "sample_size": 1, "computed_at": utcnow(),
    })
    audit(actor, "plan_fact_record", "smeta", smeta_id, {"planned": str(planned), "fact": str(fact)})
    return {"smeta_id": smeta_id, "planned": str(planned), "fact": str(fact),
            "deviation_pct": str(deviation.quantize(Decimal("0.01"))), "correction_factor": str(factor)}


def feedback(smeta_id: str, *, actor: dict[str, Any], rating: int, comment: str = "",
             correction_id: str | None = None) -> dict[str, Any]:
    """Feedback Loop: пометка исправлений для обучения + журнал событий."""
    if correction_id:
        db.execute("UPDATE llm_corrections SET used_for_training=1 WHERE id=?", (correction_id,))
    payload = {"smeta_id": smeta_id, "rating": rating, "comment": comment[:2000], "correction_id": correction_id}
    db.insert("estimate_events", {"smeta_id": smeta_id, "event_type": "feedback",
                                  "payload": dumps(payload), "actor": actor.get("username", "anonymous"),
                                  "ts": utcnow()})
    audit(actor, "feedback", "feedback", smeta_id, payload)
    return {"accepted": True, **payload}


def metrics() -> dict[str, Any]:
    """Сводка SLA/качества для дашборда (ТЗ 8.1 + конкретные SLA из v1.1 разд. 6)."""
    smetas = db.one("SELECT COUNT(*) AS c FROM smetas")["c"]
    versions = db.one("SELECT COUNT(*) AS c FROM smeta_versions")["c"]
    positions = db.one("SELECT COUNT(*) AS c FROM smeta_positions")["c"]
    status_rows = db.all("SELECT status, COUNT(*) AS c FROM smeta_positions GROUP BY status")
    statuses = {r["status"]: r["c"] for r in status_rows}
    steps = db.all("SELECT step, duration_ms FROM pipeline_execution_log WHERE duration_ms > 0")
    draft_latencies = [r["duration_ms"] for r in steps if r["step"] == "orchestrator"]
    search_latencies = [r["duration_ms"] for r in steps if r["step"] == "search"]
    errors = db.one("SELECT COUNT(*) AS c FROM pipeline_execution_log WHERE status IN ('error','failed','fallback')")["c"]
    total_steps = db.one("SELECT COUNT(*) AS c FROM pipeline_execution_log")["c"] or 1
    last_drift = db.one("SELECT * FROM drift_checks ORDER BY checked_at DESC LIMIT 1")
    last_fresh = db.one("SELECT * FROM data_freshness_log ORDER BY run_at DESC LIMIT 1")
    chain_ok, chain_len = verify_audit_chain()
    auto = statuses.get("auto_accepted", 0)
    return {
        "smetas": smetas, "versions": versions, "positions": positions,
        "position_statuses": statuses,
        "auto_accept_rate": round(auto / positions, 3) if positions else 0,
        "escalation_rate": round(statuses.get("escalated", 0) / positions, 3) if positions else 0,
        "draft_p95_ms": round(statistics.quantiles(draft_latencies, n=20)[18]) if len(draft_latencies) >= 20 else (max(draft_latencies) if draft_latencies else 0),
        "search_p95_ms": round(statistics.quantiles(search_latencies, n=20)[18]) if len(search_latencies) >= 20 else (max(search_latencies) if search_latencies else 0),
        "sla": {"draft_p95_ms": settings.draft_sla_p95_ms, "search_p95_ms": settings.search_sla_ms,
                "error_budget_pct": 1.0, "availability_pilot": 99.0, "availability_prod": 99.5,
                "rpo_h": 1, "rto_h": 4, "notification_s": 30},
        "error_rate_pct": round(errors / total_steps * 100, 3),
        "llm": {"enabled": settings.llm_enabled, "model": settings.llm_model,
                "endpoint_is_local": settings.llm_is_local, "egress_allowed": False},
        "security": {"audit_chain_valid": chain_ok, "audit_entries": chain_len,
                     "prompt_injection_patterns": len(db.all("SELECT id FROM security_audit_log WHERE action='prompt_injection_blocked'"))},
        "last_drift": last_drift, "last_freshness": last_fresh,
        "catalog": get_catalog().coverage(),
        "loops": [
            {"name": "Валидация внутри пайплайна", "period": "каждый запрос", "status": "active"},
            {"name": "Clarification Loop", "period": "при неполноте", "status": "active"},
            {"name": "Revision Loop", "period": "по запросу", "status": "active"},
            {"name": "Feedback Loop", "period": "непрерывно", "status": "active"},
            {"name": "Data Freshness Loop", "period": "еженедельно", "status": "scheduled" if not last_fresh else "active"},
            {"name": "Model Drift Loop", "period": "ежедневно", "status": "scheduled" if not last_drift else "active"},
            {"name": "Plan-Fact Loop", "period": "после проекта", "status": "active"},
            {"name": "Инфраструктурный retry", "period": "при сбоях", "status": "active"},
        ],
    }

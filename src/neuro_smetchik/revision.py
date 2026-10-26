"""Revision Service (ТЗ 3.2.8): дельта-правки, версионирование, diff-view + Feedback Loop."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from .calculation import recalculate
from .catalog import get_catalog
from .config import settings
from .db import db
from .llm import llm
from .models import Position, utcnow
from .notifications import notify
from .repository import event, load_estimate, persist_version
from .security import audit
from .validation import validate

EDITABLE_FIELDS = {"quantity", "unit_price", "name", "unit", "notes", "status", "confidence"}


def _to_positions(estimate: dict[str, Any]) -> tuple[list[Position], dict[str, Position]]:
    """Копирует позиции в новую версию (новые PK) и возвращает карту старых id.

    Строки версий неизменяемы, поэтому id не может повторяться: старые id из UI
    транслируются в новые через эту карту.
    """
    positions: list[Position] = []
    old_to_new: dict[str, Position] = {}
    for i, p in enumerate(estimate["positions"]):
        copy = Position(
            id=str(uuid.uuid4()), catalog_id=p["catalog_id"], name=p["name"], unit=p["unit"],
            quantity=Decimal(p["quantity"]), unit_price=Decimal(p["unit_price"]),
            coefficients=dict(p["coefficients"]), subtotal=Decimal(p["subtotal"]),
            vat_rate=Decimal(p["vat_rate"]), vat_amount=Decimal(p["vat_amount"]),
            total=Decimal(p["total"]), confidence=float(p["confidence"]), status=p["status"],
            source_query=p.get("source_query", ""), notes=p.get("notes", ""), sort_order=i,
        )
        positions.append(copy)
        old_to_new[p["id"]] = copy
    return positions, old_to_new


def apply_revision(smeta_id: str, operations: list[dict[str, Any]], *, actor: dict[str, Any],
                   reason: str = "Правки сметчика", revision_text: str = "",
                   trace_id: str = "") -> dict[str, Any]:
    """Обрабатывает ТОЛЬКО дельту изменений (не пересчёт сметы с нуля)."""
    estimate = load_estimate(smeta_id)
    if not estimate:
        raise ValueError(f"Смета {smeta_id} не найдена")
    if estimate["status"] == "approved":
        raise ValueError("Утверждённая смета неизменяема: создайте новую ревизию/версию через руководителя")
    positions, old_to_new = _to_positions(estimate)
    by_id = {p.id: p for p in positions}
    def find_position(position_id: Any) -> Position | None:
        key = str(position_id)
        return by_id.get(key) or old_to_new.get(key)
    cat = get_catalog()
    applied: list[dict[str, Any]] = []

    # При наличии локальной LLM правку на естественном языке можно преобразовать в дельту.
    if revision_text and llm.enabled:
        import json

        from .prompts import resolve
        prompt = resolve("revision", trace_id)
        res = llm.complete(
            service="revision", system=prompt.body.replace("{revision_text}", revision_text),
            user=revision_text, trace_id=trace_id, prompt_version=prompt.version)
        if res.source == "local_vllm":
            try:
                generated = json.loads(res.content).get("operations", [])
                if isinstance(generated, list) and generated:
                    operations = list(operations) + generated
            except (ValueError, json.JSONDecodeError):
                pass

    for op in operations:
        kind = op.get("op")
        if kind == "update":
            pos = find_position(op.get("position_id"))
            field = str(op.get("field", ""))
            if not pos or field not in EDITABLE_FIELDS:
                applied.append({"op": kind, "ok": False, "error": "unknown position or field"})
                continue
            old = getattr(pos, field)
            value: Any = op["value"]
            if field in ("quantity", "unit_price"):
                value = Decimal(str(value))
                if value < 0:
                    applied.append({"op": kind, "ok": False, "error": "negative value"})
                    continue
            elif field == "confidence":
                value = max(0.0, min(1.0, float(value)))
            else:
                value = str(value)[:1000]
            setattr(pos, field, value)
            if field in ("quantity", "unit_price"):
                pos.status = "manual"
                pos.confidence = 1.0
            applied.append({"op": kind, "ok": True, "field": field, "old": str(old), "new": str(value)})
            db.insert("llm_corrections", {
                "id": str(uuid.uuid4()), "version_id": estimate["version_id"],
                "position_id": str(op.get("position_id")), "field": field,
                "old_value": str(old), "new_value": str(value),
                "corrected_by": actor.get("username", "anonymous"), "created_at": utcnow(),
                "used_for_training": 0,
            })
        elif kind == "remove":
            pos = find_position(op.get("position_id"))
            if pos:
                positions = [p for p in positions if p.id != pos.id]
                by_id.pop(pos.id, None)
                applied.append({"op": kind, "ok": True, "catalog_id": pos.catalog_id})
        elif kind == "add":
            item = cat.get(str(op.get("catalog_id")))
            if not item:
                applied.append({"op": kind, "ok": False, "error": "catalog_id not found — позиция не будет создана (защита от галлюцинаций)"})
                continue
            if any(p.catalog_id == item.id for p in positions):
                applied.append({"op": kind, "ok": False, "error": "duplicate catalog position"})
                continue
            region = estimate["region"]
            coeff = item.region_coeffs.get(region, "1.00") if item.region_coeffs else "1.00"
            qty = Decimal(str(op.get("quantity", 1)))
            pos = Position(id=str(uuid.uuid4()), catalog_id=item.id, name=item.name, unit=item.unit,
                           quantity=qty, unit_price=item.base_price, coefficients={"region": coeff},
                           vat_rate=settings.vat_rate, confidence=1.0, status="manual",
                           source_query="добавлено вручную", sort_order=len(positions))
            positions.append(pos)
            by_id[pos.id] = pos
            applied.append({"op": kind, "ok": True, "catalog_id": item.id})
        else:
            applied.append({"op": kind, "ok": False, "error": "unsupported op"})

    totals = recalculate(positions)
    params = dict(estimate["params"])
    issues, suggestions = validate(positions, totals, params, trace_id=trace_id, smeta_id=smeta_id)
    version_no, _ = persist_version(
        smeta_id=smeta_id, positions=positions, totals=totals, params=params, actor=actor,
        reason=reason, trace_id=trace_id,
        extra={"issues": [i.__dict__ for i in issues], "suggestions": suggestions, "latency_ms": 0})
    event(smeta_id, "revision_applied", {"version_no": version_no, "operations": applied},
          actor.get("username", "anonymous"))
    audit(actor, "apply_revision", "smeta", smeta_id, {"version": version_no, "operations": applied})
    notify(event="draft_ready", subject=f"Ревизия сметы {smeta_id}: v{version_no}",
           body=f"Применено операций: {sum(1 for a in applied if a.get('ok'))} из {len(applied)}",
           trace_id=trace_id)
    result = load_estimate(smeta_id, version_no)
    assert result is not None
    result["applied_operations"] = applied
    return result


def diff(smeta_id: str, from_version: int, to_version: int) -> dict[str, Any]:
    a, b = load_estimate(smeta_id, from_version), load_estimate(smeta_id, to_version)
    if not a or not b:
        raise ValueError("Одна из версий не найдена")
    # Строки версии пересоздаются с новыми id -> сопоставляем по catalog_id.
    ma = {p["catalog_id"]: p for p in a["positions"]}
    mb = {p["catalog_id"]: p for p in b["positions"]}
    added = [{"catalog_id": k, "name": v["name"], "total": v["total"]} for k, v in mb.items() if k not in ma]
    removed = [{"catalog_id": k, "name": v["name"], "total": v["total"]} for k, v in ma.items() if k not in mb]
    changed = []
    for k in ma.keys() & mb.keys():
        fields = {"quantity", "unit_price", "subtotal", "total", "status", "confidence", "notes"}
        delta = {f: {"from": ma[k][f], "to": mb[k][f]} for f in fields if ma[k][f] != mb[k][f]}
        if delta:
            changed.append({"catalog_id": k, "name": mb[k]["name"], "changes": delta})
    return {
        "smeta_id": smeta_id, "from_version": from_version, "to_version": to_version,
        "added": added, "removed": removed, "changed": sorted(changed, key=lambda x: x["catalog_id"]),
        "totals": {"from": a["totals"]["grand_total"], "to": b["totals"]["grand_total"],
                   "delta": str(Decimal(b["totals"]["grand_total"]) - Decimal(a["totals"]["grand_total"]))},
        "checksums": {"from": a["checksum"], "to": b["checksum"]},
    }

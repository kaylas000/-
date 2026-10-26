"""Репозиторий смет: immutable-версии, аудитируемые события, загрузка (ТЗ 3.2.8, 5.2)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from .db import db
from .models import EstimateTotals, Position, dumps, jsonable, loads, utcnow
from .security import audit


def new_id(prefix: str = "id") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def log_step(trace_id: str, step: str, attempt: int, status: str, started_at: str,
             duration_ms: int = 0, error: str | None = None, inp: Any = None,
             out: Any = None, smeta_id: str | None = None,
             prompt_version: str | None = None, model_version: str | None = None) -> None:
    db.insert("pipeline_execution_log", {
        "id": new_id("log"), "trace_id": trace_id, "smeta_id": smeta_id, "step": step,
        "attempt": attempt, "status": status, "started_at": started_at, "duration_ms": duration_ms,
        "error": error, "input_json": dumps(inp) if inp is not None else None,
        "output_json": dumps(out) if out is not None else None,
        "prompt_version": prompt_version, "model_version": model_version,
    })


def event(smeta_id: str, event_type: str, payload: Any, actor: str) -> None:
    db.insert("estimate_events", {"smeta_id": smeta_id, "event_type": event_type,
                                  "payload": dumps(payload), "actor": actor, "ts": utcnow()})


def create_smeta(*, title: str, client: str, region: str, source_request: str,
                 source_type: str, actor: dict[str, Any], trace_id: str) -> str:
    smeta_id = new_id("smt")
    db.insert("smetas", {
        "id": smeta_id, "title": title, "client": client, "status": "draft", "region": region,
        "source_request": source_request, "source_type": source_type,
        "created_by": actor.get("username", "anonymous"), "created_at": utcnow(), "updated_at": utcnow(),
        "current_version": 0, "trace_id": trace_id,
    })
    event(smeta_id, "smeta_created", {"title": title, "trace_id": trace_id}, actor.get("username", "anonymous"))
    audit(actor, "create_smeta", "smeta", smeta_id, {"title": title})
    return smeta_id


def persist_version(*, smeta_id: str, positions: list[Position], totals: EstimateTotals,
                    params: dict[str, Any], actor: dict[str, Any], reason: str,
                    trace_id: str, extra: dict[str, Any] | None = None) -> tuple[int, str]:
    """Создаёт НОВУЮ неизменяемую версию. Существующие строки никогда не меняются."""
    with db.transaction() as tx:
        row = tx.execute("SELECT current_version FROM smetas WHERE id=?", (smeta_id,)).fetchone()
        if row is None:
            raise ValueError(f"Смета {smeta_id} не найдена")
        version_no = int(row["current_version"]) + 1
        version_id = new_id("ver")
        payload = {
            "money": totals.to_dict(), "params": params,
            "issues": extra.get("issues", []) if extra else [],
            "suggestions": extra.get("suggestions", []) if extra else [],
            "trace_id": trace_id, "latency_ms": extra.get("latency_ms", 0) if extra else 0,
        }
        tx.execute(
            "INSERT INTO smeta_versions(id, smeta_id, version_no, created_at, created_by, change_reason, "
            "parent_version, totals, checksum) VALUES (?,?,?,?,?,?,?,?,?)",
            (version_id, smeta_id, version_no, utcnow(), actor.get("username", "anonymous"), reason,
             version_no - 1 if version_no > 1 else None, dumps(payload), totals.checksum),
        )
        for pos in positions:
            tx.execute(
                "INSERT INTO smeta_positions(id, version_id, catalog_id, name, unit, quantity, unit_price, "
                "coefficients, subtotal, vat_rate, vat_amount, total, confidence, status, source_query, notes, sort_order) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (pos.id, version_id, pos.catalog_id, pos.name, pos.unit, str(pos.quantity), str(pos.unit_price),
                 dumps(pos.coefficients), str(pos.subtotal), str(pos.vat_rate), str(pos.vat_amount),
                 str(pos.total), pos.confidence, pos.status, pos.source_query, pos.notes, pos.sort_order),
            )
        tx.execute("UPDATE smetas SET current_version=?, updated_at=? WHERE id=?", (version_no, utcnow(), smeta_id))
        event(smeta_id, "version_created", {"version_no": version_no, "reason": reason,
                                            "positions": len(positions), "checksum": totals.checksum},
              actor.get("username", "anonymous"))
    audit(actor, "create_version", "smeta_version", f"{smeta_id}:v{version_no}", {"reason": reason})
    return version_no, version_id


def _position_from_row(row: dict[str, Any]) -> Position:
    return Position(
        id=row["id"], catalog_id=row["catalog_id"], name=row["name"], unit=row["unit"],
        quantity=Decimal(row["quantity"]), unit_price=Decimal(row["unit_price"]),
        coefficients=loads(row["coefficients"], {}), subtotal=Decimal(row["subtotal"]),
        vat_rate=Decimal(row["vat_rate"]), vat_amount=Decimal(row["vat_amount"]),
        total=Decimal(row["total"]), confidence=row["confidence"], status=row["status"],
        source_query=row["source_query"] or "", notes=row["notes"] or "", sort_order=row["sort_order"],
    )


def load_estimate(smeta_id: str, version_no: int | None = None) -> dict[str, Any] | None:
    meta = db.one("SELECT * FROM smetas WHERE id=?", (smeta_id,))
    if not meta:
        return None
    if version_no is None:
        version_no = int(meta["current_version"])
    version = db.one("SELECT * FROM smeta_versions WHERE smeta_id=? AND version_no=?", (smeta_id, version_no))
    if not version:
        return None
    rows = db.all("SELECT * FROM smeta_positions WHERE version_id=? ORDER BY sort_order", (version["id"],))
    positions = [_position_from_row(r) for r in rows]
    payload = loads(version["totals"], {})
    money = payload.get("money", {})
    totals = EstimateTotals(
        subtotal=Decimal(money.get("subtotal", "0")), overhead=Decimal(money.get("overhead", "0")),
        profit=Decimal(money.get("profit", "0")), vat=Decimal(money.get("vat", "0")),
        grand_total=Decimal(money.get("grand_total", "0")), checksum=money.get("checksum", version["checksum"]),
        verification=money.get("verification", "pending"),
    )
    return jsonable({
        "id": meta["id"], "title": meta["title"], "client": meta["client"], "status": meta["status"],
        "region": meta["region"], "source_request": meta["source_request"], "source_type": meta["source_type"],
        "created_by": meta["created_by"], "created_at": meta["created_at"], "updated_at": meta["updated_at"],
        "current_version": meta["current_version"], "approved_by": meta["approved_by"],
        "approved_at": meta["approved_at"], "second_approver": meta["second_approver"],
        "trace_id": meta["trace_id"], "version_no": version_no, "version_id": version["id"],
        "version_created_at": version["created_at"], "change_reason": version["change_reason"],
        "parent_version": version["parent_version"], "checksum": version["checksum"],
        "positions": positions, "totals": totals, "params": payload.get("params", {}),
        "issues": payload.get("issues", []), "suggestions": payload.get("suggestions", []),
        "latency_ms": payload.get("latency_ms", 0), "payload_trace_id": payload.get("trace_id"),
    })


def list_estimates(limit: int = 50) -> list[dict[str, Any]]:
    rows = db.all("SELECT * FROM smetas ORDER BY updated_at DESC LIMIT ?", (limit,))
    out = []
    for r in rows:
        v = db.one("SELECT totals FROM smeta_versions WHERE smeta_id=? AND version_no=?", (r["id"], r["current_version"]))
        money = loads(v["totals"], {}).get("money", {}) if v else {}
        out.append({"id": r["id"], "title": r["title"], "client": r["client"], "status": r["status"],
                    "region": r["region"], "current_version": r["current_version"],
                    "created_at": r["created_at"], "updated_at": r["updated_at"],
                    "grand_total": money.get("grand_total", "0")})
    return out


def set_status(smeta_id: str, status: str, actor: dict[str, Any], **fields: Any) -> None:
    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        db.execute(f"UPDATE smetas SET status=?, {sets} WHERE id=?", (status, *fields.values(), smeta_id))
    else:
        db.execute("UPDATE smetas SET status=?, updated_at=? WHERE id=?", (status, utcnow(), smeta_id))
    audit(actor, "change_status", "smeta", smeta_id, {"status": status, **fields})
    event(smeta_id, "status_changed", {"status": status}, actor.get("username", "anonymous"))


def version_rows(smeta_id: str) -> list[dict[str, Any]]:
    return db.all("SELECT id, version_no, created_at, created_by, change_reason, parent_version, checksum "
                  "FROM smeta_versions WHERE smeta_id=? ORDER BY version_no", (smeta_id,))

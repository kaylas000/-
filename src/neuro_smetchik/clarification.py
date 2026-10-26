"""Clarification Service (ТЗ 3.2.2): <=5 итераций, вопросы только по критичным полям."""
from __future__ import annotations

import re
import uuid
from typing import Any

from .catalog import get_catalog
from .config import settings
from .models import dumps, loads, utcnow
from .db import db
from .parser_service import compute_missing
from .prompts import resolve
from .notifications import notify
from .repository import log_step

FIELD_QUESTIONS = {
    "area_m2": "Какова площадь помещения в квадратных метрах? (например: 42 м²)",
    "room_type": "Уточните тип помещения: квартира, комната, ванная, кухня, офис, коммерческое или дом?",
    "work_scope": "Какие работы нужно включить в смету? Перечислите через запятую (например: штукатурка, покраска, электрика).",
    "region": "Для какого региона считать смету? (Москва, Санкт-Петербург, Казань, Екатеринбург, Регионы)",
}


def start_session(parsed: dict[str, Any], *, smeta_id: str, trace_id: str) -> dict[str, Any]:
    sid = str(uuid.uuid4())
    db.insert("clarification_sessions", {
        "id": sid, "smeta_id": smeta_id, "trace_id": trace_id,
        "max_turns": settings.max_clarification_turns, "asked_count": 0,
        "parsed_json": dumps(parsed), "status": "open", "created_at": utcnow(),
    })
    session = db.one("SELECT * FROM clarification_sessions WHERE id=?", (sid,)) or {}
    q = next_question(sid, trace_id)
    return {"session": session, "question": q}


def get_session(session_id: str) -> dict[str, Any] | None:
    row = db.one("SELECT * FROM clarification_sessions WHERE id=?", (session_id,))
    if row:
        row["parsed"] = loads(row["parsed_json"], {})
    return row


def next_question(session_id: str, trace_id: str) -> dict[str, Any] | None:
    s = get_session(session_id)
    if not s or s["status"] != "open":
        return None
    parsed = s["parsed"]
    missing = [f for f in compute_missing(parsed) if f in FIELD_QUESTIONS]
    if not missing or int(s["asked_count"]) >= int(s["max_turns"]):
        db.execute("UPDATE clarification_sessions SET status='completed' WHERE id=?", (session_id,))
        return None
    field = missing[0]
    prompt = resolve("clarification", trace_id)
    question = FIELD_QUESTIONS[field]
    turn_no = int(s["asked_count"]) + 1
    db.insert("clarification_turns", {
        "id": str(uuid.uuid4()), "session_id": session_id, "turn_no": turn_no,
        "field": field, "question": question, "asked_at": utcnow(), "answer": None,
        "answered_at": None, "skipped": 0,
    })
    db.execute("UPDATE clarification_sessions SET asked_count=? WHERE id=?", (turn_no, session_id))
    log_step(trace_id, "clarification", turn_no, "question", utcnow(), 0,
             None, {"field": field, "prompt_version": prompt.version}, {"question": question},
             s.get("smeta_id"), prompt.version)
    return {"session_id": session_id, "turn_no": turn_no, "field": field, "question": question,
            "remaining": int(s["max_turns"]) - turn_no}


def _apply_answer(parsed: dict[str, Any], field: str, answer: str) -> None:
    if field == "area_m2":
        m = re.search(r"(\d+(?:[.,]\d+)?)", answer)
        if m:
            parsed["area_m2"] = float(m.group(1).replace(",", "."))
    elif field == "room_type":
        q = answer.lower()
        for key in ("квартира", "комната", "ванная", "кухня", "офис", "коммерческое", "дом"):
            if key in q:
                parsed["room_type"] = key
                break
        else:
            parsed["room_type"] = "другое"
    elif field == "work_scope":
        parsed["work_scope"] = [p.strip() for p in re.split(r"[,;]", answer) if p.strip()][:16]
    elif field == "region":
        parsed["region"] = answer.strip() or "Москва"
    parsed["missing_fields"] = compute_missing(parsed)


def answer_turn(session_id: str, answer: str, *, skip: bool = False,
                actor: dict[str, Any] | None = None, trace_id: str = "") -> dict[str, Any]:
    """Принять ответ/пропуск. Возвращает обновлённые параметры и следующий вопрос."""
    s = get_session(session_id)
    if not s:
        raise ValueError("Сессия уточнения не найдена")
    if s["status"] != "open":
        return {"session_id": session_id, "status": s["status"], "parsed": s["parsed"], "question": None}
    trace_id = trace_id or s.get("trace_id") or ""
    turn = db.one("SELECT * FROM clarification_turns WHERE session_id=? AND answer IS NULL AND skipped=0 "
                  "ORDER BY turn_no DESC LIMIT 1", (session_id,))
    if not turn:
        return {"session_id": session_id, "status": s["status"], "parsed": s["parsed"], "question": None}
    parsed = s["parsed"]
    if skip:
        db.execute("UPDATE clarification_turns SET skipped=1, answered_at=? WHERE id=?", (utcnow(), turn["id"]))
        db.execute("UPDATE clarification_sessions SET status='skipped' WHERE id=?", (session_id,))
        # Продолжаем с неполными данными: детерминированные дефолты + пометка в constraints
        if parsed.get("area_m2") is None:
            parsed["area_m2"] = 20.0
        if parsed.get("room_type") == "другое":
            parsed["room_type"] = "другое"
        if not parsed.get("work_scope"):
            parsed["work_scope"] = list(get_catalog().typical(parsed.get("room_type", "другое")).get("default_work_scope", []))
        parsed.setdefault("constraints", []).append(" Clarification Loop прерван пользователем: часть данных принята по умолчанию")
        parsed["missing_fields"] = compute_missing(parsed)
        db.execute("UPDATE clarification_sessions SET parsed_json=? WHERE id=?", (dumps(parsed), session_id))
        log_step(trace_id, "clarification", int(turn["turn_no"]), "skipped", utcnow(), 0,
                 None, {"field": turn["field"]}, parsed, s.get("smeta_id"))
        return {"session_id": session_id, "status": "skipped", "parsed": parsed, "question": None}
    _apply_answer(parsed, turn["field"], answer)
    db.execute("UPDATE clarification_turns SET answer=?, answered_at=? WHERE id=?", (answer[:4000], utcnow(), turn["id"]))
    db.execute("UPDATE clarification_sessions SET parsed_json=? WHERE id=?", (dumps(parsed), session_id))
    log_step(trace_id, "clarification", int(turn["turn_no"]), "answered", utcnow(), 0,
             None, {"field": turn["field"], "answer": answer[:500]}, parsed, s.get("smeta_id"))
    q = next_question(session_id, trace_id)
    status = "completed" if q is None else "open"
    return {"session_id": session_id, "status": status, "parsed": parsed, "question": q}


def timeout(session_id: str) -> dict[str, Any]:
    """Уведомление об истечении таймаута ожидания сметчика (ТЗ 3.2.11 / вопрос 7)."""
    s = get_session(session_id)
    if not s:
        raise ValueError("Сессия не найдена")
    if s["status"] == "open":
        db.execute("UPDATE clarification_sessions SET status='expired' WHERE id=?", (session_id,))
        notify(recipient="estimator", channel="ui", priority="high",
               subject="Таймаут Clarification Loop",
               body=f"Сессия {session_id} ожидает ответ сметчика. Запрос переведён в отложенную обработку.",
               trace_id=s.get("trace_id"))
    return {"session_id": session_id, "status": "expired"}

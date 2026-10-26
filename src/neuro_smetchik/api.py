"""FastAPI: единая точка входа (ТЗ 4.3) + контракты из Приложения Г.

OpenAPI-спецификация доступна на /openapi.json и /openapi.yaml.
Все внутренние вызовы несут trace_id; API версионируется (/api/v1/).
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__
from .catalog import get_catalog
from .clarification import answer_turn, get_session, timeout
from .config import settings
from .db import db
from .documents import generate
from .llm import llm
from .loops import drift_check, evaluate_golden, feedback, metrics, plan_fact
from .matching import match_query
from .models import dumps, jsonable, loads, utcnow
from .notifications import inbox, mark_read
from .orchestrator import PIPELINE_STEPS, run_pipeline
from .parser_service import UnsafeRequest, deterministic_parse
from .prompts import activate, create_version, list_versions, resolve, set_canary
from .repository import (list_estimates, load_estimate, set_status, version_rows)
from .revision import apply_revision, diff
from .search import get_search
from .security import (PermissionDenied, audit, rate_limiter, require, sanitize_text,
                       verify_audit_chain)

WEB_DIR = Path(__file__).with_name("web")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Инициализация локального контура при старте (данные, схема, промпты, baseline)."""
    from .prompts import seed_prompts
    from .scripts_init import ensure_initialized
    ensure_initialized()
    seed_prompts()
    yield


app = FastAPI(
    title="Нейро-сметчик API",
    version=__version__,
    description=(
        "Локальная система поддержки составления смет. Human-in-the-loop, Decimal-расчёты, "
        "immutable-версии, трассировка trace_id, Prompt Version Control, защита от prompt injection. "
        "Данные не покидают периметр."
    ),
    docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware / actors
# ---------------------------------------------------------------------------
@app.middleware("http")
async def guard(request: Request, call_next):  # type: ignore[no-untyped-def]
    key = f"{request.client.host if request.client else 'unknown'}:{request.headers.get('X-User', 'anon')}"
    if request.url.path.startswith("/api/") and not rate_limiter.allow(key):
        return JSONResponse({"detail": "Rate limit exceeded (ТЗ 6.6)"}, status_code=429)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


def actor_from(request: Request) -> dict[str, Any]:
    username = request.headers.get("X-User", "ivanov")
    row = db.one("SELECT * FROM users WHERE username=? AND active=1", (username,))
    role = request.headers.get("X-Role") or (row["role"] if row else "client")
    return {"username": username, "role": role, "mfa": request.headers.get("X-MFA", "0") in ("1", "true", "True"),
            "display_name": row["display_name"] if row else username}


@app.exception_handler(PermissionDenied)
async def permission_handler(request: Request, exc: PermissionDenied) -> JSONResponse:
    return JSONResponse({"detail": str(exc), "code": "permission_denied"}, status_code=403)


@app.exception_handler(UnsafeRequest)
async def unsafe_handler(request: Request, exc: UnsafeRequest) -> JSONResponse:
    return JSONResponse({"detail": str(exc), "code": "prompt_injection_blocked"}, status_code=400)


# ---------------------------------------------------------------------------
# Pydantic контракты (Приложение Г)
# ---------------------------------------------------------------------------
class RequestIn(BaseModel):
    text: str = Field(min_length=3, max_length=8000, description="Запрос на естественном языке")
    client: str = ""
    source_type: Literal["text", "voice", "photo", "scan"] = "text"
    use_llm_judge: bool = False


class ClarificationIn(BaseModel):
    answer: str = ""
    skip: bool = False


class RevisionIn(BaseModel):
    operations: list[dict[str, Any]] = Field(default_factory=list)
    reason: str = "Правки сметчика"
    revision_text: str = ""


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5, default=5)
    comment: str = ""
    correction_id: str | None = None


class PlanFactIn(BaseModel):
    fact_total: str
    notes: str = ""


class PromptIn(BaseModel):
    service: str
    body: str
    author: str = "estimator"
    canary_percent: int = 0
    activate: bool = False


class PromptActionIn(BaseModel):
    service: str
    version: str
    canary_percent: int = 0


# ---------------------------------------------------------------------------
# System / meta
# ---------------------------------------------------------------------------
@app.get("/api/v1/health", tags=["system"], summary="Проверка доступности и локальности контура")
def health() -> dict[str, Any]:
    return {"status": "ok", "version": __version__, "env": settings.app_env,
            "llm_enabled": llm.enabled, "llm_endpoint_is_local": settings.llm_is_local,
            "external_ai_egress": False, "db": "sqlite-wal", "catalog_items": len(get_catalog().items)}


@app.get("/api/v1/meta", tags=["system"], summary="Конфигурация порогов и справочники для UI")
def meta() -> dict[str, Any]:
    return {
        "version": __version__, "company": settings.company_name, "inn": settings.company_inn,
        "steps": PIPELINE_STEPS,
        "thresholds": {"auto_accept": float(settings.match_auto_accept),
                       "extended_search": float(settings.match_extended_search),
                       "max_clarification_turns": settings.max_clarification_turns,
                       "four_eyes": float(settings.four_eyes_threshold),
                       "vat": float(settings.vat_rate), "overhead": float(settings.overhead),
                       "profit": float(settings.profit)},
        "sla": {"draft_p95_ms": settings.draft_sla_p95_ms, "search_p95_ms": settings.search_sla_ms,
                "rpo_h": 1, "rto_h": 4},
        "roles": [{"id": r["role"], "label": r["description"]} for r in db.all("SELECT * FROM roles")],
        "users": db.all("SELECT username, display_name, role, mfa_enabled FROM users"),
        "llm": {"enabled": llm.enabled, "model": settings.llm_model, "local_only": settings.llm_is_local},
        "formats": ["xlsx", "pdf", "grand_smeta_csv"],
    }


# ---------------------------------------------------------------------------
# Основной сценарий
# ---------------------------------------------------------------------------
@app.post("/api/v1/requests", tags=["pipeline"], summary="Создать черновик сметы (User Flow 3.1)")
def create_request(body: RequestIn, request: Request) -> dict[str, Any]:
    actor = require(actor_from(request), "request:create")
    return run_pipeline(text=body.text, actor=actor, source_type=body.source_type,
                        client=body.client, use_llm_judge=body.use_llm_judge)


@app.post("/api/v1/clarification/{session_id}/answer", tags=["clarification"],
          summary="Ответ/пропуск в Clarification Loop с пересчётом версии")
def clarification_answer(session_id: str, body: ClarificationIn, request: Request) -> dict[str, Any]:
    actor = require(actor_from(request), "estimate:write")
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "Сессия не найдена")
    result = answer_turn(session_id, body.answer, skip=body.skip, actor=actor,
                         trace_id=session.get("trace_id") or "")
    # Пересчитываем смету (дельта версии), когда диалог завершён или пропущен.
    if result["status"] in ("completed", "skipped") and session.get("smeta_id"):
        estimate = run_pipeline(
            text=f"Уточнённые данные: {dumps(result['parsed'])[:500]}", actor=actor,
            client="", smeta_id=session["smeta_id"], params_override=result["parsed"],
            session_id=session_id)
        result["estimate"] = estimate
    else:
        result["estimate"] = load_estimate(session["smeta_id"]) if session.get("smeta_id") else None
    return result


@app.post("/api/v1/clarification/{session_id}/timeout", tags=["clarification"],
          summary="Таймаут ожидания сметчика -> уведомление + отложенная обработка")
def clarification_timeout(session_id: str, request: Request) -> dict[str, Any]:
    require(actor_from(request), "estimate:write")
    return timeout(session_id)


@app.get("/api/v1/estimates", tags=["estimates"], summary="Список смет")
def estimates(request: Request, limit: int = 50) -> dict[str, Any]:
    require(actor_from(request), "estimate:read")
    return {"items": list_estimates(limit)}


@app.get("/api/v1/estimates/{smeta_id}", tags=["estimates"], summary="Смета с позициями и итогами")
def get_estimate(smeta_id: str, request: Request, version: int | None = None) -> dict[str, Any]:
    require(actor_from(request), "estimate:read")
    est = load_estimate(smeta_id, version)
    if not est:
        raise HTTPException(404, "Смета/версия не найдена")
    return est


@app.get("/api/v1/estimates/{smeta_id}/versions", tags=["estimates"], summary="История immutable-версий")
def versions(smeta_id: str, request: Request) -> dict[str, Any]:
    require(actor_from(request), "estimate:read")
    return {"items": version_rows(smeta_id)}


@app.get("/api/v1/estimates/{smeta_id}/diff", tags=["estimates"], summary="Diff-view двух версий")
def get_diff(smeta_id: str, request: Request, from_version: int = 1, to_version: int = 2) -> dict[str, Any]:
    require(actor_from(request), "estimate:read")
    try:
        return diff(smeta_id, from_version, to_version)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/v1/estimates/{smeta_id}/revisions", tags=["revisions"], summary="Применить дельту правок")
def new_revision(smeta_id: str, body: RevisionIn, request: Request) -> dict[str, Any]:
    actor = require(actor_from(request), "estimate:write")
    try:
        return apply_revision(smeta_id, body.operations, actor=actor, reason=body.reason,
                              revision_text=body.revision_text, trace_id=str(uuid.uuid4()))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/v1/estimates/{smeta_id}/approve", tags=["estimates"],
          summary="Утверждение сметы (принцип четырёх глаз выше порога)")
def approve(smeta_id: str, request: Request) -> dict[str, Any]:
    actor_raw = actor_from(request)
    est = load_estimate(smeta_id)
    if not est:
        raise HTTPException(404, "Смета не найдена")
    if est["totals"]["verification"] != "ok":
        raise HTTPException(409, "Утверждение заблокировано: контрольная сумма не подтверждена")
    if any(i["level"] == "error" for i in est.get("issues", [])):
        raise HTTPException(409, "Утверждение заблокировано: ошибки валидации")
    grand = Decimal(est["totals"]["grand_total"])
    needs_second = grand >= settings.four_eyes_threshold
    role = actor_raw["role"]
    if needs_second:
        if est["status"] == "pending_second_approval":
            actor = require(actor_raw, "estimate:approve:second")
            set_status(smeta_id, "approved", actor, second_approver=actor["username"])
            return {"status": "approved", "four_eyes": True, "second_approver": actor["username"]}
        actor = require(actor_raw, "estimate:approve")
        set_status(smeta_id, "pending_second_approval", actor, approved_by=actor["username"])
        from .notifications import notify
        notify(event="approval_required", subject=f"Требуется вторая подпись: {smeta_id}",
               body=f"Смета на {grand} ₽ превышает порог {settings.four_eyes_threshold} ₽. Необходим руководитель с MFA.",
               trace_id=est["trace_id"])
        return {"status": "pending_second_approval", "four_eyes": True,
                "message": "Ожидается вторая подпись руководителя (MFA)"}
    if role not in ("estimator", "manager", "admin"):
        raise PermissionDenied("Клиент не может утверждать смету")
    set_status(smeta_id, "approved", actor_raw, approved_by=actor_raw["username"], approved_at=utcnow())
    return {"status": "approved", "four_eyes": False, "approved_by": actor_raw["username"]}


@app.get("/api/v1/estimates/{smeta_id}/documents/{fmt}", tags=["documents"],
         summary="Excel / PDF / CSV для Гранд-Смета")
def get_document(smeta_id: str, fmt: Literal["xlsx", "pdf", "csv"], request: Request) -> Response:
    actor = require(actor_from(request), "estimate:read")
    est = load_estimate(smeta_id)
    if not est:
        raise HTTPException(404, "Смета не найдена")
    fmt_key = "grand_smeta_csv" if fmt == "csv" else fmt
    try:
        info = generate(est, fmt_key, actor)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Ошибка генерации документа: {exc}") from exc
    media = {"xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
             "pdf": "application/pdf", "grand_smeta_csv": "text/csv; charset=utf-8"}[fmt_key]
    return FileResponse(info["path"], filename=info["filename"], media_type=media)


@app.post("/api/v1/estimates/{smeta_id}/feedback", tags=["feedback"], summary="Feedback Loop")
def post_feedback(smeta_id: str, body: FeedbackIn, request: Request) -> dict[str, Any]:
    actor = require(actor_from(request), "estimate:write")
    return feedback(smeta_id, actor=actor, rating=body.rating, comment=body.comment,
                    correction_id=body.correction_id)


@app.post("/api/v1/estimates/{smeta_id}/plan-fact", tags=["feedback"], summary="Plan-Fact Loop")
def post_plan_fact(smeta_id: str, body: PlanFactIn, request: Request) -> dict[str, Any]:
    actor = require(actor_from(request), "estimate:write")
    try:
        return plan_fact(smeta_id, body.fact_total, actor=actor, notes=body.notes)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


# ---------------------------------------------------------------------------
# Каталог, поиск, матчинг, vision
# ---------------------------------------------------------------------------
@app.get("/api/v1/catalog", tags=["catalog"], summary="Каталог расценок + покрытие")
def catalog_all(request: Request) -> dict[str, Any]:
    actor = actor_from(request)
    if actor["role"] != "client":
        require(actor, "catalog:read")
    cat = get_catalog()
    return {"items": [jsonable(i) for i in cat.items], "coverage": cat.coverage(),
            "compositions": cat.compositions,
            "sources": db.all("SELECT * FROM rate_catalog_sources")}


@app.get("/api/v1/catalog/search", tags=["catalog"], summary="Гибридный поиск top-N (SLA p95 <= 500 мс)")
def catalog_search(request: Request, q: str = Query(min_length=2, max_length=300), limit: int = 8) -> dict[str, Any]:
    hits = get_search().search(q, top_n=min(limit, 30))
    return {"query": q, "latency_ms": hits[0].latency_ms if hits else 0,
            "sla_ms": settings.search_sla_ms, "within_sla": (hits[0].latency_ms if hits else 0) <= settings.search_sla_ms,
            "results": [{"catalog_id": h.catalog_id, "code": h.item.code, "name": h.item.name,
                         "unit": h.item.unit, "price": str(h.item.base_price), "category": h.item.category,
                         "score": h.score, "semantic_score": h.semantic_score,
                         "keyword_score": h.keyword_score} for h in hits]}


@app.get("/api/v1/matching", tags=["matching"], summary="Контракт Matching Service (Приложение Г)")
def matching_contract(request: Request, q: str = Query(min_length=2, max_length=300)) -> dict[str, Any]:
    require(actor_from(request), "catalog:read")
    m = match_query(q, trace_id="api-matching")
    return {"trace_id": "api-matching", "matched_catalog_id": m.catalog_id,
            "confidence": m.confidence, "status": m.status, "model_used": m.model_used,
            "latency_ms": m.latency_ms, "attempts": m.attempts}


@app.post("/api/v1/vision", tags=["vision"], summary="Загрузка фото/скана (MIME, размер, anti-injection)")
async def vision_upload(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    actor = require(actor_from(request), "request:create")
    data = await file.read()
    from .vision import analyze_image
    result = analyze_image(data, filename=file.filename or "upload", mime=file.content_type or "",
                           trace_id=str(uuid.uuid4()), actor=actor)
    if not result.get("accepted"):
        raise HTTPException(400, result.get("reason", "Файл отклонён"))
    return result


# ---------------------------------------------------------------------------
# Prompt Version Control
# ---------------------------------------------------------------------------
@app.get("/api/v1/prompts", tags=["prompts"], summary="Версии системных промптов")
def prompts(request: Request, service: str | None = None) -> dict[str, Any]:
    require(actor_from(request), "prompt:read")
    return {"items": list_versions(service),
            "active": {s: resolve(s, "ui").version for s in
                       ("parser", "clarification", "matching", "validation_judge", "vision", "revision")}}


@app.post("/api/v1/prompts", tags=["prompts"], summary="Создать версию промпта (draft/canary/active)")
def prompt_create(body: PromptIn, request: Request) -> dict[str, Any]:
    actor = require(actor_from(request), "prompt:write")
    row = create_version(body.service, body.body, actor["username"],
                         canary_percent=body.canary_percent, activate=body.activate)
    audit(actor, "prompt_version_created", "prompt", row.get("id"), {"service": body.service, "version": row.get("version")})
    return row


@app.post("/api/v1/prompts/activate", tags=["prompts"], summary="Активация/ОТКАТ версии без деплоя кода")
def prompt_activate(body: PromptActionIn, request: Request) -> dict[str, Any]:
    actor = require(actor_from(request), "prompt:write")
    try:
        row = activate(body.service, body.version)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    audit(actor, "prompt_activated", "prompt", row.get("id"), {"service": body.service, "version": body.version})
    return row


@app.post("/api/v1/prompts/canary", tags=["prompts"], summary="Canary-тестирование версии на доле трафика")
def prompt_canary(body: PromptActionIn, request: Request) -> dict[str, Any]:
    actor = require(actor_from(request), "prompt:write")
    try:
        row = set_canary(body.service, body.version, max(0, min(100, body.canary_percent)))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    audit(actor, "prompt_canary", "prompt", row.get("id"),
          {"service": body.service, "version": body.version, "percent": body.canary_percent})
    return row


# ---------------------------------------------------------------------------
# Мониторинг / обратные связи / аудит
# ---------------------------------------------------------------------------
@app.get("/api/v1/notifications", tags=["monitoring"], summary="Журнал уведомлений по роли")
def notifications(request: Request, unread_only: bool = False) -> dict[str, Any]:
    actor = actor_from(request)
    return {"items": inbox(actor["role"], unread_only=unread_only), "latency_sla_s": 30}


@app.post("/api/v1/notifications/{notification_id}/read", tags=["monitoring"])
def notification_read(notification_id: str, request: Request) -> dict[str, Any]:
    mark_read(notification_id)
    return {"ok": True}


@app.get("/api/v1/metrics", tags=["monitoring"], summary="SLA, дрейф, error budget, состояние циклов")
def get_metrics() -> dict[str, Any]:
    return metrics()


@app.post("/api/v1/admin/golden", tags=["monitoring"], summary="Regression-прогон на golden test set")
def golden_eval(request: Request, limit: int | None = None) -> dict[str, Any]:
    actor = actor_from(request)
    if actor["role"] not in ("estimator", "manager", "admin"):
        require(actor, "metrics:read")
    return evaluate_golden(limit=limit)


@app.post("/api/v1/admin/drift", tags=["monitoring"], summary="Model Drift Loop")
def drift(request: Request) -> dict[str, Any]:
    return drift_check()


@app.post("/api/v1/admin/freshness", tags=["monitoring"], summary="Data Freshness Loop")
def freshness(request: Request) -> dict[str, Any]:
    require(actor_from(request), "catalog:read")
    result = get_catalog().freshness_check()
    if result["anomalies"]:
        from .notifications import notify
        notify(event="freshness", subject="Прайс-каталог требует актуализации",
               body=f"Обнаружено {result['anomalies']} позиций с устаревшими/аномальными ценами.", trace_id="freshness")
    return result


@app.get("/api/v1/admin/trace/{trace_id}", tags=["monitoring"], summary="Сквозная трассировка пайплайна")
def trace(trace_id: str, request: Request) -> dict[str, Any]:
    actor = actor_from(request)
    if actor["role"] in ("manager", "admin"):
        require(actor, "audit:read")
    steps = db.all("SELECT * FROM pipeline_execution_log WHERE trace_id=? ORDER BY id", (trace_id,))
    for s in steps:
        s["input_json"] = loads(s["input_json"], None)
        s["output_json"] = loads(s["output_json"], None)
    llm_rows = db.all("SELECT id, service, prompt_version, model_version, input_json, output_json, confidence, "
                      "latency_ms, created_at, retention_until FROM llm_inference_log WHERE trace_id=? ORDER BY created_at",
                      (trace_id,))
    return {"trace_id": trace_id, "steps": steps, "llm_inference_log": llm_rows,
            "step_count": len(steps), "llm_calls": len(llm_rows)}


@app.get("/api/v1/admin/audit", tags=["monitoring"], summary="Неизменяемый журнал безопасности")
def audit_log(request: Request, limit: int = 100) -> dict[str, Any]:
    actor = require(actor_from(request), "audit:read")
    rows = db.all("SELECT * FROM security_audit_log ORDER BY id DESC LIMIT ?", (limit,))
    chain_ok, length = verify_audit_chain()
    return {"items": rows, "chain_valid": chain_ok, "chain_length": length, "requested_by": actor["username"]}


@app.get("/api/v1/admin/events/{smeta_id}", tags=["monitoring"], summary="Event Sourcing по смете")
def events(smeta_id: str, request: Request) -> dict[str, Any]:
    require(actor_from(request), "estimate:read")
    rows = db.all("SELECT * FROM estimate_events WHERE smeta_id=? ORDER BY id", (smeta_id,))
    for r in rows:
        r["payload"] = loads(r["payload"], {})
    return {"items": rows}


@app.get("/api/v1/admin/corrections", tags=["monitoring"], summary="Исправления человека (обучение)")
def corrections(request: Request) -> dict[str, Any]:
    return {"items": db.all("SELECT * FROM llm_corrections ORDER BY created_at DESC LIMIT 200")}


@app.get("/api/v1/admin/parser-preview", tags=["debug"], summary="Детерминированный разбор запроса без записи")
def parser_preview(q: str = Query(min_length=3, max_length=2000)) -> dict[str, Any]:
    verdict = sanitize_text(q)
    return {"sanitized": verdict.sanitized, "clean": verdict.clean, "patterns": list(verdict.patterns),
            "parsed": deterministic_parse(verdict.sanitized)}


# ---------------------------------------------------------------------------
# OpenAPI YAML + статический UI
# ---------------------------------------------------------------------------
@app.get("/metrics", include_in_schema=False, summary="Prometheus exposition (scrape)")
def prometheus_metrics() -> PlainTextResponse:
    m = metrics()
    s = m["sla"]
    lines = [
        "# HELP neuro_smetchik_smetas_total Total estimates", "# TYPE neuro_smetchik_smetas_total gauge",
        f"neuro_smetchik_smetas_total {m['smetas']}",
        "# HELP neuro_smetchik_versions_total Total immutable versions", "# TYPE neuro_smetchik_versions_total gauge",
        f"neuro_smetchik_versions_total {m['versions']}",
        "# HELP neuro_smetchik_positions_total Total estimate positions", "# TYPE neuro_smetchik_positions_total gauge",
        f"neuro_smetchik_positions_total {m['positions']}",
        "# HELP neuro_smetchik_auto_accept_rate Auto-accepted positions ratio", "# TYPE neuro_smetchik_auto_accept_rate gauge",
        f"neuro_smetchik_auto_accept_rate {m['auto_accept_rate']}",
        "# HELP neuro_smetchik_escalation_rate Escalated positions ratio", "# TYPE neuro_smetchik_escalation_rate gauge",
        f"neuro_smetchik_escalation_rate {m['escalation_rate']}",
        "# HELP neuro_smetchik_draft_p95_ms Draft generation p95", "# TYPE neuro_smetchik_draft_p95_ms gauge",
        f"neuro_smetchik_draft_p95_ms {m['draft_p95_ms']}",
        "# HELP neuro_smetchik_search_p95_ms Search p95", "# TYPE neuro_smetchik_search_p95_ms gauge",
        f"neuro_smetchik_search_p95_ms {m['search_p95_ms']}",
        "# HELP neuro_smetchik_error_rate_pct Technical error rate", "# TYPE neuro_smetchik_error_rate_pct gauge",
        f"neuro_smetchik_error_rate_pct {m['error_rate_pct']}",
        "# HELP neuro_smetchik_audit_chain_valid Append-only audit chain integrity", "# TYPE neuro_smetchik_audit_chain_valid gauge",
        f"neuro_smetchik_audit_chain_valid {int(m['security']['audit_chain_valid'])}",
        "# HELP neuro_smetchik_external_ai_egress External AI API egress (must be 0)", "# TYPE neuro_smetchik_external_ai_egress gauge",
        f"neuro_smetchik_external_ai_egress {int(m['llm']['egress_allowed'])}",
        "# HELP neuro_smetchik_draft_sla_ms Draft SLA target", "# TYPE neuro_smetchik_draft_sla_ms gauge",
        f"neuro_smetchik_draft_sla_ms {s['draft_p95_ms']}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/openapi.yaml", include_in_schema=False)
def openapi_yaml() -> PlainTextResponse:
    return PlainTextResponse(yaml.safe_dump(app.openapi(), allow_unicode=True, sort_keys=False),
                             media_type="application/yaml")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/favicon.svg", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(WEB_DIR / "favicon.svg", media_type="image/svg+xml")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

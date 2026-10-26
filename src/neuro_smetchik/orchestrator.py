"""Orchestrator (ТЗ 3.2.9): детерминированный пайплайн, retry, circuit breaker, эскалация.

Никакого «свободного агентного поведения» LLM: последовательность шагов фиксирована,
LLM участвует только как классификатор/ревьюер внутри отдельных сервисов.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable

from .calculation import recalculate
from .catalog import get_catalog
from .clarification import start_session
from .config import settings
from .db import db
from .llm import llm
from .matching import match_query
from .models import ParsedRequest, Position, utcnow
from .notifications import notify
from .parser_service import parse_request
from .repository import create_smeta, load_estimate, log_step, persist_version, set_status
from .security import audit
from .validation import validate
from .vision import analyze_image

PIPELINE_STEPS = ["parser", "clarification", "search", "matching", "calculation", "validation", "document"]


@dataclass
class CircuitBreaker:
    threshold: int = 3
    failures: int = 0
    opened_at: float | None = None
    cooldown_s: float = 20.0

    @property
    def is_open(self) -> bool:
        if self.opened_at and time.monotonic() - self.opened_at > self.cooldown_s:
            self.opened_at = None
            self.failures = 0
        return self.failures >= self.threshold

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = time.monotonic()

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None


breakers: dict[str, CircuitBreaker] = {step: CircuitBreaker(settings.circuit_breaker_threshold)
                                       for step in ("matching", "calculation", "validation", "search")}


@dataclass
class PipelineState:
    trace_id: str
    actor: dict[str, Any]
    steps: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    escalations: list[str] = field(default_factory=list)

    def mark(self, step: str, status: str, duration_ms: int = 0, detail: str = "") -> None:
        self.steps.append({"step": step, "status": status, "duration_ms": duration_ms, "detail": detail})
        log_step(self.trace_id, step, 1, status, utcnow(), duration_ms,
                 detail or None, None, {"detail": detail})


def with_retry(step: str, fn: Callable[[], Any], state: PipelineState, attempts: int = 3) -> Any:
    """Retry с экспоненциальной задержкой для ТЕХНИЧЕСКИХ сбоев (ТЗ 8.2, цикл №8)."""
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            if breakers[step].is_open:
                raise RuntimeError(f"circuit breaker open for {step}")
            result = fn()
            breakers[step].record_success()
            if attempt > 1:
                state.mark(step, f"retry_ok_attempt_{attempt}")
            return result
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            breakers[step].record_failure()
            state.errors.append(f"{step} attempt {attempt}: {type(exc).__name__}: {exc}")
            log_step(state.trace_id, step, attempt, "error", utcnow(), 0, str(exc)[:500])
            if attempt < attempts:
                time.sleep(settings.retry_base_delay_ms / 1000 * (2 ** (attempt - 1)))
    raise RuntimeError(f"Step {step} failed after {attempts} attempts: {last_exc}")


def _fallback_params(parsed: dict[str, Any]) -> dict[str, Any]:
    """Безопасные дефолты при неполных данных (пользователь может прервать Clarification Loop)."""
    cat = get_catalog()
    params = dict(parsed)
    if params.get("area_m2") is None:
        params["area_m2"] = 20.0
    if params.get("room_type") in (None, "другое"):
        params["room_type"] = "другое"
    if not params.get("work_scope"):
        params["work_scope"] = list(cat.typical(params["room_type"]).get("default_work_scope", []))
    params.setdefault("constraints", []).append("часть параметров принята по умолчанию — требуется проверка сметчиком")
    params["missing_fields"] = []
    return params


def _build_positions(params: dict[str, Any], state: PipelineState, smeta_id: str) -> list[Position]:
    cat = get_catalog()
    area = Decimal(str(params.get("area_m2") or 20))
    region = params.get("region", "Москва")
    seen: dict[str, Position] = {}
    search_latencies: list[float] = []
    for idx, hint in enumerate(params.get("work_scope", [])[:16]):
        try:
            m = with_retry("matching", lambda h=hint: match_query(h, trace_id=state.trace_id, smeta_id=smeta_id),
                           state, attempts=2)
        except RuntimeError:
            state.escalations.append(f"Сервис сопоставления недоступен для «{hint}» — позиция требует ручного подбора")
            continue
        search_latencies.append(m.latency_ms)
        if not m.catalog_id:
            state.escalations.append(f"Не найдена расценка для «{hint}» — эскалация сметчику")
            continue
        item = cat.get(m.catalog_id)
        if not item:  # защита от галлюцинаций: ссылка должна существовать
            state.escalations.append(f"Матчер вернул несуществующий catalog_id {m.catalog_id}")
            continue
        if m.catalog_id in seen:
            continue  # дедупликация позиций
        coeff = item.region_coeffs.get(region, "1.00") if item.region_coeffs else "1.00"
        pos = Position(
            id=str(uuid.uuid4()), catalog_id=item.id, name=item.name, unit=item.unit,
            quantity=cat.quantity(item, area), unit_price=item.base_price,
            coefficients={"region": coeff}, vat_rate=settings.vat_rate,
            confidence=m.confidence, status=m.status, source_query=hint, sort_order=idx,
            notes="" if m.status == "auto_accepted" else "Обязательная проверка сметчиком",
        )
        seen[item.id] = pos
    if search_latencies:
        log_step(state.trace_id, "search", 1, "ok", utcnow(), int(max(search_latencies)), None,
                 {"queries": len(search_latencies)}, {"p_max_ms": max(search_latencies)}, smeta_id)
        state.mark("search", "ok", int(max(search_latencies)))
    positions = sorted(seen.values(), key=lambda p: (p.catalog_id, p.sort_order))
    for i, p in enumerate(positions):
        p.sort_order = i
    # Сортируем по категории для читаемого документа
    positions.sort(key=lambda p: (cat.get(p.catalog_id).category if cat.get(p.catalog_id) else "", p.catalog_id))
    for i, p in enumerate(positions):
        p.sort_order = i
    return positions


def run_pipeline(*, text: str, actor: dict[str, Any], source_type: str = "text", client: str = "",
                 smeta_id: str | None = None, params_override: dict[str, Any] | None = None,
                 session_id: str | None = None, use_llm_judge: bool | None = None,
                 image: tuple[bytes, str, str] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    trace_id = str(uuid.uuid4())
    state = PipelineState(trace_id, actor)
    started = utcnow()
    state.mark("orchestrator", "started")

    # --- 1. Parser -----------------------------------------------------------
    if params_override:
        parsed_obj = ParsedRequest.model_validate(params_override)
        attempts: list[dict[str, Any]] = [{"attempt": 1, "status": "from_clarification", "source": "human"}]
        state.mark("parser", "ok_from_clarification")
    else:
        parsed_obj, attempts = parse_request(text, trace_id, source_type=source_type,
                                             actor=actor, smeta_id=smeta_id)
        state.mark("parser", "ok", 0, f"attempts={len(attempts)}")
    params = parsed_obj.model_dump()

    # --- 2. Vision/OCR (опционально) ----------------------------------------
    vision_result: dict[str, Any] | None = None
    if image:
        data, filename, mime = image
        vision_result = analyze_image(data, filename=filename, mime=mime, trace_id=trace_id, actor=actor)
        state.mark("vision", "ok" if vision_result.get("accepted") else "rejected", 0)
        for el in vision_result.get("elements", []):
            if el.get("type") == "площадь" and float(el.get("confidence", 0)) >= 0.5 and not params.get("area_m2"):
                params["area_m2"] = float(el["value"])
        if vision_result.get("degraded_to_manual"):
            state.escalations.append("Низкое качество фото: включён ручной ввод параметров")

    # --- 3. Создание/обновление сметы ---------------------------------------
    if not smeta_id:
        title = f"{params.get('room_type','объект')} {params.get('area_m2','?')} м² — {text[:60]}"
        smeta_id = create_smeta(title=title, client=client, region=params.get("region", "Москва"),
                                source_request=text[:8000], source_type=source_type,
                                actor=actor, trace_id=trace_id)
    else:
        db.execute("UPDATE smetas SET updated_at=?, region=? WHERE id=?",
                   (utcnow(), params.get("region", "Москва"), smeta_id))

    # --- 4. Clarification Loop ----------------------------------------------
    questions: list[dict[str, Any]] = []
    clarification_session_id = session_id
    pending = bool(parsed_obj.missing_fields) and not params_override
    if pending:
        session = start_session(params, smeta_id=smeta_id, trace_id=trace_id)
        clarification_session_id = session["session"]["id"]
        if session.get("question"):
            questions.append(session["question"])
        params = _fallback_params(params)
        state.mark("clarification", "awaiting_answer")
    else:
        state.mark("clarification", "not_required")
    if params.get("area_m2") is None:
        params["area_m2"] = 20.0
    if not params.get("work_scope"):
        params = _fallback_params(params)

    # --- 5. Search + Matching -> позиции ------------------------------------
    positions = _build_positions(params, state, smeta_id)
    state.mark("matching", "ok", 0, f"positions={len(positions)}")

    # --- 6. Calculation (только Decimal) ------------------------------------
    totals = with_retry("calculation", lambda: recalculate(positions), state)
    state.mark("calculation", totals.verification, 0, f"checksum={totals.checksum[:12]}")
    if totals.verification != "ok":
        state.escalations.append("Независимый пересчёт не совпал — смета заблокирована для утверждения")

    # --- 7. Validation -------------------------------------------------------
    issues, suggestions = with_retry(
        "validation",
        lambda: validate(positions, totals, params, trace_id=trace_id, smeta_id=smeta_id,
                         use_llm_judge=use_llm_judge), state)
    state.mark("validation", "ok", 0, f"issues={len(issues)}")

    # --- 8. Persistence (новая immutable-версия) -----------------------------
    version_no, _ = persist_version(
        smeta_id=smeta_id, positions=positions, totals=totals, params=params, actor=actor,
        reason="Правки после Clarification Loop" if params_override else "Первичный черновик сметы",
        trace_id=trace_id,
        extra={"issues": [i.__dict__ for i in issues], "suggestions": suggestions,
               "latency_ms": int((time.perf_counter() - t0) * 1000),
               "parser_attempts": attempts, "pipeline_steps": state.steps,
               "escalations": state.escalations, "vision": vision_result})
    status = "needs_clarification" if pending else "needs_review"
    set_status(smeta_id, status, actor)
    state.mark("document", "ready")

    # --- 9. Notification / эскалация ----------------------------------------
    notify(event="draft_ready", subject=f"Черновик сметы {smeta_id} готов",
           body=f"Версия v{version_no}: {len(positions)} позиций, требуется проверка человеком.",
           trace_id=trace_id)
    low_conf = [p for p in positions if p.status in ("escalated", "needs_review")]
    if low_conf:
        state.escalations.append(f"{len(low_conf)} позиций с confidence < порога — обязательная ручная проверка")
        notify(event="low_confidence", subject=f"Эскалация по смете {smeta_id}",
               body=f"{len(low_conf)} позиций требуют подтверждения сметчиком (confidence < {settings.match_auto_accept}).",
               trace_id=trace_id)
    for esc in state.escalations:
        log_step(trace_id, "orchestrator", 1, "escalation", utcnow(), 0, esc)
    if not llm.enabled:
        state.steps.append({"step": "llm", "status": "deterministic_fallback",
                            "duration_ms": 0, "detail": "GPU-инференс отключён: включён ручной/правиловый режим (ТЗ 8.2)"})

    latency_ms = int((time.perf_counter() - t0) * 1000)
    log_step(trace_id, "orchestrator", 1, "completed", started, latency_ms,
             None, {"text": text[:500]}, {"smeta_id": smeta_id, "version": version_no},
             smeta_id)
    audit(actor, "run_pipeline", "smeta", smeta_id,
          {"trace_id": trace_id, "version": version_no, "positions": len(positions), "latency_ms": latency_ms})
    result = load_estimate(smeta_id, version_no)
    assert result is not None
    result.update({
        "trace_id": trace_id, "questions": questions,
        "clarification_session_id": clarification_session_id,
        "pipeline_steps": state.steps, "errors": state.errors, "escalations": state.escalations,
        "parser_attempts": attempts, "vision": vision_result, "latency_ms": latency_ms,
        "llm_degraded": not llm.enabled,
    })
    return result

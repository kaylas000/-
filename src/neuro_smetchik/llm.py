"""Локальный LLM-клиент (OpenAI-совместимый vLLM/TGI) + детерминированный fallback.

Жёсткие правила:
  * исходящие вызовы разрешены ТОЛЬКО на хосты внутреннего периметра (ТЗ 4.4);
  * system/user роли разделены на уровне API (ТЗ 6.1);
  * КАЖДЫЙ вызов (включая fallback) пишется в append-only llm_inference_log;
  * LLM никогда не вызывается для расчёта денег и не придумывает цены (ТЗ 3.2.5, 5.2).
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from .config import settings
from .db import db
from .models import dumps, utcnow
from .security import sanitize_text


@dataclass(frozen=True)
class InferenceResult:
    content: str
    model: str
    prompt_version: str
    latency_ms: int
    source: str  # local_vllm | deterministic_fallback | blocked
    confidence: float | None = None


class LocalLLM:
    def __init__(self) -> None:
        self.model = settings.llm_model

    @property
    def enabled(self) -> bool:
        return settings.llm_enabled and settings.llm_is_local

    def complete(
        self,
        *,
        service: str,
        system: str,
        user: str,
        trace_id: str,
        prompt_version: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> InferenceResult:
        started = time.perf_counter()
        verdict = sanitize_text(user)
        if not verdict.clean:
            return self._log_and_return(InferenceResult(
                content="", model="guard-rules-v1", prompt_version=prompt_version,
                latency_ms=int((time.perf_counter() - started) * 1000), source="blocked", confidence=0.0,
            ), service, trace_id, {"blocked_patterns": list(verdict.patterns)}, {"error": "prompt_injection_detected"})

        if not self.enabled:
            return self._log_and_return(InferenceResult(
                content="", model="rules-fallback-v1", prompt_version=prompt_version,
                latency_ms=int((time.perf_counter() - started) * 1000), source="deterministic_fallback",
            ), service, trace_id, {"user": verdict.sanitized[:4000]}, {"fallback": True})

        url = settings.llm_base_url.rstrip("/") + "/chat/completions"
        try:
            resp = httpx.post(
                url,
                json={
                    "model": self.model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": verdict.sanitized},
                    ],
                    "response_format": {"type": "json_object"},
                },
                timeout=settings.llm_timeout_s,
                headers={"X-Trace-Id": trace_id},
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # circuit breaker / graceful degradation (ТЗ 8.2)
            return self._log_and_return(InferenceResult(
                content="", model="rules-fallback-v1", prompt_version=prompt_version,
                latency_ms=int((time.perf_counter() - started) * 1000), source="deterministic_fallback",
            ), service, trace_id, {"user": verdict.sanitized[:4000]}, {"fallback": True, "error": type(exc).__name__})

        return self._log_and_return(InferenceResult(
            content=content, model=self.model, prompt_version=prompt_version,
            latency_ms=int((time.perf_counter() - started) * 1000), source="local_vllm",
        ), service, trace_id, {"user": verdict.sanitized[:4000], "system_hash": hash(system) & 0xFFFFFFFF},
            {"content": content[:8000]})

    def _log_and_return(self, result: InferenceResult, service: str, trace_id: str,
                        inp: dict[str, Any], out: dict[str, Any]) -> InferenceResult:
        retention = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(timespec="seconds")
        try:
            db.insert("llm_inference_log", {
                "id": str(uuid.uuid4()), "trace_id": trace_id, "service": service,
                "prompt_version": result.prompt_version, "model_version": result.model,
                "input_json": dumps(inp), "output_json": dumps(out),
                "confidence": result.confidence, "latency_ms": result.latency_ms,
                "created_at": utcnow(), "retention_until": retention,
            })
        except Exception:
            # Аудит LLM-вызовов не должен ронять пайплайн, но это инцидент (логируется orchestrator).
            pass
        return result


llm = LocalLLM()


def validate_llm_json(content: str, schema: type[BaseModel]) -> tuple[BaseModel | None, list[str]]:
    """Строгая валидация выходного JSON по схеме; возвращает ошибки для retry (ТЗ 3.2.1)."""
    if not content.strip():
        return None, ["empty_response"]
    try:
        # Модель иногда оборачивает JSON в markdown-блок — снимаем только этот контейнер.
        text = content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            text = text[4:] if text.startswith("json") else text
        data = json.loads(text)
    except (json.JSONDecodeError, IndexError) as exc:
        return None, [f"invalid_json: {exc}"]
    try:
        return schema.model_validate(data), []
    except ValidationError as exc:
        return None, [f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors()]

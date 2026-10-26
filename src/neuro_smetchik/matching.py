"""Matching Service (ТЗ 3.2.4): confidence score + расширенный поиск + эскалация.

Пороги: >= 0.85 — авто-принятие; 0.5–0.85 — расширенный повторный поиск; < 0.5 — ручная проверка.
"""
from __future__ import annotations

import json
import time

from .config import settings
from .llm import llm
from .models import MatchResult
from .prompts import resolve
from .repository import log_step
from .search import get_search, tokens
from .models import utcnow

VAGUE_MARKERS = ("что-то", "что-нибудь", "красивый", "разные работы", "всё", "все работы",
                 "как-нибудь", "что угодно", "на усмотрение")

# Калибровка уверенности (обновляется на golden set, см. scripts/evaluate_golden.py)
W_BASE, W_SCORE, W_MARGIN, W_EXACT = 0.08, 0.86, 0.10, 0.06


def _confidence(top_score: float, second_score: float, exact_phrase: bool) -> float:
    margin = max(0.0, min(1.0, top_score - second_score))
    value = W_BASE + W_SCORE * top_score + W_MARGIN * margin + (W_EXACT if exact_phrase else 0.0)
    return round(max(0.0, min(0.99, value)), 3)


def match_query(query_text: str, *, trace_id: str, smeta_id: str | None = None,
                category: str | None = None, persist_log: bool = True) -> MatchResult:
    started = utcnow()
    t0 = time.perf_counter()
    search = get_search()
    hits = search.search(query_text, category=category)
    prompt = resolve("matching", trace_id)
    if not hits:
        if persist_log:
            log_step(trace_id, "matching", 1, "escalated", started,
                     int((time.perf_counter() - t0) * 1000), "no_candidates", {"query": query_text}, None,
                     smeta_id, prompt.version, "rules-matcher-v1")
        return MatchResult(None, 0.0, "escalated", "rules-matcher-v1",
                           round((time.perf_counter() - t0) * 1000, 2), query_text)

    top, second = hits[0], (hits[1] if len(hits) > 1 else None)
    exact = search._exact_phrase(query_text, top.item) > 0
    conf = _confidence(top.score, second.score if second else 0.0, exact)
    attempts = 1
    model_used = "rules-matcher-v1"
    # Слишком общая формулировка не может быть принята автоматически:
    # эскалация на ручную проверку (ТЗ 3.2.4, порог < 0.5).
    q_lower = query_text.lower()
    too_short = len(tokens(query_text)) < 2
    too_vague = any(marker in q_lower for marker in VAGUE_MARKERS)
    if too_vague:
        conf = round(min(conf, 0.42), 3)           # эскалация: бессмысленная формулировка
    elif too_short:
        conf = round(min(conf, 0.65), 3)           # неоднозначное однословное описание -> проверка
    conf_cap = too_vague or too_short

    # 0.5–0.85: расширенный повторный поиск по синонимам и категории
    if not conf_cap and settings.match_extended_search <= conf < settings.match_auto_accept:
        attempts += 1
        expanded = query_text + " " + " ".join(top.item.synonyms[:3]) + " " + top.item.category
        retry_hits = search.search(expanded, expand=True)
        if retry_hits:
            r_top, r_second = retry_hits[0], (retry_hits[1] if len(retry_hits) > 1 else None)
            r_conf = _confidence(r_top.score, r_second.score if r_second else 0.0,
                                 search._exact_phrase(query_text, r_top.item) > 0)
            if r_conf > conf:
                conf, top = r_conf, r_top

    # Опциональный LLM-реранк (каскад моделей), только локальный инференс
    if llm.enabled and top and not conf_cap:
        candidates = " | ".join(f"{h.catalog_id}: {h.item.name} ({h.item.unit})" for h in hits[:5])
        body = prompt.body.replace("{query_text}", query_text).replace("{candidates}", candidates)
        res = llm.complete(service="matching", system=body, user=query_text, trace_id=trace_id,
                           prompt_version=prompt.version)
        if res.source == "local_vllm":
            try:
                data = json.loads(res.content)
                llm_conf = float(data.get("confidence", 0))
                if 0 <= llm_conf <= 1:
                    conf = round(0.6 * conf + 0.4 * llm_conf, 3)
                    model_used = res.model
            except (ValueError, TypeError, json.JSONDecodeError):
                pass

    if conf_cap:
        conf = round(min(conf, 0.42 if too_vague else 0.65), 3)
    if conf >= settings.match_auto_accept:
        status = "auto_accepted"
    elif conf >= settings.match_extended_search:
        status = "needs_review"
    else:
        status = "escalated"
    latency = round((time.perf_counter() - t0) * 1000, 2)
    if persist_log:
        log_step(trace_id, "matching", attempts, status, started, int(latency), None,
                 {"query": query_text, "top_score": top.score, "prompt_version": prompt.version},
                 {"catalog_id": top.catalog_id, "confidence": conf, "attempts": attempts},
                 smeta_id, prompt.version, model_used)
    return MatchResult(top.catalog_id, conf, status, model_used, latency, query_text, attempts)

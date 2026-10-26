"""Parser Service (ТЗ 3.2.1): строгая JSON-схема, retry до 3 попыток, лог всех попыток.

В demo-режиме (LLM_ENABLED=false) используется детерминированный rule-based экстрактор:
он не требует GPU, полностью воспроизводим и служит fallback при недоступности инференса.
"""
from __future__ import annotations

import re
import time
from typing import Any

from pydantic import ValidationError

from .catalog import get_catalog
from .config import settings
from .llm import llm, validate_llm_json
from .models import ParsedRequest, dumps, utcnow
from .prompts import resolve
from .repository import log_step
from .search import tokens
from .security import audit, sanitize_text

CRITICAL_FIELDS = ("area_m2", "room_type", "work_scope")

# Порядок важен: «ванная» (помещение) не должна путаться с «ванна» (сантехника).
ROOM_PATTERNS: list[tuple[str, str]] = [
    ("ванная", r"\b(ванная|ванную|ванной|ванные|санузел|туалет)\b"),
    ("кухня", r"\b(кухня|кухню|кухни|кухонн\w*)\b"),
    ("офис", r"\b(офис\w*|переговорн\w*)\b"),
    ("коммерческое", r"\b(коммерческ\w*|магазин\w*|ресторан\w*|торгов\w*|склад\w*)\b"),
    ("квартира", r"\b(квартир\w*|новостройк\w*)\b|под ключ"),
    ("комната", r"\b(комнат\w*|гостин\w*|спальн\w*|детск\w*|коридор\w*|прихож\w*)\b"),
    ("дом", r"\b(дом|дома|дому|коттедж\w*|дач\w*)\b"),
]

AREA_RE = re.compile(
    r"(?<![\d.,])(\d{1,5}(?:[.,]\d{1,2})?)\s*(м²|м2|кв\.?\s*м\.?|квадратн\w*\s*метр\w*|кв\.?м)", re.I)
BARE_AREA_RE = re.compile(r"(?i)площад\w*\s*(?:помещени\w*\s*)?(?:составляет\s*)?(\d{1,5}(?:[.,]\d{1,2})?)")
BUDGET_RE = re.compile(
    r"(?i)(?:бюджет\w*|стоимость\w*|уложиться)\s*(?:до|не более|в пределах|в)?\s*"
    r"(\d{1,3}(?:[\s\u00a0]?\d{3})*(?:[.,]\d+)?)\s*(млн|миллион\w*|тыс\.?|тысяч\w*|руб\.?|рубл\w*|₽)")

# Разговорные формулировки -> канонические подсказки (дальше их разбирает Matching Service)
GENERIC_HINTS: list[tuple[tuple[str, ...], list[str]]] = [
    (("сантехник", "трубы", "водопровод", "канализац"), ["прокладка полипропиленовых труб", "монтаж канализационной трубы", "установка смесителя"]),
    (("электрик", "электромонтаж", "проводк", "электроточк"), ["штробление стен под проводку", "установка розеток и выключателей", "сборка электрощита"]),
    (("розет", "выключател"), ["установить розетки", "штробление стен под проводку"]),
    (("плитк", "кафел", "плиточн"), ["укладка кафеля", "затирка швов плитки", "гидроизоляция стен"]),
    (("штукатурк", "оштукатур", "выравниван"), ["штукатурка стен по маякам"]),
    (("шпаклевк", "шпатлевк", "зашпаклеват"), ["шпаклевка стен в 2 слоя", "шлифовка шпаклевки"]),
    (("покраск", "окраск", "малярн", "побелит"), ["окраска стен в 2 слоя", "грунтовка поверхностей"]),
    (("обо", "поклеит"), ["поклейка обоев"]),
    (("ламинат", "линолеум", "напольн", "полы", "настил"), ["укладка ламината", "монтаж напольного плинтуса"]),
    (("стяжк", "выровнять пол"), ["стяжка пола", "армирование стяжки"]),
    (("потолок", "потолочн", "потолк"), ["натяжной потолок", "установка точечных светильников"]),
    (("стены", "стену", "стене"), ["шпаклевка стен в 2 слоя", "окраска стен в 2 слоя"]),
    (("демонтаж", "снос", "снести"), ["демонтаж старой штукатурки", "вывоз строительного мусора"]),
    (("двер", "окн"), ["монтаж межкомнатной двери", "заделка оконных откосов"]),
    (("вентиляц", "воздуховод"), ["монтаж вентиляционного канала"]),
    (("гидроизоляц",), ["гидроизоляция пола"]),
    (("тёплый пол", "теплый пол"), ["устройство электрического тёплого пола"]),
    (("уборк",), ["уборка помещения после ремонта"]),
    (("капитальный ремонт", "ремонт под ключ", "полный ремонт"), ["штукатурка стен по маякам", "шпаклевка стен в 2 слоя", "окраска стен в 2 слоя", "укладка ламината", "штробление стен под проводку"]),
]

CONSTRAINT_PATTERNS = [
    (r"(?i)без демонтажа", "без демонтажа"),
    (r"(?i)только работу|только работы", "только работы (материалы заказчика)"),
    (r"(?i)без материалов", "без материалов"),
    (r"(?i)в выходные|по выходным", "работа в выходные"),
    (r"(?i)сдать за\s*(\d+\s*(?:нед|дн|мес)\w*)", "срок: {}"),
]


class UnsafeRequest(ValueError):
    pass


def _norm(text: str) -> str:
    return (text or "").lower().replace("ё", "е")


def _extract_area(text: str) -> float | None:
    m = AREA_RE.search(text)
    if not m:
        m2 = BARE_AREA_RE.search(text)
        if not m2:
            return None
        raw = m2.group(1)
    else:
        raw = m.group(1)
    return float(raw.replace(",", ".").replace(" ", ""))


def _extract_room(text: str) -> str:
    q = _norm(text) + " "
    for room, pattern in ROOM_PATTERNS:
        if re.search(pattern, q, re.I):
            return room
    return "другое"


def _extract_region(text: str) -> str:
    q = _norm(text)
    for region, keys in {
        "Санкт-Петербург": ("санкт-петербург", "спб", "петербург"),
        "Казань": ("казан",),
        "Екатеринбург": ("екатеринбург",),
        "Москва": ("москв", "московск"),
    }.items():
        if any(k in q for k in keys):
            return region
    return "Москва"


def _extract_budget(text: str) -> float | None:
    m = BUDGET_RE.search(text)
    if not m:
        return None
    value = float(m.group(1).replace(" ", "").replace("\u00a0", "").replace(",", "."))
    unit = (m.group(2) or "").lower()
    if unit.startswith(("млн", "миллион")):
        value *= 1_000_000
    elif unit.startswith(("тыс", "тысяч")) or value < 10_000:
        value *= 1_000
    return value


def extract_work_hints(text: str, room_type: str) -> list[str]:
    """Формулировки работ из запроса. Никаких цен и количеств — только текст."""
    cat = get_catalog()
    q = _norm(text)
    q_tokens = tokens(q)
    hints: list[str] = []
    # 1) Разговорные/обобщающие формулировки (канонические подсказки идут первыми)
    for triggers, canonical in GENERIC_HINTS:
        if any(t in q for t in triggers):
            hints.extend(canonical)
    # 2) Точное вхождение синонимов каталога
    for item in cat.items:
        for syn in item.synonyms:
            s = tokens(syn)
            if s and s.issubset(q_tokens):
                hints.append(syn)
                break
    # 3) Неопознанные/размытые формулировки передаём в Matching как есть:
    #    он обязан выставить низкий confidence и отправить позицию на ручную проверку.
    for marker in ("что-нибудь", "что-то", "на усмотрение", "и прочее", "прочие работы", "что угодно"):
        if marker in q:
            hints.append("уточнить объём работ: " + marker)
            break
    # 4) Если ничего не нашли — типовой состав работ по паттерну архива
    if not hints:
        hints = list(cat.typical(room_type).get("default_work_scope", []))
    # Дедупликация с сохранением порядка
    seen: set[str] = set()
    result: list[str] = []
    for h in hints:
        key = h.lower()
        if key not in seen:
            seen.add(key)
            result.append(h)
    return result[:16]


def deterministic_parse(text: str, source_type: str = "text") -> dict[str, Any]:
    area = _extract_area(text)
    room = _extract_room(text)
    hints = extract_work_hints(text, room)
    constraints: list[str] = []
    for pattern, label in CONSTRAINT_PATTERNS:
        m = re.search(pattern, text)
        if m:
            constraints.append(label.format(m.group(1)) if "{}" in label else label)
    parsed = {
        "room_type": room,
        "area_m2": area,
        "work_scope": hints,
        "region": _extract_region(text),
        "constraints": constraints,
        "urgency": "срочная" if re.search(r"(?i)срочно|срочный|как можно быстрее|в кратчайшие сроки", text) else "обычная",
        "budget_limit": _extract_budget(text),
        "source_type": source_type,
        "raw_text": text[:8000],
        "missing_fields": [],
    }
    parsed["missing_fields"] = compute_missing(parsed)
    return parsed


def compute_missing(parsed: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if parsed.get("area_m2") is None:
        missing.append("area_m2")
    if parsed.get("room_type") in (None, "другое"):
        missing.append("room_type")
    if not parsed.get("work_scope"):
        missing.append("work_scope")
    return missing


def parse_request(text: str, trace_id: str, *, source_type: str = "text",
                  actor: dict[str, Any] | None = None, max_retries: int | None = None,
                  smeta_id: str | None = None) -> tuple[ParsedRequest, list[dict[str, Any]]]:
    actor = actor or {"username": "system", "role": "estimator"}
    max_retries = max_retries or settings.parser_max_retries
    verdict = sanitize_text(text)
    if not verdict.clean:
        audit(actor, "prompt_injection_blocked", "request", smeta_id, {"patterns": list(verdict.patterns)}, severity="critical")
        log_step(trace_id, "parser", 1, "blocked", utcnow(), 0, "prompt_injection_detected",
                 {"patterns": list(verdict.patterns)}, None, smeta_id)
        raise UnsafeRequest("Запрос отклонён: обнаружена попытка prompt injection / извлечения системного промпта")
    clean_text = verdict.sanitized
    attempts: list[dict[str, Any]] = []
    prompt = resolve("parser", trace_id)
    schema_json = dumps(ParsedRequest.model_json_schema(), indent=2)[:6000]

    for attempt in range(1, max_retries + 1):
        started = utcnow()
        t0 = time.perf_counter()
        feedback = "" if not attempts else "\nОшибки прошлой попытки: " + "; ".join(attempts[-1]["errors"]) + ". Исправь их."
        system = prompt.body.replace("{schema}", schema_json)
        user = clean_text + feedback
        result = llm.complete(service="parser", system=system, user=user, trace_id=trace_id,
                              prompt_version=prompt.version)
        errors: list[str] = []
        parsed_obj: ParsedRequest | None = None
        if result.source == "local_vllm":
            parsed_obj, errors = validate_llm_json(result.content, ParsedRequest)
        else:
            try:
                raw = deterministic_parse(clean_text, source_type)
                parsed_obj = ParsedRequest.model_validate(raw)
                errors = [] if result.source != "blocked" else ["llm_guard_block"]
            except ValidationError as exc:  # pragma: no cover - защита детерминированного пути
                errors = [e["msg"] for e in exc.errors()]
        status = "ok" if parsed_obj and not errors else "retry"
        attempts.append({"attempt": attempt, "status": status, "source": result.source,
                         "errors": errors, "prompt_version": prompt.version,
                         "model": result.model, "latency_ms": result.latency_ms})
        log_step(trace_id, "parser", attempt, status, started, int((time.perf_counter() - t0) * 1000),
                 "; ".join(errors) or None, {"text": clean_text[:600], "attempt": attempt},
                 parsed_obj.model_dump() if parsed_obj else {"errors": errors}, smeta_id,
                 prompt.version, result.model)
        if parsed_obj and not errors:
            parsed_obj.missing_fields = compute_missing(parsed_obj.model_dump())
            return parsed_obj, attempts

    # Исчерпаны попытки -> детерминированный fallback (никогда не блокируем сметчика)
    raw = deterministic_parse(clean_text, source_type)
    final = ParsedRequest.model_validate(raw)
    attempts.append({"attempt": max_retries + 1, "status": "fallback", "source": "deterministic_fallback",
                     "errors": [], "prompt_version": prompt.version, "model": "rules-v1", "latency_ms": 0})
    log_step(trace_id, "parser", max_retries + 1, "fallback", utcnow(), 0,
             "llm_attempts_exhausted", {"text": clean_text[:600]}, final.model_dump(), smeta_id,
             prompt.version, "rules-v1")
    return final, attempts

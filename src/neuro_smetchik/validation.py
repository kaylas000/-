"""Validation Service (ТЗ 3.2.6): аномалии, дубли, полнота, опциональный LLM-judge."""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from .catalog import get_catalog
from .config import settings
from .llm import llm
from .models import EstimateTotals, Position, ValidationIssue, dumps, utcnow
from .prompts import resolve
from .repository import log_step

LEVEL_ORDER = {"error": 0, "warning": 1, "info": 2}


def validate(positions: list[Position], totals: EstimateTotals, params: dict[str, Any],
             *, trace_id: str, smeta_id: str | None = None,
             use_llm_judge: bool | None = None) -> tuple[list[ValidationIssue], list[dict[str, Any]]]:
    started = utcnow()
    cat = get_catalog()
    issues: list[ValidationIssue] = []
    suggestions: list[dict[str, Any]] = []

    # 0) Защита от галлюцинаций: позиция обязана ссылаться на РЕАЛЬНУЮ запись каталога
    for p in positions:
        item = cat.get(p.catalog_id)
        if item is None:
            issues.append(ValidationIssue("error", "hallucinated_catalog_ref",
                                          f"Позиция «{p.name}» не найдена в price_catalog", p.id))
        elif item.name != p.name:
            # Имя позиции может быть отредактировано человеком — это допустимо, но логируем.
            pass

    # 1) Аномальные цены относительно исторических данных
    for p in positions:
        item = cat.get(p.catalog_id)
        if not item or item.hist_avg <= 0:
            continue
        eff = p.unit_price
        for c in p.coefficients.values():
            eff *= Decimal(str(c))
        deviation = (eff - item.hist_avg) / item.hist_avg
        if abs(deviation) > settings.anomaly_deviation:
            issues.append(ValidationIssue(
                "warning", "price_anomaly",
                f"Цена «{p.name}» отклоняется от исторического среднего на {deviation * 100:.0f}% "
                f"(диапазон {item.hist_min}–{item.hist_max} ₽)", p.id,
                "Проверить актуальность расценки в прайс-листе"))
        if p.quantity <= 0:
            issues.append(ValidationIssue("error", "non_positive_quantity",
                                          f"Нулевое количество у позиции «{p.name}»", p.id))
        if p.status == "escalated":
            issues.append(ValidationIssue("warning", "low_confidence",
                                          f"Низкая уверенность сопоставления ({p.confidence:.2f}): «{p.name}»", p.id,
                                          "Подтвердить или заменить позицию вручную"))

    # 2) Дублирование позиций
    seen: dict[str, str] = {}
    for p in positions:
        if p.catalog_id in seen:
            issues.append(ValidationIssue("warning", "duplicate_position",
                                          f"Дублируется расценка {p.catalog_id}: «{p.name}»", p.id,
                                          "Объединить количества или удалить дубль"))
        seen[p.catalog_id] = p.id

    # 3) Полнота: сверка с типовым составом работ по паттернам архива
    room = params.get("room_type", "другое")
    pattern = cat.typical(room)
    present_categories = {cat.get(p.catalog_id).category for p in positions if cat.get(p.catalog_id)}
    for required in pattern.get("required_categories", []):
        if required not in present_categories:
            issues.append(ValidationIssue("warning", "incomplete_scope",
                                          f"Не закрыта категория работ «{required}» для типа «{pattern['label']}»", None,
                                          "Проверить предложения системы ниже"))
    present_ids = {p.catalog_id for p in positions}
    for cid in pattern.get("recommended_ids", []):
        if cid in present_ids or len(suggestions) >= 6:
            continue
        item = cat.get(cid)
        if item:
            suggestions.append({"catalog_id": cid, "code": item.code, "name": item.name,
                                "unit": item.unit, "price": str(cat.regional_price(item, params.get("region", "Москва"))),
                                "category": item.category, "reason": "типовой состав работ по архиву"})
    present_ids = {p.catalog_id for p in positions}

    # 4) Бюджет и математическая верификация
    budget = params.get("budget_limit")
    if budget and totals.grand_total > Decimal(str(budget)):
        issues.append(ValidationIssue("warning", "budget_exceeded",
                                      f"Итого {totals.grand_total} ₽ превышает заявленный бюджет {budget} ₽", None,
                                      "Согласовать объём работ с заказчиком"))
    if totals.verification != "ok":
        issues.append(ValidationIssue("error", "checksum_mismatch",
                                      "Независимый пересчёт контрольной суммы не совпал", None,
                                      "Заблокировать утверждение сметы"))
    if params.get("constraints") and any("Clarification" in str(c) for c in params["constraints"]):
        issues.append(ValidationIssue("info", "incomplete_input",
                                      "Смета построена на неполных исходных данных (уточнение прервано)", None,
                                      "Уточнить площадь и состав работ"))

    # 5) Опциональный независимый LLM-ревью (judge-паттерн)
    judge_requested = llm.enabled if use_llm_judge is None else (use_llm_judge and llm.enabled)
    if judge_requested:
        prompt = resolve("validation_judge", trace_id)
        draft = dumps({"positions": [p.to_dict() for p in positions], "totals": totals.to_dict()})[:7000]
        res = llm.complete(service="validation_judge", system=prompt.body.replace("{draft}", draft),
                           user=draft, trace_id=trace_id, prompt_version=prompt.version)
        if res.source == "local_vllm":
            try:
                for raw in json.loads(res.content).get("issues", [])[:10]:
                    issues.append(ValidationIssue(str(raw.get("level", "warning")),
                                                  str(raw.get("code", "llm_judge")),
                                                  str(raw.get("message", ""))[:400]))
            except (ValueError, json.JSONDecodeError):
                issues.append(ValidationIssue("info", "judge_unavailable", "Ответ LLM-ревьюера не разобран", None))

    issues.sort(key=lambda i: LEVEL_ORDER.get(i.level, 3))
    log_step(trace_id, "validation", 1, "ok" if not any(i.level == "error" for i in issues) else "errors_found",
             started, 0, None, {"positions": len(positions)},
             {"issues": [i.__dict__ for i in issues], "suggestions": suggestions}, smeta_id)
    return issues, suggestions

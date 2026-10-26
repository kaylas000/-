"""Доменные модели и строгие схемы (ТЗ 3.2.1: обязательная валидация JSON)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StrictModel(BaseModel):
    """Запрет неизвестных полей = жёсткая схема ответа LLM."""

    model_config = ConfigDict(extra="forbid")


class ParsedRequest(StrictModel):
    """Выход Parser Service. Любое отклонение -> retry (до 3 попыток)."""

    room_type: Literal["квартира", "комната", "ванная", "кухня", "офис", "коммерческое", "дом", "другое"] = "другое"
    area_m2: float | None = None
    work_scope: list[str] = Field(default_factory=list, max_length=40)
    region: str = "Москва"
    constraints: list[str] = Field(default_factory=list, max_length=20)
    urgency: Literal["обычная", "срочная"] = "обычная"
    budget_limit: float | None = None
    source_type: Literal["text", "voice", "photo", "scan"] = "text"
    raw_text: str = ""
    missing_fields: list[str] = Field(default_factory=list)

    @field_validator("area_m2")
    @classmethod
    def _check_area(cls, v: float | None) -> float | None:
        if v is not None and not (1 <= v <= 100_000):
            raise ValueError("area_m2 must be between 1 and 100000")
        return v

    @field_validator("budget_limit")
    @classmethod
    def _check_budget(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("budget_limit must be positive")
        return v


# ---------------------------------------------------------------------------
# Domain dataclasses (внутренние; деньги — ТОЛЬКО Decimal)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CatalogItem:
    id: str
    code: str
    name: str
    unit: str
    category: str
    base_price: Decimal
    synonyms: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    qty_rule: dict[str, Any] = field(default_factory=dict)
    rooms: tuple[str, ...] = ()
    hist_min: Decimal = Decimal("0")
    hist_avg: Decimal = Decimal("0")
    hist_max: Decimal = Decimal("0")
    region_coeffs: dict[str, str] = field(default_factory=dict)
    source_id: str = ""
    valid_from: str = ""
    updated_at: str = ""

    @property
    def searchable(self) -> str:
        return " ".join([self.name, " ".join(self.synonyms), " ".join(self.tags), self.category, self.code]).lower()


@dataclass(frozen=True)
class SearchHit:
    catalog_id: str
    score: float
    semantic_score: float
    keyword_score: float
    latency_ms: float
    item: CatalogItem


@dataclass(frozen=True)
class MatchResult:
    catalog_id: str | None
    confidence: float
    status: str  # auto_accepted | needs_review | escalated
    model_used: str
    latency_ms: float
    query_text: str
    attempts: int = 1


@dataclass
class Position:
    id: str
    catalog_id: str  # ОБЯЗАТЕЛЬНАЯ ссылка на price_catalog (ТЗ 5.2)
    name: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    coefficients: dict[str, str] = field(default_factory=dict)
    subtotal: Decimal = Decimal("0")
    vat_rate: Decimal = Decimal("0.20")
    vat_amount: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    confidence: float = 0.0
    status: str = "needs_review"
    source_query: str = ""
    notes: str = ""
    sort_order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return jsonable(self)


@dataclass
class EstimateTotals:
    subtotal: Decimal = Decimal("0")
    overhead: Decimal = Decimal("0")
    profit: Decimal = Decimal("0")
    vat: Decimal = Decimal("0")
    grand_total: Decimal = Decimal("0")
    checksum: str = ""
    verification: str = "pending"  # ok | mismatch

    def to_dict(self) -> dict[str, Any]:
        return jsonable(self)


@dataclass(frozen=True)
class ValidationIssue:
    level: str  # error | warning | info
    code: str
    message: str
    position_id: str | None = None
    suggestion: str | None = None


@dataclass
class EstimateDraft:
    smeta_id: str
    version_no: int
    title: str
    status: str
    params: dict[str, Any]
    positions: list[Position]
    totals: EstimateTotals
    issues: list[ValidationIssue]
    suggestions: list[dict[str, Any]]
    trace_id: str
    created_at: str
    latency_ms: int
    questions: list[dict[str, Any]] = field(default_factory=list)
    clarification_session_id: str | None = None
    escalations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return jsonable(self)


class Role(str, Enum):
    CLIENT = "client"
    ESTIMATOR = "estimator"
    MANAGER = "manager"
    ADMIN = "admin"


def jsonable(obj: Any) -> Any:
    """Decimal -> строка (никогда float), dataclass/pydantic/enum -> JSON."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, StrictModel) or isinstance(obj, BaseModel):
        return jsonable(obj.model_dump())
    if is_dataclass(obj) and not isinstance(obj, type):
        return {k: jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def dumps(obj: Any, **kwargs: Any) -> str:
    return json.dumps(jsonable(obj), ensure_ascii=False, **kwargs)


def loads(text: str | None, default: Any = None) -> Any:
    if text is None or text == "":
        return default if default is not None else {}
    return json.loads(text)

"""Централизованная конфигурация. Все пороги — настраиваемые (ТЗ 3.2.9)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]


def _dec(name: str, default: str) -> Decimal:
    return Decimal(os.getenv(name, default))


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "dev"))
    db_path: Path = field(default_factory=lambda: ROOT / os.getenv("DB_PATH", "data/neuro_smetchik.db"))

    # LLM — только локальный контур
    llm_enabled: bool = field(default_factory=lambda: os.getenv("LLM_ENABLED", "false").lower() == "true")
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "http://127.0.0.1:8001/v1"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "qwen2.5-32b-instruct"))
    llm_timeout_s: int = field(default_factory=lambda: _int("LLM_TIMEOUT_S", 20))
    llm_allowed_hosts: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            h.strip() for h in os.getenv("LLM_ALLOWED_HOSTS", "127.0.0.1,localhost,vllm,llm,host.docker.internal").split(",")
        )
    )

    # Пороги matching / clarification / retry
    match_auto_accept: Decimal = field(default_factory=lambda: _dec("MATCH_AUTO_ACCEPT", "0.85"))
    match_extended_search: Decimal = field(default_factory=lambda: _dec("MATCH_EXTENDED_SEARCH", "0.50"))
    max_clarification_turns: int = field(default_factory=lambda: _int("MAX_CLARIFICATION_TURNS", 5))
    parser_max_retries: int = field(default_factory=lambda: _int("PARSER_MAX_RETRIES", 3))
    search_top_n: int = field(default_factory=lambda: _int("SEARCH_TOP_N", 8))
    search_sla_ms: int = field(default_factory=lambda: _int("SEARCH_SLA_MS", 500))
    draft_sla_p95_ms: int = field(default_factory=lambda: _int("DRAFT_SLA_P95_MS", 60000))
    retry_base_delay_ms: int = 50
    circuit_breaker_threshold: int = 3

    # Деньги
    vat_rate: Decimal = field(default_factory=lambda: _dec("DEFAULT_VAT_RATE", "0.20"))
    overhead: Decimal = field(default_factory=lambda: _dec("DEFAULT_OVERHEAD", "0.12"))
    profit: Decimal = field(default_factory=lambda: _dec("DEFAULT_PROFIT", "0.08"))
    four_eyes_threshold: Decimal = field(default_factory=lambda: _dec("FOUR_EYES_THRESHOLD", "500000"))
    anomaly_deviation: Decimal = field(default_factory=lambda: _dec("ANOMALY_DEVIATION", "0.35"))

    # Безопасность / шаблон
    rate_limit_per_min: int = field(default_factory=lambda: _int("RATE_LIMIT_PER_MIN", 120))
    max_upload_mb: int = field(default_factory=lambda: _int("MAX_UPLOAD_MB", 15))
    company_name: str = field(default_factory=lambda: os.getenv("COMPANY_NAME", "ООО «СтройИнвест»"))
    company_inn: str = field(default_factory=lambda: os.getenv("COMPANY_INN", "7700000000"))

    @property
    def llm_host(self) -> str:
        return urlparse(self.llm_base_url).hostname or ""

    @property
    def llm_is_local(self) -> bool:
        """Жёсткая проверка сетевой изоляции (ТЗ 4.4, 12/кр. 4)."""
        return self.llm_host in self.llm_allowed_hosts


settings = Settings()

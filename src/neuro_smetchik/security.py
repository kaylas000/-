"""Безопасность: RBAC, аудит (hash-chain), rate limiting, защита от injection (ТЗ 6, 6.6)."""
from __future__ import annotations

import hashlib
import re
import time
import unicodedata
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from .config import settings
from .db import db
from .models import dumps, utcnow

# ---------------------------------------------------------------------------
# 6.1 Prompt injection / извлечение системного промпта
# ---------------------------------------------------------------------------
INJECTION_PATTERNS = [
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts)", "ignore_previous_instructions"),
    (r"(?i)(забудь|игнорируй|отмени)\s+(все\s+)?(предыдущие|системные|свои)\s+(инструкции|указания|правила)", "ru_ignore_instructions"),
    (r"(?i)(show|print|reveal|repeat|выведи|покажи|раскрой|повтори)\s+(me\s+)?(the\s+)?(your\s+)?(system\s+prompt|системн\w*\s+промпт|системн\w*\s+инструкц\w*)", "system_prompt_extraction"),
    (r"(?i)(developer\s+mode|режим\s+разработчика|jailbreak|DAN\b)", "jailbreak"),
    (r"(?i)(disregard|override)\s+(the\s+)?(rules|safety|schema)", "rule_override"),
    (r"(?i)(curl|wget|http[s]?://|fetch\s+the\s+url|exec\()", "tool_or_network_abuse"),
]

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\u200b-\u200f\u202a-\u202e\u2066-\u2069\ufeff]")


@dataclass(frozen=True)
class SecurityVerdict:
    clean: bool
    sanitized: str
    patterns: tuple[str, ...] = ()


def sanitize_text(text: str, *, strict: bool = True) -> SecurityVerdict:
    """Санитизация + детекция попыток injection. При strict=False внешние URL не блокируются
    (используется для технических полей), но управляющие символы удаляются всегда."""
    cleaned = unicodedata.normalize("NFKC", text or "")
    cleaned = CONTROL_CHARS.sub(" ", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    found: list[str] = []
    for pattern, code in INJECTION_PATTERNS:
        if code == "tool_or_network_abuse" and not strict:
            continue
        if re.search(pattern, cleaned):
            found.append(code)
    return SecurityVerdict(clean=not found, sanitized=cleaned, patterns=tuple(found))


# ---------------------------------------------------------------------------
# 6.2 RBAC / MFA / append-only аудит
# ---------------------------------------------------------------------------
PERMISSIONS: dict[str, tuple[str, ...]] = {
    "client": ("estimate:read", "request:create"),
    "estimator": ("estimate:read", "estimate:write", "estimate:approve", "request:create", "catalog:read", "prompt:read"),
    "manager": ("estimate:read", "estimate:approve:second", "metrics:read", "audit:read", "catalog:read", "prompt:read", "prompt:write"),
    "admin": ("*",),
}

MFA_REQUIRED = {"manager", "admin"}


def check_permission(role: str, permission: str, *, mfa: bool = False) -> bool:
    perms = PERMISSIONS.get(role, ())
    if "*" in perms:
        return True
    if permission not in perms:
        return False
    if role in MFA_REQUIRED and permission.startswith(("estimate:approve:second", "audit", "prompt:write")) and not mfa:
        return False
    return True


class PermissionDenied(Exception):
    pass


def require(actor: dict[str, Any], permission: str) -> dict[str, Any]:
    role = actor.get("role", "client")
    if not check_permission(role, permission, mfa=bool(actor.get("mfa"))):
        audit(actor, "permission_denied", "security", permission, severity="warning")
        raise PermissionDenied(f"Роль {role!r} не имеет права {permission!r} (или не пройдена MFA)")
    return actor


# ---------------------------------------------------------------------------
# Append-only журнал безопасности с цепочкой хэшей (неизменяемость)
# ---------------------------------------------------------------------------
def _hash_row(prev: str, payload: str) -> str:
    return hashlib.sha256(f"{prev}|{payload}".encode("utf-8")).hexdigest()


def audit(actor: dict[str, Any], action: str, entity: str, entity_id: str | None = None,
          details: Any = None, severity: str = "info", ip: str | None = None) -> None:
    if not __import__("os").getenv("AUDIT_ENABLED", "true").lower() == "true":
        return
    # read + insert атомарны: иначе два потока могут получить одинаковый prev_hash
    # и нарушить хэш-цепочку. RLock безопасен при вложенных transaction().
    with db._write_lock:
        last = db.one("SELECT hash FROM security_audit_log ORDER BY id DESC LIMIT 1")
        prev = last["hash"] if last else "0" * 64
        ts = utcnow()
        detail_str = dumps(details) if details is not None else None
        # Нормализуем поля ДО хэширования: payload должен совпадать с сохранённой строкой.
        actor_name = actor.get("username") or "anonymous"
        role_name = actor.get("role") or "client"
        payload = dumps({"ts": ts, "actor": actor_name, "role": role_name,
                         "action": action, "entity": entity, "entity_id": entity_id, "details": detail_str})
        digest = _hash_row(prev, payload)
        db.insert("security_audit_log", {
            "ts": ts, "actor": actor_name, "role": role_name,
            "action": action, "entity": entity, "entity_id": entity_id, "ip": ip,
            "details": detail_str, "severity": severity, "prev_hash": prev, "hash": digest,
        })


def verify_audit_chain() -> tuple[bool, int]:
    rows = db.all("SELECT * FROM security_audit_log ORDER BY id")
    prev = "0" * 64
    for row in rows:
        payload = dumps({"ts": row["ts"], "actor": row["actor"], "role": row["role"],
                         "action": row["action"], "entity": row["entity"], "entity_id": row["entity_id"],
                         "details": row["details"]})
        if row["prev_hash"] != prev or _hash_row(prev, payload) != row["hash"]:
            return False, row["id"]
        prev = row["hash"]
    return True, len(rows)


# ---------------------------------------------------------------------------
# 6.6 Rate limiting / загрузка файлов
# ---------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, limit: int, window_s: int = 60) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = __import__("threading").Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window_s:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


rate_limiter = RateLimiter(settings.rate_limit_per_min)

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp", "application/pdf", "image/tiff"}
MAGIC = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG": "image/png",
    b"RIFF": "image/webp",
    b"%PDF": "application/pdf",
}


def validate_upload(data: bytes, declared_mime: str, filename: str) -> tuple[bool, str]:
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        return False, f"Файл больше {settings.max_upload_mb} МБ"
    if declared_mime not in ALLOWED_MIME:
        return False, f"Недопустимый MIME-тип: {declared_mime}"
    detected = next((mime for magic, mime in MAGIC.items() if data.startswith(magic)), None)
    if detected is None or detected != declared_mime:
        return False, "Magic bytes не совпадают с заявленным MIME (возможная подмена)"
    # EXIF prompt injection (ТЗ 6.6): санитизируем имя и проверяем метаданные
    if CONTROL_CHARS.search(filename) or re.search(r"(?i)(system|prompt|ignore)", filename):
        return False, "Подозрительное имя файла (возможна EXIF/metadata injection)"
    if b"ignore previous" in data[:65536].lower() or b"system prompt" in data[:65536].lower():
        return False, "В метаданных файла обнаружена попытка prompt injection"
    return True, "ok"

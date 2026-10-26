"""Notification Service (ТЗ v1.1 3.2.11): приоритеты, подписки по ролям, журнал."""
from __future__ import annotations

import uuid
from typing import Any

from .db import db
from .models import utcnow

RULES: dict[str, tuple[str, ...]] = {
    "low_confidence": ("estimator", "manager"),
    "clarification_timeout": ("estimator",),
    "draft_ready": ("estimator",),
    "approval_required": ("manager", "admin"),
    "drift_alert": ("admin", "manager"),
    "security": ("admin",),
    "freshness": ("estimator", "manager"),
}
PRIORITY = {"security": "high", "drift_alert": "high", "low_confidence": "high",
            "approval_required": "high", "clarification_timeout": "normal",
            "draft_ready": "low", "freshness": "normal"}


def notify(*, recipient: str | None = None, channel: str = "ui", priority: str = "normal",
           subject: str, body: str, trace_id: str | None = None, event: str | None = None) -> list[str]:
    recipients = [recipient] if recipient else list(RULES.get(event or "", ("estimator",)))
    priority = PRIORITY.get(event or "", priority)
    ids: list[str] = []
    for r in recipients:
        nid = str(uuid.uuid4())
        db.insert("notifications", {
            "id": nid, "recipient": r, "channel": channel, "priority": priority,
            "subject": subject, "body": body, "trace_id": trace_id,
            "created_at": utcnow(), "read_at": None,
        })
        ids.append(nid)
    # email/messenger — адаптеры self-hosted; в MVP пишут в тот же журнал с channel=email
    if priority == "high" and channel == "ui":
        for r in recipients:
            db.insert("notifications", {
                "id": str(uuid.uuid4()), "recipient": r, "channel": "email", "priority": priority,
                "subject": subject, "body": body, "trace_id": trace_id,
                "created_at": utcnow(), "read_at": None,
            })
    return ids


def inbox(role: str, *, unread_only: bool = False, limit: int = 50) -> list[dict[str, Any]]:
    sql = "SELECT * FROM notifications WHERE recipient=? OR recipient='estimator'"
    params: list[Any] = [role]
    if unread_only:
        sql += " AND read_at IS NULL"
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    return db.all(sql, tuple(params))


def mark_read(notification_id: str) -> None:
    db.execute("UPDATE notifications SET read_at=? WHERE id=?", (utcnow(), notification_id))

"""Фоновый воркер циклов обратной связи (MVP-замена Celery beat).

В проде заменяется на Celery/RQ + Redis с отдельными задачами:
daily_drift_check, weekly_catalog_refresh, notification_delivery.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timezone

from .catalog import get_catalog
from .loops import drift_check
from .notifications import notify
from .scripts_init import ensure_initialized


def main() -> None:
    ensure_initialized()
    print("Worker started: Model Drift Loop (daily) + Data Freshness Loop (weekly)", flush=True)
    last_drift: date | None = None
    last_iso_week: tuple[int, int] | None = None
    while True:
        now = datetime.now(timezone.utc)
        today = now.date()
        iso = now.isocalendar()
        if last_drift != today:
            try:
                report = drift_check()
                print(f"[{today}] drift: {report['verdict']} (delta {report['delta_pct']}%)", flush=True)
                last_drift = today
            except Exception as exc:  # noqa: BLE001
                print(f"[{today}] drift failed: {exc}", flush=True)
        if last_iso_week != (iso[0], iso[1]):
            try:
                result = get_catalog().freshness_check()
                print(f"[{today}] freshness: {result['checked_items']} items, {result['anomalies']} anomalies", flush=True)
                if result["anomalies"]:
                    notify(event="freshness", subject="Каталог требует актуализации",
                           body=f"Обнаружено {result['anomalies']} устаревших/аномальных позиций.",
                           trace_id="worker-freshness")
                last_iso_week = (iso[0], iso[1])
            except Exception as exc:  # noqa: BLE001
                print(f"[{today}] freshness failed: {exc}", flush=True)
        time.sleep(3600)


if __name__ == "__main__":
    main()

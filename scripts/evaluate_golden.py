#!/usr/bin/env python3
"""Regression-тест качества на golden set (ТЗ 8.5, Этап 0 DoD)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neuro_smetchik.scripts_init import ensure_initialized  # noqa: E402
from neuro_smetchik.loops import evaluate_golden  # noqa: E402
from neuro_smetchik.db import db  # noqa: E402
from neuro_smetchik.models import utcnow  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="Подробный отчёт")
    parser.add_argument("--write", action="store_true", help="Сохранить baseline и drift_checks")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    ensure_initialized()
    report = evaluate_golden(limit=args.limit, trace_id="cli-golden")
    print(json.dumps({k: v for k, v in report.items() if k != "failures"}, ensure_ascii=False, indent=2))
    if args.report or not report["pass"]:
        print("\nПримеры ошибок:")
        for f in report["failures"][:15]:
            print(" -", json.dumps(f, ensure_ascii=False))
    if args.write:
        model = db.one("SELECT * FROM model_versions WHERE status='active' ORDER BY loaded_at DESC LIMIT 1")
        if model:
            db.execute("UPDATE model_versions SET golden_accuracy=? WHERE id=?",
                       (report["matching_top1_accuracy"], model["id"]))
        db.insert("drift_checks", {
            "id": f"baseline-{utcnow()[:10]}", "checked_at": utcnow(),
            "model_version": model["name"] if model else "rules-fallback-v1",
            "golden_accuracy": report["matching_top1_accuracy"], "baseline": report["matching_top1_accuracy"],
            "delta_pct": 0.0, "verdict": "baseline_set",
        })
        print(f"\nBaseline зафиксирован: {report['matching_top1_accuracy']}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

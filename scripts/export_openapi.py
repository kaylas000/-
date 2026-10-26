#!/usr/bin/env python3
"""Экспорт OpenAPI-спецификации (Приложение Г) в openapi/neuro-smetchik.yaml."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402
from neuro_smetchik.api import app  # noqa: E402

if __name__ == "__main__":
    out = ROOT / "openapi" / "neuro-smetchik.yaml"
    out.parent.mkdir(exist_ok=True)
    spec = app.openapi()
    out.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"OK: {out} ({len(spec['paths'])} путей, {len(spec['components']['schemas'])} схем)")

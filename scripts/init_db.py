#!/usr/bin/env python3
"""Создать схему БД и загрузить справочники. Запуск: .venv/bin/python scripts/init_db.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neuro_smetchik.scripts_init import ensure_initialized  # noqa: E402
from neuro_smetchik.catalog import get_catalog  # noqa: E402
from neuro_smetchik.db import db  # noqa: E402

if __name__ == "__main__":
    ensure_initialized()
    cat = get_catalog()
    print(f"БД: {db.path}")
    print(f"Позиций в каталоге: {len(cat.items)}; категорий: {len(cat.coverage()['by_category'])}")
    print(f"Golden-примеров: {db.one('SELECT COUNT(*) AS c FROM golden_examples')['c']}")
    print(f"Промптов: {db.one('SELECT COUNT(*) AS c FROM prompt_versions')['c']}")

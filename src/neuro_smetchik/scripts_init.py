"""Инициализация при старте API: данные -> схема -> справочники -> baseline."""
from __future__ import annotations

import runpy
import uuid

from .config import ROOT
from .db import db
from .models import utcnow

DATA = ROOT / "data"


def ensure_initialized() -> None:
    import neuro_smetchik.catalog as catmod
    import neuro_smetchik.search as searchmod

    needed = [DATA / "price_catalog.json", DATA / "typical_compositions.json", DATA / "golden_set.json"]
    if not all(p.exists() for p in needed):
        runpy.run_path(str(ROOT / "scripts" / "build_catalog.py"), run_name="__main__")
        catmod.catalog = None
        searchmod._search = None
    db.init_schema()
    from .catalog import get_catalog
    cat = get_catalog()
    cat.seed()
    from .prompts import seed_prompts
    seed_prompts()
    if not db.one("SELECT id FROM model_versions LIMIT 1"):
        db.insert("model_versions", {
            "id": str(uuid.uuid4()), "name": "rules-fallback-v1" if not _llm_enabled() else _model_name(),
            "weights_hash": "n/a-deterministic-rules", "license": "internal",
            "loaded_at": utcnow(), "golden_accuracy": None, "status": "active",
        })
    if not db.one("SELECT id FROM knowledge_base_versions LIMIT 1"):
        cat.seed()


def _llm_enabled() -> bool:
    from .config import settings
    return settings.llm_enabled


def _model_name() -> str:
    from .config import settings
    return settings.llm_model

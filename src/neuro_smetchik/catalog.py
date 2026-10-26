"""Каталог расценок: загрузка, правила расчёта количеств, актуальность цен (ТЗ 7, Data Freshness Loop)."""
from __future__ import annotations

import hashlib
import json
import uuid
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from .config import ROOT
from .db import db
from .models import CatalogItem, dumps, utcnow

DATA = ROOT / "data"
Q = Decimal("0.01")


def _d(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


class Catalog:
    def __init__(self, path: Path | None = None) -> None:
        path = Path(path or DATA / "price_catalog.json")
        if not path.exists():
            raise FileNotFoundError("Сначала выполните: python scripts/build_catalog.py && python scripts/init_db.py")
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.items: list[CatalogItem] = []
        for r in raw:
            self.items.append(CatalogItem(
                id=r["id"], code=r["code"], name=r["name"], unit=r["unit"], category=r["category"],
                base_price=_d(r["base_price"]), synonyms=tuple(r.get("synonyms", [])),
                tags=tuple(r.get("tags", [])), qty_rule=r.get("qty_rule", {}),
                rooms=tuple(r.get("rooms", [])), hist_min=_d(r.get("hist_min", 0)),
                hist_avg=_d(r.get("hist_avg", 0)), hist_max=_d(r.get("hist_max", 0)),
                region_coeffs=r.get("region_coeffs", {}), source_id=r.get("source_id", ""),
                valid_from=r.get("valid_from", ""), updated_at=r.get("updated_at", ""),
            ))
        self.by_id = {i.id: i for i in self.items}
        self.compositions: dict[str, Any] = json.loads((DATA / "typical_compositions.json").read_text(encoding="utf-8"))
        self.hash = hashlib.sha256(path.read_bytes()).hexdigest()[:16]

    # -------------------------------------------------------------- seeding
    def seed(self) -> None:
        with db.transaction() as tx:
            tx.execute(
                "INSERT OR IGNORE INTO rate_catalog_sources(id,name,license,legal_status,url,checked_at,responsible) "
                "VALUES (?,?,?,?,?,?,?)",
                ("SRC-DEMO", "Демонстрационный синтетический прайс (НЕ ГЭСН/ФЕР)",
                 "internal-demo-data", "checked", None, utcnow(), "Data Engineer"),
            )
            for item in self.items:
                tx.execute(
                    "INSERT OR IGNORE INTO price_catalog(id, code, name, unit, category, base_price, synonyms, tags, "
                    "qty_rule, rooms, hist_min, hist_avg, hist_max, region_coeffs, source_id, valid_from, valid_to, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (item.id, item.code, item.name, item.unit, item.category, str(item.base_price),
                     dumps(list(item.synonyms)), dumps(list(item.tags)), dumps(item.qty_rule), dumps(list(item.rooms)),
                     str(item.hist_min), str(item.hist_avg), str(item.hist_max), dumps(item.region_coeffs),
                     item.source_id or None, item.valid_from, None, item.updated_at),
                )
            golden = json.loads((DATA / "golden_set.json").read_text(encoding="utf-8"))
            for g in golden:
                tx.execute(
                    "INSERT OR IGNORE INTO golden_examples(id, query, probe, expected_params, expected_catalog_ids, category, added_at) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (g["id"], g["query"], g.get("probe", ""), dumps(g["expected_params"]),
                     dumps(g["expected_catalog_ids"]), g["category"], g["added_at"]),
                )
            version = f"kb-{self.hash}"
            tx.execute(
                "INSERT OR IGNORE INTO knowledge_base_versions(id, version, created_at, notes, catalog_hash, "
                "prompt_service_versions, model_version, status) VALUES (?,?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), version, utcnow(), "Исходное наполнение (синтетический демо-прайс)",
                 self.hash, dumps({k: "v1" for k in ("parser", "matching", "clarification", "validation_judge", "vision", "revision")}),
                 "rules-fallback-v1", "active"),
            )

    # -------------------------------------------------------------- helpers
    def get(self, catalog_id: str) -> CatalogItem | None:
        return self.by_id.get(catalog_id)

    def regional_price(self, item: CatalogItem, region: str) -> Decimal:
        coeff = _d(item.region_coeffs.get(region, item.region_coeffs.get("Регионы", "1.00"))) if item.region_coeffs else Decimal("1")
        return (item.base_price * coeff).quantize(Q, rounding=ROUND_HALF_UP)

    def quantity(self, item: CatalogItem, area: Decimal) -> Decimal:
        """Детерминированное правило количества (никакого LLM!)."""
        rule = item.qty_rule or {"basis": "area", "factor": 1.0}
        basis, factor = rule.get("basis", "area"), _d(rule.get("factor", 1))
        a = max(_d(area), Decimal("1"))
        if basis == "area":
            raw = a
        elif basis == "wall_area":          # стены: 4 × √S × высота 2.7 м (аппроксимация периметра)
            raw = Decimal("4") * a.sqrt() * Decimal("2.7")
        elif basis == "ceiling":
            raw = a
        elif basis == "perimeter":
            raw = Decimal("4") * a.sqrt()
        elif basis == "lights":
            raw = a / Decimal("6")
        elif basis == "points":
            raw = a / Decimal("2.5")
        elif basis == "debris":
            raw = a * Decimal("0.12")
        elif basis == "fixed":
            raw = Decimal("1")
        else:
            raw = a
        return (raw * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def typical(self, room_type: str) -> dict[str, Any]:
        return self.compositions.get(room_type, self.compositions["другое"])

    def coverage(self) -> dict[str, Any]:
        by_cat: dict[str, int] = {}
        for i in self.items:
            by_cat[i.category] = by_cat.get(i.category, 0) + 1
        missing_prices = [i.id for i in self.items if i.base_price <= 0]
        anomalies = [i.id for i in self.items if i.base_price > i.hist_max * Decimal("1.5") or i.base_price < i.hist_min / Decimal("1.5")]
        return {"items": len(self.items), "by_category": by_cat, "missing_prices": missing_prices,
                "price_anomalies": anomalies, "hash": self.hash}

    def freshness_check(self) -> dict[str, Any]:
        """Data Freshness Loop (еженедельно): возраст цен, покрытие, аномалии."""
        cov = self.coverage()
        stale = [i.id for i in self.items if i.updated_at and i.updated_at[:10] < "2026-07-01"]
        result = {"checked_items": cov["items"], "updated_items": 0, "anomalies": len(cov["price_anomalies"]) + len(stale),
                  "stale_ids": stale, "coverage": cov["by_category"], "missing_prices": cov["missing_prices"],
                  "run_at": utcnow(), "kb_version": f"kb-{self.hash}"}
        db.insert("data_freshness_log", {
            "id": str(uuid.uuid4()), "run_at": result["run_at"], "checked_items": result["checked_items"],
            "updated_items": result["updated_items"], "anomalies": result["anomalies"],
            "kb_version": result["kb_version"],
        })
        return result


catalog = Catalog() if (DATA / "price_catalog.json").exists() else None  # type: ignore[assignment]


def get_catalog() -> Catalog:
    global catalog
    if catalog is None:
        catalog = Catalog()
    return catalog

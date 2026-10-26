"""Unit: Validation Service (ТЗ 3.2.6) — аномалии, дубли, полнота, галлюцинации."""
from __future__ import annotations

from decimal import Decimal

from neuro_smetchik.calculation import compute_totals
from neuro_smetchik.catalog import get_catalog
from neuro_smetchik.models import Position
from neuro_smetchik.validation import validate


def make_positions(*specs):
    cat = get_catalog()
    out = []
    for i, (cid, price, qty, status) in enumerate(specs):
        item = cat.get(cid)
        out.append(Position(id=f"p{i}", catalog_id=cid, name=item.name, unit=item.unit,
                            quantity=Decimal(str(qty)), unit_price=Decimal(str(price)),
                            coefficients={"region": "1.00"}, vat_rate=Decimal("0.20"),
                            confidence=0.9, status=status, sort_order=i))
    return out


def test_duplicate_positions_flagged():
    positions = make_positions(("CAT-018", 720, 10, "auto_accepted"), ("CAT-018", 720, 5, "auto_accepted"))
    totals = compute_totals(positions)
    issues, _ = validate(positions, totals, {"room_type": "квартира"}, trace_id="t-val", use_llm_judge=False)
    assert any(i.code == "duplicate_position" for i in issues)


def test_price_anomaly_flagged():
    positions = make_positions(("CAT-018", 99999, 10, "auto_accepted"))
    totals = compute_totals(positions)
    issues, _ = validate(positions, totals, {"room_type": "квартира"}, trace_id="t-val", use_llm_judge=False)
    assert any(i.code == "price_anomaly" for i in issues)


def test_completeness_suggests_archive_patterns():
    positions = make_positions(("CAT-028", 1050, 10, "auto_accepted"))
    totals = compute_totals(positions)
    issues, suggestions = validate(positions, totals, {"room_type": "ванная"}, trace_id="t-val", use_llm_judge=False)
    assert any(i.code == "incomplete_scope" for i in issues)
    assert suggestions and all(get_catalog().get(s["catalog_id"]) for s in suggestions)


def test_hallucinated_catalog_reference_blocked():
    positions = make_positions(("CAT-018", 720, 10, "auto_accepted"))
    positions[0].catalog_id = "CAT-DOES-NOT-EXIST"
    totals = compute_totals(positions)
    issues, _ = validate(positions, totals, {"room_type": "квартира"}, trace_id="t-val", use_llm_judge=False)
    assert any(i.code == "hallucinated_catalog_ref" and i.level == "error" for i in issues)


def test_low_confidence_requires_human():
    positions = make_positions(("CAT-018", 720, 10, "escalated"))
    totals = compute_totals(positions)
    issues, _ = validate(positions, totals, {"room_type": "квартира"}, trace_id="t-val", use_llm_judge=False)
    assert any(i.code == "low_confidence" for i in issues)

"""Unit: Calculation Service (ТЗ 3.2.5, критерий приёмки №3)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from neuro_smetchik.calculation import (checksum, compute_position, compute_totals,
                                        effective_unit_price, money, recalculate,
                                        verify_independent)
from neuro_smetchik.models import Position


def pos(**kw) -> Position:
    data = dict(id="p1", catalog_id="CAT-018", name="Штукатурка", unit="м2",
                quantity=Decimal("12.5"), unit_price=Decimal("720.00"),
                coefficients={"region": "1.00"}, vat_rate=Decimal("0.20"))
    data.update(kw)
    return Position(**data)


def test_no_float_in_money_fields():
    p = compute_position(pos())
    assert isinstance(p.subtotal, Decimal) and isinstance(p.total, Decimal)
    assert p.subtotal == Decimal("9000.00")
    assert p.vat_amount == Decimal("1800.00")
    assert p.total == Decimal("10800.00")


def test_coefficients_applied_deterministically():
    assert effective_unit_price(Decimal("100"), {"region": "0.9", "complexity": "1.1"}) == Decimal("99.000")


def test_rounding_half_up():
    assert money(Decimal("10.005")) == Decimal("10.01")
    assert money(Decimal("10.004")) == Decimal("10.00")


def test_independent_verification_matches_main_path():
    positions = [pos(), pos(id="p2", quantity=Decimal("3.33"), unit_price=Decimal("1050.99"),
                            coefficients={"region": "0.93"})]
    totals = compute_totals(positions)
    assert totals.verification == "ok"
    assert verify_independent(positions, totals)
    assert totals.grand_total == (totals.subtotal + totals.overhead + totals.profit + totals.vat)


def test_tampering_detected_by_checksum_and_recalculation():
    positions = [pos()]
    totals = compute_totals(positions)
    assert totals.checksum == checksum(positions, totals)
    positions[0].total = Decimal("999999.00")
    assert checksum(positions, totals) != totals.checksum
    totals.grand_total = Decimal("1.00")
    assert not verify_independent(positions, totals)


def test_recalculate_is_idempotent():
    positions = [pos(), pos(id="p2", quantity=Decimal("1"), unit_price=Decimal("99.99"))]
    a = recalculate(positions)
    b = recalculate(positions)
    assert a.grand_total == b.grand_total and a.checksum == b.checksum


def test_negative_values_rejected():
    with pytest.raises(ValueError):
        compute_position(pos(quantity=Decimal("-1")))
    with pytest.raises(ValueError):
        compute_position(pos(unit_price=Decimal("-5")))

"""Calculation Service (ТЗ 3.2.5): ТОЛЬКО детерминированный код, Decimal, независимая верификация.

Запрещено: float для денег, LLM для расчётов, неявные округления.
Каждая сумма пересчитывается вторым, независимым методом (integer kopeks + Fraction).
"""
from __future__ import annotations

import hashlib
from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
from typing import Any

from .config import settings
from .models import EstimateTotals, Position

CENT = Decimal("0.01")
ZERO = Decimal("0")
ROUND = ROUND_HALF_UP


def D(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND)


def effective_unit_price(unit_price: Decimal, coefficients: dict[str, str]) -> Decimal:
    result = unit_price
    for value in coefficients.values():
        result *= D(value)
    return result


def compute_position(position: Position, *, vat_rate: Decimal | None = None) -> Position:
    """Расчёт строки: quantity × unit_price × Π(coefficients) + НДС."""
    rate = D(vat_rate if vat_rate is not None else settings.vat_rate)
    unit_price = D(position.unit_price)
    qty = D(position.quantity)
    if qty < 0 or unit_price < 0:
        raise ValueError("Отрицательные количество/цена запрещены")
    eff = effective_unit_price(unit_price, position.coefficients)
    subtotal = money(qty * eff)
    vat_amount = money(subtotal * rate)
    position.vat_rate = rate
    position.subtotal = subtotal
    position.vat_amount = vat_amount
    position.total = money(subtotal + vat_amount)
    return position


def compute_totals(positions: list[Position], *, vat_rate: Decimal | None = None,
                   overhead_rate: Decimal | None = None, profit_rate: Decimal | None = None) -> EstimateTotals:
    """Итоги по смете. Наценки считаются от суммы строк, НДС — от строк и наценок."""
    rate = D(vat_rate if vat_rate is not None else settings.vat_rate)
    oh = D(overhead_rate if overhead_rate is not None else settings.overhead)
    profit = D(profit_rate if profit_rate is not None else settings.profit)
    for p in positions:
        compute_position(p, vat_rate=rate)
    subtotal = money(sum((p.subtotal for p in positions), ZERO))
    overhead_amount = money(subtotal * oh)
    profit_amount = money((subtotal + overhead_amount) * profit)
    vat_sum = money(sum((p.vat_amount for p in positions), ZERO) + money((overhead_amount + profit_amount) * rate))
    grand_total = money(subtotal + overhead_amount + profit_amount + vat_sum)
    totals = EstimateTotals(subtotal=subtotal, overhead=overhead_amount, profit=profit_amount,
                            vat=vat_sum, grand_total=grand_total)
    totals.checksum = checksum(positions, totals)
    totals.verification = "ok" if verify_independent(
        positions, totals, vat_rate=rate, overhead_rate=oh, profit_rate=profit) else "mismatch"
    return totals


def checksum(positions: list[Position], totals: EstimateTotals) -> str:
    """Контрольная сумма версии: связывает позиции, каталог и деньги."""
    payload = "|".join(
        f"{p.id}:{p.catalog_id}:{p.quantity}:{p.unit_price}:{sorted(p.coefficients.items())}:{p.subtotal}:{p.total}"
        for p in sorted(positions, key=lambda x: x.id)
    ) + f"||{totals.grand_total}|{totals.vat}|{totals.subtotal}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _round_cents(frac: Fraction) -> int:
    """Половина копейки вверх, целочисленная арифметика (независимый путь)."""
    scaled = frac * 100
    return int(scaled + Fraction(1, 2)) if scaled >= 0 else -int(-scaled + Fraction(1, 2))


def verify_independent(positions: list[Position], totals: EstimateTotals,
                       *, vat_rate: Decimal | None = None,
                       overhead_rate: Decimal | None = None,
                       profit_rate: Decimal | None = None) -> bool:
    """Независимый пересчёт через Fraction + целые копейки, в другом порядке агрегации.

    Критерий приёмки №3: 100% совпадение с основным расчётом.
    """
    oh = D(overhead_rate if overhead_rate is not None else settings.overhead)
    profit = D(profit_rate if profit_rate is not None else settings.profit)
    sub_cents = 0
    vat_cents = 0
    for p in positions:
        qty = Fraction(D(p.quantity))
        price = Fraction(D(p.unit_price))
        for coeff in p.coefficients.values():
            price *= Fraction(D(coeff))
        line = _round_cents(qty * price)
        sub_cents += line
        vat_cents += _round_cents(Fraction(line, 100) * Fraction(D(p.vat_rate)))
    overhead_cents = _round_cents(Fraction(sub_cents, 100) * Fraction(oh))
    profit_cents = _round_cents(Fraction(sub_cents + overhead_cents, 100) * Fraction(profit))
    vat_cents += _round_cents(Fraction(overhead_cents + profit_cents, 100)
                              * Fraction(D(vat_rate if vat_rate is not None else settings.vat_rate)))
    total_cents = sub_cents + overhead_cents + profit_cents + vat_cents
    expected = _round_cents(Fraction(D(totals.grand_total)))
    return total_cents == expected


def recalculate(positions: list[Position], **kwargs: Any) -> EstimateTotals:
    """Единая точка пересчёта (используется и Revision Service)."""
    return compute_totals(positions, **kwargs)

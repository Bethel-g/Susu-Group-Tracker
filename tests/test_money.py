"""Money handling tests (FR-10, US-09)."""

from decimal import Decimal

import pytest

from susu_tracker.exceptions import InvalidAmountError
from susu_tracker.money import as_money, ensure_positive, format_money


def test_as_money_accepts_decimal_int_and_string():
    assert as_money(Decimal("50")) == Decimal("50.00")
    assert as_money(50) == Decimal("50.00")
    assert as_money("50") == Decimal("50.00")
    assert as_money("50.5") == Decimal("50.50")
    assert as_money("  50.25  ") == Decimal("50.25")


def test_as_money_keeps_trailing_zeros_to_two_places():
    assert str(as_money(Decimal("50.000"))) == "50.00"


@pytest.mark.parametrize("value", ["abc", "", "50.", ".5", "1,000", "NaN", None, [1]])
def test_as_money_rejects_invalid_values(value):
    with pytest.raises(InvalidAmountError):
        as_money(value)


def test_as_money_rejects_more_than_two_decimal_places():
    with pytest.raises(InvalidAmountError):
        as_money("50.123")
    with pytest.raises(InvalidAmountError):
        as_money(Decimal("0.001"))


def test_as_money_rejects_float_precision_loss():
    # 0.1 + 0.2 is not exactly 0.3 in binary floating point; the tiny extra
    # fraction is rejected instead of being silently rounded.
    with pytest.raises(InvalidAmountError):
        as_money(0.1 + 0.2)
    # A clean float is still accepted through its shortest representation.
    assert as_money(50.0) == Decimal("50.00")


def test_ensure_positive_rejects_zero_and_negative():
    with pytest.raises(InvalidAmountError):
        ensure_positive(Decimal("0.00"), "Weekly contribution")
    with pytest.raises(InvalidAmountError):
        ensure_positive(Decimal("-0.01"), "Contribution amount")
    assert ensure_positive(Decimal("0.01")) == Decimal("0.01")


def test_format_money_always_uses_two_decimal_places():
    assert format_money(Decimal("150")) == "GHS 150.00"
    assert format_money(Decimal("50")) == "GHS 50.00"
    assert format_money(Decimal("0.05")) == "GHS 0.05"
    assert format_money(Decimal("1500.5")) == "GHS 1,500.50"

"""Exact money handling for Susu Group Tracker.

Monetary values are always decimal.Decimal, never float, so arithmetic is
exact. Amounts are restricted to two decimal places (GHS pesewas) and are
displayed in the form "GHS 50.00".
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .exceptions import InvalidAmountError

CURRENCY = "GHS"
PLACE = Decimal("0.01")

# Optional sign, digits, optionally a fraction of one or two digits.
# Rejects "", "50.", ".5", "1,000", "50.123", "abc", "NaN".
_MONEY_PATTERN = re.compile(r"^[+-]?\d+(\.\d{1,2})?$")


def as_money(value: object) -> Decimal:
    """Coerce *value* to an exact two-decimal-place Decimal.

    Accepts Decimal, int, str, and float. Floats are converted through their
    shortest round-trip representation, so values that lost precision
    (e.g. 0.1 + 0.2) are rejected instead of silently rounded.
    """
    if isinstance(value, Decimal):
        text = str(value)
    elif isinstance(value, int):
        text = str(value)
    elif isinstance(value, float):
        text = repr(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise InvalidAmountError(f"{value!r} is not a valid money amount.")

    if not _MONEY_PATTERN.match(text):
        raise InvalidAmountError(
            f"'{text}' is not a valid money amount (use e.g. 50 or 50.25)."
        )

    try:
        amount = Decimal(text)
    except InvalidOperation as exc:  # defensive: pattern should prevent this
        raise InvalidAmountError(f"'{text}' is not a valid money amount.") from exc

    if not amount.is_finite():
        raise InvalidAmountError(f"'{text}' is not a valid money amount.")
    if amount % PLACE != 0:
        raise InvalidAmountError(f"'{text}' has more than two decimal places.")
    try:
        return amount.quantize(PLACE, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise InvalidAmountError(f"'{text}' is not a valid money amount.") from exc


def ensure_positive(amount: Decimal, label: str = "Amount") -> Decimal:
    """Return *amount* if it is greater than zero, otherwise raise."""
    if amount <= 0:
        raise InvalidAmountError(f"{label} must be greater than zero.")
    return amount


def format_money(amount: Decimal) -> str:
    """Render an amount as 'GHS 1,500.50' with exactly two decimals."""
    return f"{CURRENCY} {as_money(amount):,.2f}"

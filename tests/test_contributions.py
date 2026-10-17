"""Contribution tracking tests (FR-03, FR-04, US-03, US-04)."""

from decimal import Decimal

import pytest

from susu_tracker.exceptions import (
    InvalidAmountError,
    OverpaymentError,
    UnknownMemberError,
)
from susu_tracker.susu_service import SusuService


def test_partial_payment_reduces_the_outstanding_balance(three_members: SusuService):
    contribution = three_members.record_contribution("M1", "30.00")
    assert contribution.amount == Decimal("30.00")
    assert contribution.week_number == 1
    assert three_members.get_member_balance("M1", 1) == Decimal("20.00")

    three_members.record_contribution("M1", "20.00")
    assert three_members.get_member_balance("M1", 1) == Decimal("0.00")
    # Both payments are kept as separate records.
    assert len(three_members.get_group().contributions) == 2


def test_multiple_partial_payments_are_summed(three_members: SusuService):
    for amount in ("10.00", "15.00", "25.00"):
        three_members.record_contribution("M1", amount)
    assert three_members.get_member_paid("M1", 1) == Decimal("50.00")
    assert three_members.get_member_balance("M1", 1) == Decimal("0.00")


def test_unknown_member_is_rejected_without_changing_state(three_members: SusuService):
    with pytest.raises(UnknownMemberError):
        three_members.record_contribution("M9", "50.00")
    group = three_members.get_group()
    assert group.contributions == []
    assert three_members.get_member_balance("M1", 1) == Decimal("50.00")


def test_payment_above_the_outstanding_balance_is_rejected(three_members: SusuService):
    with pytest.raises(OverpaymentError):
        three_members.record_contribution("M1", "60.00")
    assert three_members.get_group().contributions == []
    assert three_members.get_member_balance("M1", 1) == Decimal("50.00")


def test_overpayment_after_full_payment_changes_nothing(three_members: SusuService):
    three_members.record_contribution("M1", "50.00")
    with pytest.raises(OverpaymentError):
        three_members.record_contribution("M1", "0.01")
    group = three_members.get_group()
    assert len(group.contributions) == 1
    assert three_members.get_member_balance("M1", 1) == Decimal("0.00")


@pytest.mark.parametrize("amount", ["0", "0.00", "-10", "-0.01", "abc", "10.123"])
def test_invalid_contribution_amounts_are_rejected(three_members: SusuService, amount):
    with pytest.raises(InvalidAmountError):
        three_members.record_contribution("M1", amount)
    assert three_members.get_group().contributions == []


def test_balance_is_never_negative(three_members: SusuService):
    three_members.record_contribution("M1", "50.00")
    balance = three_members.get_member_balance("M1", 1)
    assert balance == Decimal("0.00")
    assert balance >= 0


def test_unknown_member_balance_is_rejected(three_members: SusuService):
    with pytest.raises(UnknownMemberError):
        three_members.get_member_balance("M9", 1)


def test_multiple_partial_payments_are_kept_as_separate_records(three_members: SusuService):
    three_members.record_contribution("M1", "30.00")
    three_members.record_contribution("M1", "20.00")
    amounts = [c.amount for c in three_members.get_group().contributions]
    assert amounts == [Decimal("30.00"), Decimal("20.00")]


def test_week_status_lists_every_member(three_members: SusuService):
    three_members.record_contribution("M1", "50.00")
    three_members.record_contribution("M3", "30.00")

    status = three_members.get_week_status(1)
    assert [(b.name, b.paid, b.balance) for b in status] == [
        ("Ama", Decimal("50.00"), Decimal("0.00")),
        ("Kofi", Decimal("0.00"), Decimal("50.00")),
        ("Esi", Decimal("30.00"), Decimal("20.00")),
    ]


def test_paid_and_balance_default_to_the_current_week(three_members: SusuService):
    three_members.record_contribution("M1", "30.00")
    assert three_members.get_member_paid("M1") == Decimal("30.00")
    assert three_members.get_member_balance("M1") == Decimal("20.00")

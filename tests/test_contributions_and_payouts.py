"""Commit 3 acceptance tests: contributions and weekly payouts (US-06 to US-08).

One test per acceptance criterion, plus the worked example from the
specification (Ama, Kofi, and Esi on a GHS 50.00 group).  These drive the
public `SusuService` API; the finer-grained unit tests live in
`test_contributions.py`, `test_week_closure.py`, and `test_reports.py`.
"""

from decimal import Decimal

import pytest

from susu_tracker.exceptions import (
    IncompleteWeekError,
    InvalidAmountError,
    NoMembersError,
    OverpaymentError,
    UnknownMemberError,
)
from susu_tracker.susu_service import SusuService


# -- US-06: record full and partial contributions --------------------------


def test_full_payment_clears_the_balance(three_members: SusuService):
    three_members.record_contribution("M1", "50.00")
    assert three_members.get_member_paid("M1", 1) == Decimal("50.00")
    assert three_members.get_member_balance("M1", 1) == Decimal("0.00")


def test_multiple_partial_payments_are_summed(three_members: SusuService):
    three_members.record_contribution("M2", "30.00")
    three_members.record_contribution("M2", "20.00")
    assert three_members.get_member_paid("M2", 1) == Decimal("50.00")
    assert three_members.get_member_balance("M2", 1) == Decimal("0.00")


def test_outstanding_balance_follows_the_stated_formula(three_members: SusuService):
    three_members.record_contribution("M3", "30.00")
    group = three_members.get_group()
    paid = three_members.get_member_paid("M3", 1)
    balance = three_members.get_member_balance("M3", 1)
    assert balance == group.weekly_contribution - paid
    assert balance == Decimal("20.00")


def test_contributions_are_tracked_per_week(three_members: SusuService, pay_all):
    pay_all("50.00")
    three_members.close_week()
    assert three_members.get_member_paid("M1", 1) == Decimal("50.00")
    assert three_members.get_member_paid("M1", 2) == Decimal("0.00")


def test_unknown_member_contribution_changes_nothing(three_members: SusuService):
    with pytest.raises(UnknownMemberError):
        three_members.record_contribution("M9", "50.00")
    assert three_members.get_group().contributions == []


def test_overpayment_is_rejected_and_not_recorded(three_members: SusuService):
    with pytest.raises(OverpaymentError):
        three_members.record_contribution("M1", "50.01")
    assert three_members.get_group().contributions == []


@pytest.mark.parametrize("amount", ["0", "0.00", "-1", "abc"])
def test_invalid_amounts_are_rejected(three_members: SusuService, amount):
    with pytest.raises(InvalidAmountError):
        three_members.record_contribution("M1", amount)
    assert three_members.get_group().contributions == []


# -- US-07: close the week and pay the pot ---------------------------------


def test_close_reports_every_unpaid_member(three_members: SusuService):
    three_members.record_contribution("M1", "50.00")
    three_members.record_contribution("M2", "40.00")
    three_members.record_contribution("M3", "10.00")

    with pytest.raises(IncompleteWeekError) as error:
        three_members.close_week()

    assert {(b.member_id, b.balance) for b in error.value.outstanding} == {
        ("M2", Decimal("10.00")),
        ("M3", Decimal("40.00")),
    }


def test_failed_close_makes_no_payout_and_keeps_the_week(three_members: SusuService):
    three_members.record_contribution("M1", "50.00")

    with pytest.raises(IncompleteWeekError):
        three_members.close_week()

    group = three_members.get_group()
    assert group.payouts == []
    assert group.current_week == 1
    assert group.get_week(1).payout is None


def test_pot_is_weekly_contribution_times_member_count(three_members: SusuService, pay_all):
    pay_all("50.00")
    payout = three_members.close_week()
    assert payout.amount == three_members.get_group().weekly_contribution * 3
    assert payout.amount == Decimal("150.00")


def test_payouts_follow_joining_order(three_members: SusuService, pay_all):
    recipients = []
    for _ in three_members.get_group().members:
        pay_all("50.00")
        recipients.append(three_members.close_week().recipient_id)
    assert recipients == ["M1", "M2", "M3"]


def test_a_closed_week_is_not_paid_twice(three_members: SusuService, pay_all):
    pay_all("50.00")
    three_members.close_week()

    with pytest.raises(IncompleteWeekError):
        three_members.close_week()
    assert len(three_members.get_group().payouts) == 1


def test_close_without_members_is_rejected(group_50: SusuService):
    with pytest.raises(NoMembersError):
        group_50.close_week()
    assert group_50.get_group().payouts == []


# -- US-08: payment status and payout history ------------------------------


def test_report_shows_week_paid_and_owed_for_every_member(three_members: SusuService):
    three_members.record_contribution("M1", "50.00")
    three_members.record_contribution("M3", "30.00")

    report = three_members.get_report()
    assert report.current_week == 1
    paid = {balance.member_id: balance.paid for balance in report.members}
    owed = {balance.member_id: balance.balance for balance in report.members}
    assert paid == {"M1": Decimal("50.00"), "M2": Decimal("0.00"), "M3": Decimal("30.00")}
    assert owed == {"M1": Decimal("0.00"), "M2": Decimal("50.00"), "M3": Decimal("20.00")}


def test_report_payout_entry_has_week_recipient_and_amount(three_members: SusuService, pay_all):
    pay_all("50.00")
    three_members.close_week()

    payout = three_members.get_report().payout_history[0]
    assert (payout.week_number, payout.recipient_id, payout.amount) == (
        1,
        "M1",
        Decimal("150.00"),
    )


def test_report_omits_failed_closures(three_members: SusuService):
    three_members.record_contribution("M1", "50.00")
    with pytest.raises(IncompleteWeekError):
        three_members.close_week()

    assert three_members.get_report().payout_history == []


def test_report_is_read_only(three_members: SusuService):
    three_members.record_contribution("M1", "50.00")
    first = three_members.get_report()
    second = three_members.get_report()

    assert first == second
    assert len(three_members.get_group().contributions) == 1


# -- The worked example from the specification -----------------------------


def test_spec_example_contributions_then_closure(three_members: SusuService):
    # Ama pays 50, Kofi pays 30 + 20, Esi pays 30 -> Esi still owes 20.
    three_members.record_contribution("M1", "50.00")
    three_members.record_contribution("M2", "30.00")
    three_members.record_contribution("M2", "20.00")
    three_members.record_contribution("M3", "30.00")

    assert three_members.get_member_balance("M1") == Decimal("0.00")
    assert three_members.get_member_balance("M2") == Decimal("0.00")
    assert three_members.get_member_balance("M3") == Decimal("20.00")

    # The first close attempt fails and changes nothing.
    with pytest.raises(IncompleteWeekError) as error:
        three_members.close_week()
    assert [(b.member_id, b.balance) for b in error.value.outstanding] == [
        ("M3", Decimal("20.00"))
    ]
    assert three_members.get_group().current_week == 1
    assert three_members.get_group().payouts == []

    # Esi pays the rest, then the week closes and the pot goes to Ama.
    three_members.record_contribution("M3", "20.00")
    payout = three_members.close_week()

    group = three_members.get_group()
    assert payout.week_number == 1
    assert payout.amount == Decimal("150.00")
    assert payout.recipient_id == "M1"
    assert group.current_week == 2
    assert group.next_recipient.member_id == "M2"

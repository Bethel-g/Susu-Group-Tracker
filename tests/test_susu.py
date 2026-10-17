"""Commit 2 and Commit 4 acceptance tests for the Susu domain.

Covers US-01 to US-05 (group creation and member management) and US-09 to
US-11 (contributions, weekly closing, payout order, and reporting).  The tests
drive the domain model (`SusuGroup`) directly — one case per acceptance
criterion — so the rules can be checked without the CLI or the service layer.
"""

from decimal import Decimal

import pytest

from susu_tracker.exceptions import (
    DuplicateMemberError,
    IncompleteWeekError,
    InvalidAmountError,
    InvalidMemberError,
    MembershipFrozenError,
    OverpaymentError,
    UnknownMemberError,
)
from susu_tracker.models import SusuGroup


def create_group() -> SusuGroup:
    """A GHS 50.00 group with Ama, Kofi, and Esi, as used in the examples."""
    group = SusuGroup(Decimal("50.00"))
    for member_id, name in (("M001", "Ama"), ("M002", "Kofi"), ("M003", "Esi")):
        group.add_member(member_id, name)
    return group


# -- US-01: create a group ------------------------------------------------


def test_create_group_with_valid_contribution():
    group = SusuGroup(Decimal("50.00"))
    assert group.weekly_contribution == Decimal("50.00")
    assert group.current_week == 1
    assert group.members == []


def test_create_group_with_zero_contribution_is_rejected():
    with pytest.raises(InvalidAmountError):
        SusuGroup(Decimal("0.00"))


def test_create_group_with_negative_contribution_is_rejected():
    with pytest.raises(InvalidAmountError):
        SusuGroup(Decimal("-50.00"))


# -- US-02: add a member --------------------------------------------------


def test_add_valid_member():
    group = SusuGroup(Decimal("50.00"))
    member = group.add_member("M001", "Ama")
    assert member.member_id == "M001"
    assert member.name == "Ama"
    assert member.join_order == 1
    assert group.members == [member]


def test_reject_member_with_empty_id():
    group = SusuGroup(Decimal("50.00"))
    with pytest.raises(InvalidMemberError):
        group.add_member("   ", "Ama")
    assert group.members == []


def test_reject_member_with_empty_name():
    group = SusuGroup(Decimal("50.00"))
    with pytest.raises(InvalidMemberError):
        group.add_member("M001", "   ")
    assert group.members == []


def test_member_details_are_trimmed():
    group = SusuGroup(Decimal("50.00"))
    member = group.add_member("  M001  ", "  Ama  ")
    assert member.member_id == "M001"
    assert member.name == "Ama"


# -- US-03: prevent duplicate IDs -----------------------------------------


def test_reject_duplicate_member_id():
    group = SusuGroup(Decimal("50.00"))
    group.add_member("M001", "Ama")
    with pytest.raises(DuplicateMemberError):
        group.add_member("M001", "Kofi")
    assert len(group.members) == 1


def test_reject_member_id_differing_only_by_case():
    group = SusuGroup(Decimal("50.00"))
    group.add_member("M001", "Ama")
    with pytest.raises(DuplicateMemberError):
        group.add_member("m001", "Kofi")
    assert len(group.members) == 1


def test_members_may_share_a_name():
    group = SusuGroup(Decimal("50.00"))
    group.add_member("M001", "Ama")
    group.add_member("M002", "Ama")
    assert [member.member_id for member in group.list_members()] == ["M001", "M002"]
    assert [member.name for member in group.list_members()] == ["Ama", "Ama"]


# -- US-04: view members ---------------------------------------------------


def test_list_members_in_empty_group():
    group = SusuGroup(Decimal("50.00"))
    assert group.list_members() == []


def test_multiple_members_keep_joining_order():
    group = SusuGroup(Decimal("50.00"))
    group.add_member("M001", "Ama")
    group.add_member("M002", "Kofi")
    group.add_member("M003", "Esi")
    assert [member.join_order for member in group.list_members()] == [1, 2, 3]
    assert [member.member_id for member in group.list_members()] == ["M001", "M002", "M003"]


def test_listing_members_does_not_change_group_state():
    group = SusuGroup(Decimal("50.00"))
    group.add_member("M001", "Ama")
    group.list_members().clear()
    assert len(group.members) == 1


# -- US-05: enforce membership rules --------------------------------------


def test_membership_freezes_once_a_week_has_started():
    group = SusuGroup(Decimal("50.00"))
    group.add_member("M001", "Ama")
    group.record_contribution("M001", Decimal("10.00"))
    with pytest.raises(MembershipFrozenError):
        group.add_member("M002", "Kofi")
    assert len(group.members) == 1


def test_members_can_be_added_before_the_first_payment():
    group = SusuGroup(Decimal("50.00"))
    group.add_member("M001", "Ama")
    group.add_member("M002", "Kofi")
    assert len(group.members) == 2


# -- US-09: failed registrations leave the group unchanged ----------------


def test_failed_registrations_do_not_change_the_member_list_or_order():
    group = SusuGroup(Decimal("50.00"))
    group.add_member("M001", "Ama")

    with pytest.raises(DuplicateMemberError):
        group.add_member("m001", "Kofi")
    with pytest.raises(InvalidMemberError):
        group.add_member("M002", "   ")
    with pytest.raises(InvalidMemberError):
        group.add_member("   ", "Esi")

    assert [member.member_id for member in group.list_members()] == ["M001"]

    # The next valid member still joins at position 2.
    next_member = group.add_member("M002", "Kofi")
    assert next_member.join_order == 2
    assert [member.join_order for member in group.list_members()] == [1, 2]


# -- US-10: contributions and partial payments -----------------------------


def test_valid_contribution_is_recorded_for_a_registered_member():
    group = create_group()
    contribution = group.record_contribution("M001", Decimal("50.00"))
    assert contribution.amount == Decimal("50.00")
    assert contribution.week_number == 1
    assert group.get_member_paid("M001") == Decimal("50.00")


def test_partial_payment_leaves_the_expected_balance():
    group = create_group()
    group.record_contribution("M001", Decimal("30.00"))
    assert group.get_member_balance("M001") == Decimal("20.00")

    group.record_contribution("M001", Decimal("20.00"))
    assert group.get_member_balance("M001") == Decimal("0.00")


def test_multiple_partial_payments_accumulate():
    group = create_group()
    for amount in ("10.00", "15.00", "25.00"):
        group.record_contribution("M001", Decimal(amount))
    assert group.get_member_paid("M001") == Decimal("50.00")
    assert group.get_member_balance("M001") == Decimal("0.00")


def test_outstanding_balance_is_weekly_contribution_minus_paid():
    group = create_group()
    group.record_contribution("M002", Decimal("30.00"))
    assert group.get_member_balance("M002") == (
        group.weekly_contribution - group.get_member_paid("M002")
    )


@pytest.mark.parametrize("amount", ["0", "0.00", "-50", "-0.01"])
def test_zero_and_negative_payments_are_rejected(amount):
    group = create_group()
    with pytest.raises(InvalidAmountError):
        group.record_contribution("M001", Decimal(amount))
    assert group.get_member_paid("M001") == Decimal("0.00")
    assert group.get_member_balance("M001") == Decimal("50.00")


def test_payment_exceeding_the_outstanding_balance_is_rejected():
    group = create_group()
    with pytest.raises(OverpaymentError):
        group.record_contribution("M001", Decimal("60.00"))
    assert group.get_member_paid("M001") == Decimal("0.00")


def test_payment_for_unknown_member_is_rejected():
    group = create_group()
    with pytest.raises(UnknownMemberError):
        group.record_contribution("M999", Decimal("10.00"))
    assert group.contributions == []


def test_failed_payment_does_not_modify_the_recorded_balance():
    group = create_group()
    group.record_contribution("M001", Decimal("30.00"))

    with pytest.raises(OverpaymentError):
        group.record_contribution("M001", Decimal("30.00"))

    assert group.get_member_paid("M001") == Decimal("30.00")
    assert group.get_member_balance("M001") == Decimal("20.00")
    assert len(group.contributions) == 1


def test_money_stays_exact_decimal():
    # A float would give 16.670000000000002; Decimal gives exactly 16.67.
    group = create_group()
    group.record_contribution("M001", Decimal("33.33"))
    assert group.get_member_balance("M001") == Decimal("16.67")

    # A float would give 0.15000000000000002; Decimal gives exactly 0.15.
    small = SusuGroup(Decimal("0.05"))
    for member_id in ("M001", "M002", "M003"):
        small.add_member(member_id, "Member " + member_id)
    assert small.pot == Decimal("0.15")
    small.record_contribution("M001", Decimal("0.03"))
    assert small.get_member_balance("M001") == Decimal("0.02")


# -- US-11: weekly closing, payout order, and reports ----------------------


def test_week_cannot_close_while_a_member_owes_money():
    group = create_group()
    group.record_contribution("M001", Decimal("50.00"))
    group.record_contribution("M002", Decimal("50.00"))
    group.record_contribution("M003", Decimal("30.00"))

    with pytest.raises(IncompleteWeekError):
        group.close_week()

    # The failed attempt must not advance the week or create a payout.
    assert group.current_week == 1
    assert group.get_member_balance("M003") == Decimal("20.00")
    assert group.payouts == []


def test_successful_payout_pays_the_pot_to_the_first_member():
    group = create_group()
    for member_id in ("M001", "M002", "M003"):
        group.record_contribution(member_id, Decimal("50.00"))

    payout = group.close_week()

    # Pot = weekly contribution x member count.
    assert payout.amount == group.weekly_contribution * 3
    assert payout.amount == Decimal("150.00")
    assert payout.recipient_id == "M001"
    assert group.current_week == 2
    assert len(group.payouts) == 1


def test_second_payout_follows_joining_order():
    group = create_group()
    for _ in range(2):
        for member_id in ("M001", "M002", "M003"):
            group.record_contribution(member_id, Decimal("50.00"))
        group.close_week()

    assert [payout.recipient_id for payout in group.payouts] == ["M001", "M002"]
    assert group.current_week == 3
    assert group.next_recipient.member_id == "M003"


def test_payout_history_records_week_recipient_and_amount():
    group = create_group()
    for member_id in ("M001", "M002", "M003"):
        group.record_contribution(member_id, Decimal("50.00"))
    group.close_week()

    assert [(p.week_number, p.recipient_id, p.amount) for p in group.payouts] == [
        (1, "M001", Decimal("150.00"))
    ]


def test_report_shows_paid_and_outstanding_for_every_member():
    group = create_group()
    group.record_contribution("M001", Decimal("50.00"))
    group.record_contribution("M003", Decimal("30.00"))

    balances = group.week_balances(1)

    assert [(b.member_id, b.paid, b.balance) for b in balances] == [
        ("M001", Decimal("50.00"), Decimal("0.00")),
        ("M002", Decimal("0.00"), Decimal("50.00")),
        ("M003", Decimal("30.00"), Decimal("20.00")),
    ]

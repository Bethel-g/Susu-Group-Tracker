"""Weekly closure, payout rotation, and completion tests (FR-05..FR-09)."""

from decimal import Decimal

import pytest

from susu_tracker.exceptions import (
    IncompleteWeekError,
    MembershipFrozenError,
    NoMembersError,
    RotationCompleteError,
)
from susu_tracker.models import WeekStatus
from susu_tracker.susu_service import SusuService


def test_closure_is_rejected_when_members_owe_money(three_members: SusuService):
    three_members.record_contribution("M1", "50.00")
    three_members.record_contribution("M2", "50.00")
    three_members.record_contribution("M3", "30.00")

    with pytest.raises(IncompleteWeekError) as error:
        three_members.close_week()

    assert [(b.member_id, b.balance) for b in error.value.outstanding] == [
        ("M3", Decimal("20.00"))
    ]


def test_failed_closure_leaves_the_group_unchanged(three_members: SusuService):
    for member_id, amount in (("M1", "50.00"), ("M2", "50.00"), ("M3", "30.00")):
        three_members.record_contribution(member_id, amount)
    before = three_members.get_report()

    with pytest.raises(IncompleteWeekError):
        three_members.close_week()

    group = three_members.get_group()
    assert three_members.get_report() == before
    assert group.payouts == []
    assert group.current_week == 1
    assert group.next_recipient_index == 0
    assert group.get_week(1).status is WeekStatus.OPEN
    assert len(group.contributions) == 3


def test_week_cannot_be_closed_without_members(group_50: SusuService):
    with pytest.raises(NoMembersError):
        group_50.close_week()
    assert group_50.get_group().payouts == []


def test_successful_closure_pays_the_pot_to_the_first_member(three_members: SusuService, pay_all):
    pay_all("50.00")
    payout = three_members.close_week()

    group = three_members.get_group()
    assert payout.week_number == 1
    assert payout.recipient_id == "M1"
    assert payout.amount == Decimal("150.00")
    assert group.get_week(1).payout == payout


def test_successful_closure_advances_the_cycle(three_members: SusuService, pay_all):
    pay_all("50.00")
    three_members.close_week()

    group = three_members.get_group()
    assert group.current_week == 2
    assert group.next_recipient_index == 1
    assert group.next_recipient.name == "Kofi"
    assert group.is_complete is False
    # The new week starts with nobody having paid.
    assert all(balance.paid == Decimal("0.00") for balance in three_members.get_week_status(2))
    assert all(
        balance.balance == Decimal("50.00") for balance in three_members.get_week_status(2)
    )


def test_reopening_a_closed_week_is_rejected(three_members: SusuService, pay_all):
    pay_all("50.00")
    three_members.close_week()

    # The cycle has advanced, so an immediate second closure must fail instead
    # of paying the same week twice.
    with pytest.raises(IncompleteWeekError):
        three_members.close_week()
    assert len(three_members.get_group().payouts) == 1


def test_full_rotation_pays_every_member_in_registration_order(three_members: SusuService, pay_all):
    for _ in three_members.get_group().members:
        pay_all("50.00")
        three_members.close_week()

    group = three_members.get_group()
    assert [payout.recipient_id for payout in group.payouts] == ["M1", "M2", "M3"]
    assert [payout.amount for payout in group.payouts] == [Decimal("150.00")] * 3
    assert [payout.week_number for payout in group.payouts] == [1, 2, 3]


def test_rotation_is_marked_complete_after_the_last_payout(three_members: SusuService, pay_all):
    for _ in range(3):
        pay_all("50.00")
        three_members.close_week()

    group = three_members.get_group()
    assert group.is_complete is True
    assert group.rotation_status == "Complete"
    assert group.next_recipient is None


def test_completed_rotation_rejects_new_payouts(three_members: SusuService, pay_all):
    for _ in range(3):
        pay_all("50.00")
        three_members.close_week()

    with pytest.raises(RotationCompleteError):
        three_members.close_week()
    assert len(three_members.get_group().payouts) == 3


def test_completed_rotation_rejects_new_contributions(three_members: SusuService, pay_all):
    for _ in range(3):
        pay_all("50.00")
        three_members.close_week()

    with pytest.raises(RotationCompleteError):
        three_members.record_contribution("M1", "50.00")
    assert len(three_members.get_group().contributions) == 9


def test_single_member_group_completes_in_one_week(service: SusuService):
    service.create_group("50.00")
    service.add_member("M1", "Ama")
    service.record_contribution("M1", "50.00")

    payout = service.close_week()
    assert payout.amount == Decimal("50.00")
    assert payout.recipient_id == "M1"
    assert service.get_group().is_complete is True

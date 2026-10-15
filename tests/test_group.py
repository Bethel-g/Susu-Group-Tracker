"""Group setup and membership tests (FR-01, FR-02, US-01, US-02)."""

from decimal import Decimal

import pytest

from susu_tracker.exceptions import (
    DuplicateMemberError,
    GroupAlreadyExistsError,
    InvalidAmountError,
    InvalidMemberError,
    MembershipFrozenError,
)
from susu_tracker.money import format_money
from susu_tracker.susu_service import SusuService


def test_create_group_stores_weekly_contribution(service: SusuService):
    group = service.create_group("50.00")
    assert group.weekly_contribution == Decimal("50.00")
    assert group.currency == "GHS"
    assert group.current_week == 1
    assert group.is_complete is False
    assert group.members == []


@pytest.mark.parametrize("amount", ["0", "0.00", "-5", "-0.01"])
def test_create_group_rejects_non_positive_amounts(service: SusuService, amount):
    with pytest.raises(InvalidAmountError):
        service.create_group(amount)
    assert service.has_group() is False


@pytest.mark.parametrize("amount", ["abc", "", "50.123"])
def test_create_group_rejects_invalid_money_input(service: SusuService, amount):
    with pytest.raises(InvalidAmountError):
        service.create_group(amount)
    assert service.has_group() is False


def test_second_group_is_not_created_silently(group_50: SusuService):
    with pytest.raises(GroupAlreadyExistsError):
        group_50.create_group("60.00")
    assert group_50.get_group().weekly_contribution == Decimal("50.00")


def test_members_keep_registration_order(three_members: SusuService):
    group = three_members.get_group()
    assert [member.member_id for member in group.members] == ["M1", "M2", "M3"]
    assert [member.name for member in group.members] == ["Ama", "Kofi", "Esi"]
    assert [member.join_order for member in group.members] == [1, 2, 3]


def test_duplicate_member_id_is_rejected(group_50: SusuService):
    group_50.add_member("M1", "Ama")
    with pytest.raises(DuplicateMemberError):
        group_50.add_member("m1", "Kofi")
    assert len(group_50.get_group().members) == 1


def test_duplicate_member_name_is_rejected(group_50: SusuService):
    group_50.add_member("M1", "Ama")
    with pytest.raises(DuplicateMemberError):
        group_50.add_member("M2", "  ama ")
    assert len(group_50.get_group().members) == 1


@pytest.mark.parametrize("member_id,name", [("", "Ama"), ("   ", "Ama"), ("M1", ""), ("M1", "   ")])
def test_blank_member_details_are_rejected(group_50: SusuService, member_id, name):
    with pytest.raises(InvalidMemberError):
        group_50.add_member(member_id, name)
    assert group_50.get_group().members == []


def test_members_can_be_added_while_no_payments_exist(group_50: SusuService):
    group_50.add_member("M1", "Ama")
    group_50.add_member("M2", "Kofi")
    assert len(group_50.get_group().members) == 2


def test_membership_freezes_after_first_contribution(group_50: SusuService):
    group_50.add_member("M1", "Ama")
    group_50.record_contribution("M1", "10.00")
    with pytest.raises(MembershipFrozenError):
        group_50.add_member("M2", "Kofi")
    assert len(group_50.get_group().members) == 1


def test_group_header_values_are_formatted_with_two_decimals(service: SusuService):
    group = service.create_group("50")
    assert format_money(group.weekly_contribution) == "GHS 50.00"

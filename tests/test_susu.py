"""Commit 2 acceptance tests: group setup and member management (US-01 to US-05).

These tests drive the domain model (`SusuGroup`) directly, one case per row of
the Commit 2 test table, so the group and membership rules can be checked
without the CLI or the service layer.
"""

from decimal import Decimal

import pytest

from susu_tracker.exceptions import (
    DuplicateMemberError,
    InvalidAmountError,
    InvalidMemberError,
    MembershipFrozenError,
)
from susu_tracker.models import SusuGroup


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

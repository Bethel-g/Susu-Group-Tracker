"""Shared pytest fixtures for the Susu Group Tracker test suite."""

import pytest

from susu_tracker.susu_service import SusuService


@pytest.fixture
def service() -> SusuService:
    """A service with no group created yet."""
    return SusuService()


@pytest.fixture
def group_50(service: SusuService) -> SusuService:
    """A service whose group requires GHS 50.00 per member per week."""
    service.create_group("50.00")
    return service


@pytest.fixture
def three_members(group_50: SusuService) -> SusuService:
    """A GHS 50.00 group with Ama, Kofi, and Esi registered in that order."""
    for member_id, name in (("M1", "Ama"), ("M2", "Kofi"), ("M3", "Esi")):
        group_50.add_member(member_id, name)
    return group_50


@pytest.fixture
def pay_all(three_members: SusuService):
    """Return a helper that pays the current week for every member."""

    def _pay_all(amount: str = "50.00") -> None:
        group = three_members.get_group()
        for member in group.members:
            three_members.record_contribution(member.member_id, amount)

    return _pay_all

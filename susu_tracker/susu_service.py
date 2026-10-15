"""Application service coordinating group operations.

The CLI calls these methods; business rules are enforced by the domain model.
"""

from __future__ import annotations

from decimal import Decimal

from .exceptions import GroupAlreadyExistsError
from .models import Contribution, Member, MemberBalance, Payout, SusuGroup
from .repository import InMemoryRepository


class SusuService:
    """Coordinates group creation, membership, and (later) week operations."""

    def __init__(self, repository: InMemoryRepository | None = None) -> None:
        self.repository = repository if repository is not None else InMemoryRepository()

    # -- group lifecycle ----------------------------------------------

    def has_group(self) -> bool:
        return self.repository.has_group()

    def get_group(self) -> SusuGroup:
        return self.repository.get_group()

    def create_group(self, weekly_amount: Decimal | str | int) -> SusuGroup:
        if self.repository.has_group():
            raise GroupAlreadyExistsError(
                "A savings group already exists; it has not been changed."
            )
        group = SusuGroup(weekly_amount)
        self.repository.save_group(group)
        return group

    # -- membership ----------------------------------------------------

    def add_member(self, member_id: str, name: str) -> Member:
        return self.get_group().add_member(member_id, name)

    # -- contributions --------------------------------------------------

    def record_contribution(self, member_id: str, amount: Decimal | str | int) -> Contribution:
        return self.get_group().record_contribution(member_id, amount)

    def get_member_balance(self, member_id: str, week_number: int) -> Decimal:
        return self.get_group().outstanding_balance(member_id, week_number)

    def get_week_status(self, week_number: int) -> list[MemberBalance]:
        return self.get_group().week_balances(week_number)

    # -- week closure -----------------------------------------------------

    def close_week(self) -> Payout:
        return self.get_group().close_week()

    def get_payout_history(self) -> list[Payout]:
        return list(self.get_group().payouts)

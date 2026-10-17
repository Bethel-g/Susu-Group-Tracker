"""Application service coordinating group operations.

The CLI calls these methods; business rules are enforced by the domain model.
"""

from __future__ import annotations

from decimal import Decimal

from .exceptions import GroupAlreadyExistsError
from .models import Contribution, GroupReport, Member, MemberBalance, Payout, SusuGroup
from .repository import InMemoryRepository


class SusuService:
    """Coordinates group creation, membership, contributions, and week closure."""

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

    def get_member_paid(self, member_id: str, week_number: int | None = None) -> Decimal:
        """Total paid by a member for one week (defaults to the current week)."""
        return self.get_group().get_member_paid(member_id, week_number)

    def get_member_balance(self, member_id: str, week_number: int | None = None) -> Decimal:
        """Outstanding balance for a member (defaults to the current week)."""
        return self.get_group().get_member_balance(member_id, week_number)

    def get_week_status(self, week_number: int) -> list[MemberBalance]:
        return self.get_group().week_balances(week_number)

    # -- week closure -----------------------------------------------------

    def close_week(self) -> Payout:
        return self.get_group().close_week()

    def get_payout_history(self) -> list[Payout]:
        return list(self.get_group().payouts)

    # -- reporting ---------------------------------------------------------

    def get_report(self) -> GroupReport:
        group = self.get_group()
        recipient = group.next_recipient
        return GroupReport(
            weekly_contribution=group.weekly_contribution,
            currency=group.currency,
            current_week=group.current_week,
            current_week_status=group.get_week(group.current_week).status,
            rotation_status=group.rotation_status,
            is_complete=group.is_complete,
            pot=group.pot,
            next_recipient_name=recipient.name if recipient else None,
            members=group.week_balances(group.current_week),
            payout_history=list(group.payouts),
        )

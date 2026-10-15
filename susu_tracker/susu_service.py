"""Application service coordinating group operations.

The CLI calls these methods; business rules are enforced by the domain model.
"""

from __future__ import annotations

from decimal import Decimal

from .exceptions import GroupAlreadyExistsError
from .models import Member, SusuGroup
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

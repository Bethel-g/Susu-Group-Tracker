"""Domain model for Susu Group Tracker.

All financial and membership rules live in this module so they can be tested
without the command-line interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .exceptions import (
    DuplicateMemberError,
    InvalidMemberError,
    MembershipFrozenError,
    UnknownMemberError,
)
from .money import as_money, ensure_positive


@dataclass(frozen=True)
class Member:
    """A registered group member, identified by a unique ID and name."""

    member_id: str
    name: str
    join_order: int


class SusuGroup:
    """A rotating savings group ("susu") with a fixed weekly contribution."""

    def __init__(self, weekly_contribution: Decimal | str | int) -> None:
        self.weekly_contribution: Decimal = ensure_positive(
            as_money(weekly_contribution), "Weekly contribution"
        )
        self.currency = "GHS"
        self.members: list[Member] = []
        self.current_week: int = 1
        self.next_recipient_index: int = 0
        self.is_complete: bool = False

    # -- membership ---------------------------------------------------

    @property
    def membership_frozen(self) -> bool:
        """Members may not be added once any contribution is recorded."""
        return False  # overridden once contribution tracking exists

    @staticmethod
    def _key(text: object) -> str:
        """Normalise an identifier: trimmed and case-insensitive."""
        return str(text).strip().casefold()

    def get_member(self, member_id: str) -> Member:
        key = self._key(member_id)
        for member in self.members:
            if self._key(member.member_id) == key:
                return member
        raise UnknownMemberError(f"No member with ID '{str(member_id).strip()}' is registered.")

    def add_member(self, member_id: str, name: str) -> Member:
        if self.membership_frozen:
            raise MembershipFrozenError(
                "Membership is frozen because contributions have already been recorded."
            )
        member_id_text = "" if member_id is None else str(member_id).strip()
        name_text = "" if name is None else str(name).strip()
        if not member_id_text or not name_text:
            raise InvalidMemberError("Both a member ID and a name are required.")

        id_key = self._key(member_id_text)
        name_key = self._key(name_text)
        for existing in self.members:
            if self._key(existing.member_id) == id_key:
                raise DuplicateMemberError(f"Member ID '{member_id_text}' is already registered.")
            if self._key(existing.name) == name_key:
                raise DuplicateMemberError(f"Member name '{name_text}' is already registered.")

        member = Member(
            member_id=member_id_text,
            name=name_text,
            join_order=len(self.members) + 1,
        )
        self.members.append(member)
        return member

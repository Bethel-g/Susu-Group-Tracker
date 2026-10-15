"""Domain model for Susu Group Tracker.

All financial and membership rules live in this module so they can be tested
without the command-line interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .exceptions import (
    DuplicateMemberError,
    IncompleteWeekError,
    InvalidMemberError,
    MembershipFrozenError,
    NoMembersError,
    OverpaymentError,
    RotationCompleteError,
    UnknownMemberError,
    UnknownWeekError,
    WeekClosedError,
)
from .money import as_money, ensure_positive, format_money

ZERO = Decimal("0.00")


class WeekStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass(frozen=True)
class Member:
    """A registered group member, identified by a unique ID and name."""

    member_id: str
    name: str
    join_order: int


@dataclass(frozen=True)
class Contribution:
    """One payment made by a member toward one week.

    Partial payments are stored as separate records rather than overwriting
    the previous amount, which keeps the payment history transparent.
    """

    member_id: str
    week_number: int
    amount: Decimal


@dataclass(frozen=True)
class Payout:
    """The whole weekly pot paid to one member."""

    week_number: int
    recipient_id: str
    amount: Decimal


@dataclass
class Week:
    """A saving week, open for contributions until it is closed.

    A closed week always has a payout attached.
    """

    number: int
    status: WeekStatus = WeekStatus.OPEN
    payout: Payout | None = None


@dataclass(frozen=True)
class MemberBalance:
    """How much one member has paid and still owes for a week."""

    member_id: str
    name: str
    paid: Decimal
    balance: Decimal


@dataclass(frozen=True)
class GroupReport:
    """A snapshot of the group's financial state for display."""

    weekly_contribution: Decimal
    currency: str
    current_week: int
    current_week_status: WeekStatus
    rotation_status: str
    is_complete: bool
    pot: Decimal
    next_recipient_name: str | None
    members: list[MemberBalance]
    payout_history: list[Payout]


class SusuGroup:
    """A rotating savings group ("susu") with a fixed weekly contribution."""

    def __init__(self, weekly_contribution: Decimal | str | int) -> None:
        self.weekly_contribution: Decimal = ensure_positive(
            as_money(weekly_contribution), "Weekly contribution"
        )
        self.currency = "GHS"
        self.members: list[Member] = []
        self.contributions: list[Contribution] = []
        self.payouts: list[Payout] = []
        self.weeks: dict[int, Week] = {1: Week(1)}
        self.current_week: int = 1
        self.next_recipient_index: int = 0
        self.is_complete: bool = False

    # -- membership ---------------------------------------------------

    @property
    def membership_frozen(self) -> bool:
        """Members may not be added once any contribution is recorded."""
        return bool(self.contributions)

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

    # -- weeks ---------------------------------------------------------

    def get_week(self, week_number: int) -> Week:
        try:
            return self.weeks[week_number]
        except KeyError:
            raise UnknownWeekError(f"Week {week_number} does not exist.") from None

    # -- contributions --------------------------------------------------

    def paid_amount(self, member_id: str, week_number: int) -> Decimal:
        """Total already paid by one member for one week."""
        self.get_week(week_number)
        member = self.get_member(member_id)
        total = ZERO
        for contribution in self.contributions:
            if (
                contribution.member_id == member.member_id
                and contribution.week_number == week_number
            ):
                total += contribution.amount
        return total

    def outstanding_balance(self, member_id: str, week_number: int) -> Decimal:
        """What the member still owes for the week; never negative."""
        balance = self.weekly_contribution - self.paid_amount(member_id, week_number)
        return balance if balance > 0 else ZERO

    def week_balances(self, week_number: int) -> list[MemberBalance]:
        """Payment status of every member for one week."""
        self.get_week(week_number)
        paid_by_member: dict[str, Decimal] = {}
        for contribution in self.contributions:
            if contribution.week_number == week_number:
                paid_by_member[contribution.member_id] = (
                    paid_by_member.get(contribution.member_id, ZERO) + contribution.amount
                )

        balances = []
        for member in self.members:
            paid = paid_by_member.get(member.member_id, ZERO)
            owed = self.weekly_contribution - paid
            balances.append(
                MemberBalance(
                    member_id=member.member_id,
                    name=member.name,
                    paid=paid,
                    balance=owed if owed > 0 else ZERO,
                )
            )
        return balances

    def record_contribution(self, member_id: str, amount: Decimal | str | int) -> Contribution:
        """Record a full or partial payment against the current open week."""
        if self.is_complete:
            raise RotationCompleteError(
                "The rotation is complete, so no more contributions can be recorded."
            )
        week = self.get_week(self.current_week)
        if week.status is not WeekStatus.OPEN:  # defensive: current week is always open here
            raise WeekClosedError(f"Week {week.number} is already closed.")

        money = ensure_positive(as_money(amount), "Contribution amount")
        member = self.get_member(member_id)
        balance = self.outstanding_balance(member.member_id, week.number)
        if money > balance:
            raise OverpaymentError(
                f"Cannot record {format_money(money)}: only {format_money(balance)} "
                f"remains due for {member.name} in week {week.number}."
            )

        contribution = Contribution(
            member_id=member.member_id,
            week_number=week.number,
            amount=money,
        )
        self.contributions.append(contribution)
        return contribution

    # -- closure and payouts --------------------------------------------

    @property
    def pot(self) -> Decimal:
        """The weekly pot: weekly contribution times the number of members."""
        return self.weekly_contribution * len(self.members)

    @property
    def next_recipient(self) -> Member | None:
        """The member who will be paid when the current week closes."""
        if self.is_complete or not self.members:
            return None
        return self.members[self.next_recipient_index]

    @property
    def rotation_status(self) -> str:
        return "Complete" if self.is_complete else "Active"

    def close_week(self) -> Payout:
        """Validate the current week and pay the pot to the next recipient.

        Validation happens before any state changes, so a rejected closure
        leaves the group exactly as it was.
        """
        # Phase 1: validate. Nothing is mutated before every check passes.
        if self.is_complete:
            raise RotationCompleteError(
                "The rotation is already complete; no further payouts can be made."
            )
        if not self.members:
            raise NoMembersError(
                "Cannot close a week before any members are registered."
            )
        week = self.get_week(self.current_week)
        if week.status is not WeekStatus.OPEN:  # defensive: current week is always open here
            raise WeekClosedError(f"Week {week.number} is already closed.")

        outstanding = [
            balance for balance in self.week_balances(week.number) if balance.balance > 0
        ]
        if outstanding:
            raise IncompleteWeekError(
                f"Week {week.number} cannot be closed because members still owe money.",
                outstanding,
            )

        # Phase 2: apply. Every check passed, so this block always completes.
        recipient = self.members[self.next_recipient_index]
        payout = Payout(
            week_number=week.number,
            recipient_id=recipient.member_id,
            amount=self.pot,
        )
        week.status = WeekStatus.CLOSED
        week.payout = payout
        self.payouts.append(payout)

        if len(self.payouts) >= len(self.members):
            # Every member has received exactly one payout.
            self.is_complete = True
        else:
            self.next_recipient_index += 1
            self.current_week += 1
            self.weeks[self.current_week] = Week(self.current_week)

        return payout

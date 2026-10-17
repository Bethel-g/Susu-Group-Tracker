"""Expected business-rule errors raised by the Susu domain and services.

Every error the application handles on purpose derives from SusuError, so the
CLI can catch one type and still distinguish individual failures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids an import cycle
    from .models import MemberBalance


class SusuError(Exception):
    """Base class for all expected business-rule violations."""


class InvalidAmountError(SusuError):
    """A monetary value is missing, malformed, non-positive, or too precise."""


class InvalidMemberError(SusuError):
    """A member ID or member name is empty."""


class DuplicateMemberError(SusuError):
    """A member with the same ID is already registered."""


class MembershipFrozenError(SusuError):
    """Members cannot be added once the first contribution is recorded."""


class UnknownMemberError(SusuError):
    """No registered member matches the given ID."""


class UnknownWeekError(SusuError):
    """The requested week number does not exist in this group."""


class OverpaymentError(SusuError):
    """A contribution would push the member's total above the weekly amount."""


class NoGroupError(SusuError):
    """An operation was requested before a group was created."""


class GroupAlreadyExistsError(SusuError):
    """A second group would silently overwrite the existing one."""


class NoMembersError(SusuError):
    """A week was closed before any member registered."""


class WeekClosedError(SusuError):
    """The current week is already closed and cannot be mutated."""


class RotationCompleteError(SusuError):
    """Every member has received a payout; the rotation cannot continue."""


class IncompleteWeekError(SusuError):
    """Closure was attempted while members still owe money.

    Carries the outstanding balances so the caller can report exactly who
    still owes what.
    """

    def __init__(self, message: str, outstanding: list[MemberBalance] | None = None) -> None:
        super().__init__(message)
        self.outstanding: list[MemberBalance] = list(outstanding or [])

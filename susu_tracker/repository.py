"""In-memory storage for the active group.

Data lives only for the lifetime of one program run; see NOTES.md.
"""

from __future__ import annotations

from .exceptions import NoGroupError
from .models import SusuGroup


class InMemoryRepository:
    """Holds at most one SusuGroup while the application runs."""

    def __init__(self) -> None:
        self._group: SusuGroup | None = None

    def has_group(self) -> bool:
        return self._group is not None

    def save_group(self, group: SusuGroup) -> None:
        self._group = group

    def get_group(self) -> SusuGroup:
        if self._group is None:
            raise NoGroupError("No savings group has been created yet.")
        return self._group

    def clear(self) -> None:
        self._group = None

"""Restriction model for Digital IDs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from digital_id.domain.errors import InvalidRestrictionError


@dataclass(frozen=True)
class Restriction:
    """Represents a restriction with an optional validity period."""

    name: str
    start: date | None = None
    end: date | None = None

    def is_active_on(self, when: date) -> bool:
        if self.start and when < self.start:
            return False
        if self.end and when > self.end:
            return False
        return True

    def validate(self) -> None:
        if not self.name.strip():
            raise InvalidRestrictionError("Restriction name cannot be empty.")
        if self.start and self.end and self.end < self.start:
            raise InvalidRestrictionError("Restriction end date must be after start date.")

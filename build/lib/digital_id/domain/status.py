"""Status model and allowed transitions for Digital IDs."""

from __future__ import annotations

from enum import Enum

from digital_id.domain.errors import InvalidStatusTransition


class Status(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"

    def can_transition_to(self, next_status: "Status") -> bool:
        if self is Status.REVOKED:
            return False
        if self is Status.ACTIVE:
            return next_status in {Status.SUSPENDED, Status.REVOKED, Status.ACTIVE}
        if self is Status.SUSPENDED:
            return next_status in {Status.ACTIVE, Status.REVOKED, Status.SUSPENDED}
        return False

    def ensure_transition(self, next_status: "Status") -> None:
        if not self.can_transition_to(next_status):
            raise InvalidStatusTransition(f"Cannot transition from {self.value} to {next_status.value}.")

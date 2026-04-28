"""Digital ID aggregate root."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from digital_id.domain.errors import ImmutableAttributeError
from digital_id.domain.history import StatusHistoryEntry
from digital_id.domain.restrictions import Restriction
from digital_id.domain.status import Status


@dataclass(frozen=True)
class IdentityAttributes:
    digital_id: str
    national_id: str
    date_of_birth: str


@dataclass
class MutableAttributes:
    name: str
    address: str
    email: str
    phone: str


@dataclass
class DigitalId:
    identity: IdentityAttributes
    mutable: MutableAttributes
    status: Status = Status.ACTIVE
    restrictions: list[Restriction] = field(default_factory=list)
    status_history: list[StatusHistoryEntry] = field(default_factory=list)

    def update_mutable(self, updates: MutableAttributes) -> None:
        self.mutable = updates

    def update_immutable(self, identity: IdentityAttributes) -> None:
        if identity != self.identity:
            raise ImmutableAttributeError("Immutable identity attributes cannot be changed.")

    def add_restriction(self, restriction: Restriction) -> None:
        restriction.validate()
        self.restrictions.append(restriction)

    def replace_restrictions(self, restrictions: Iterable[Restriction]) -> None:
        validated = []
        for restriction in restrictions:
            restriction.validate()
            validated.append(restriction)
        self.restrictions = validated

    def change_status(self, next_status: Status, reason: str) -> None:
        self.status.ensure_transition(next_status)
        entry = StatusHistoryEntry(
            from_status=self.status,
            to_status=next_status,
            changed_at=datetime.utcnow(),
            reason=reason,
        )
        self.status = next_status
        self.status_history.append(entry)

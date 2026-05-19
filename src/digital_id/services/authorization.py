"""Authorization rules for actors performing operations on Digital IDs."""

from __future__ import annotations

from enum import StrEnum

from digital_id.domain.status import Status


class AuthorizationError(Exception):
    pass


class Role(StrEnum):
    CENTRAL = "central_authority"
    LOCAL = "local_authority"
    AUDITOR = "auditor"


class AuthorizationService:
    """Simple role-based rules for status transitions.

    - `CENTRAL` may perform any transition.
    - Other roles may only verify and cannot change status.
    """

    def can_change_status(self, role: Role, current: Status, target: Status) -> bool:
        if role is Role.CENTRAL:
            return True
        return False

    def ensure_can_change(self, role: Role, current: Status, target: Status) -> None:
        if not self.can_change_status(role, current, target):
            raise AuthorizationError(
                f"Role {role.value} cannot change {current.value} -> {target.value}"
            )

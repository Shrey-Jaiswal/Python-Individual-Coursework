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
    TAX_AUTHORITY = "tax_authority"
    DRIVING_LICENCE_AUTHORITY = "driving_licence_authority"
    BANK_EMPLOYER = "bank_employer"


class VerificationType(StrEnum):
    TAX = "tax"
    DRIVING_LICENCE = "driving_licence"
    LOCAL_AUTHORITY = "local_authority"
    BANK_EMPLOYER = "bank_employer"


class AuthorizationService:
    """Simple role-based rules for status transitions.

    - `CENTRAL` may perform any transition.
    - Other roles may only verify and cannot change status.
    """

    def can_change_status(self, role: Role, current: Status, target: Status) -> bool:
        if role is Role.CENTRAL:
            return True
        return False

    def can_verify(self, role: Role, verification: VerificationType) -> bool:
        allowed = {
            VerificationType.TAX: {Role.TAX_AUTHORITY},
            VerificationType.DRIVING_LICENCE: {Role.DRIVING_LICENCE_AUTHORITY},
            VerificationType.LOCAL_AUTHORITY: {Role.LOCAL},
            VerificationType.BANK_EMPLOYER: {Role.BANK_EMPLOYER},
        }
        return role in allowed.get(verification, set())

    def ensure_can_change(self, role: Role, current: Status, target: Status) -> None:
        if not self.can_change_status(role, current, target):
            raise AuthorizationError(
                f"Role {role.value} cannot change {current.value} -> {target.value}"
            )

    def ensure_can_verify(self, role: Role, verification: VerificationType) -> None:
        if not self.can_verify(role, verification):
            raise AuthorizationError(
                f"Role {role.value} cannot verify {verification.value} requests"
            )

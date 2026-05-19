"""Verification strategies for different authorities."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from digital_id.domain import DigitalId, Restriction, Status
from digital_id.services.audit_log import AuditLog, build_audit_entry
from digital_id.services.authorization import (
    AuthorizationService,
    Role,
    VerificationType,
)


@dataclass(frozen=True)
class VerificationResult:
    eligible: bool
    reason: str


class VerificationService:
    """Applies organisation-specific verification rules."""

    def __init__(
        self,
        auth_service: AuthorizationService | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self._auth = auth_service or AuthorizationService()
        self._audit_log = audit_log

    def verify_tax(
        self,
        identity: DigitalId,
        period_start: date,
        period_end: date,
        role: Role,
        as_of: date | None = None,
    ) -> VerificationResult:
        self._auth.ensure_can_verify(role, VerificationType.TAX)
        if period_end < period_start:
            return VerificationResult(False, "reporting period end must be after start")
        if as_of is None:
            as_of = date.today()
        if period_end > as_of:
            return VerificationResult(False, "reporting period has not ended")
        if identity.status is not Status.ACTIVE:
            result = VerificationResult(False, "identity is not active")
        else:
            result = VerificationResult(True, "tax verification passed")
        self._record("verify_tax", identity.identity.digital_id, result.eligible, role)
        return result

    def verify_driving_licence(
        self,
        identity: DigitalId,
        role: Role,
        as_of: date | None = None,
        restriction_keywords: Iterable[str] | None = None,
    ) -> VerificationResult:
        self._auth.ensure_can_verify(role, VerificationType.DRIVING_LICENCE)
        if as_of is None:
            as_of = date.today()
        if identity.status is not Status.ACTIVE:
            result = VerificationResult(False, "identity is not active")
            self._record("verify_driving", identity.identity.digital_id, result.eligible, role)
            return result

        active = self._active_restrictions(identity.restrictions, as_of)
        filtered = self._filter_restrictions(active, restriction_keywords)
        if filtered:
            result = VerificationResult(False, "active restrictions present")
        else:
            result = VerificationResult(True, "driving licence verification passed")
        self._record("verify_driving", identity.identity.digital_id, result.eligible, role)
        return result

    def verify_local_authority(
        self,
        identity: DigitalId,
        role: Role,
        required_locality: str | None = None,
    ) -> VerificationResult:
        self._auth.ensure_can_verify(role, VerificationType.LOCAL_AUTHORITY)
        if identity.status is not Status.ACTIVE:
            result = VerificationResult(False, "identity is not active")
            self._record("verify_local", identity.identity.digital_id, result.eligible, role)
            return result
        address = identity.mutable.address.strip()
        if not address:
            result = VerificationResult(False, "address is required")
            self._record("verify_local", identity.identity.digital_id, result.eligible, role)
            return result
        if required_locality and required_locality.lower() not in address.lower():
            result = VerificationResult(False, "address does not match locality")
        else:
            result = VerificationResult(True, "local authority verification passed")
        self._record("verify_local", identity.identity.digital_id, result.eligible, role)
        return result

    def verify_bank_employer(self, identity: DigitalId, role: Role) -> VerificationResult:
        self._auth.ensure_can_verify(role, VerificationType.BANK_EMPLOYER)
        if identity.status is Status.ACTIVE:
            result = VerificationResult(True, "identity is active")
        else:
            result = VerificationResult(False, "identity is not active")
        self._record("verify_bank", identity.identity.digital_id, result.eligible, role)
        return result

    def _active_restrictions(
        self,
        restrictions: Iterable[Restriction],
        as_of: date,
    ) -> list[Restriction]:
        return [
            restriction for restriction in restrictions if restriction.is_active_on(as_of)
        ]

    def _filter_restrictions(
        self,
        restrictions: Iterable[Restriction],
        keywords: Iterable[str] | None,
    ) -> list[Restriction]:
        if keywords is None:
            return list(restrictions)
        lowered = [keyword.lower() for keyword in keywords]
        return [
            restriction
            for restriction in restrictions
            if any(keyword in restriction.name.lower() for keyword in lowered)
        ]

    def _record(self, action: str, target_id: str, eligible: bool, actor: Role) -> None:
        if self._audit_log is None:
            return
        self._audit_log.record(
            build_audit_entry(
                action=action,
                actor=actor.value,
                target_id=target_id,
                details={"eligible": str(eligible).lower()},
            )
        )

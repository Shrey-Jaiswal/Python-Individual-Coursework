"""Verification strategies for different authorities."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date

from digital_id.domain import DigitalId, Restriction, Status
from digital_id.persistence.errors import NotFoundError
from digital_id.persistence.repository import DigitalIdRepository
from digital_id.services.audit_log import AuditLog, build_audit_entry
from digital_id.services.authorization import (
    AuthorizationError,
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
        repository: DigitalIdRepository,
        auth_service: AuthorizationService | None = None,
        audit_log: AuditLog | None = None,
        today_provider: Callable[[], date] | None = None,
    ) -> None:
        self._repository = repository
        self._auth = auth_service or AuthorizationService()
        self._audit_log = audit_log
        self._today = today_provider or date.today

    def verify_tax(
        self,
        digital_id: str,
        period_start: date,
        period_end: date,
        role: Role,
        as_of: date | None = None,
    ) -> VerificationResult:
        self._ensure_can_verify(role, VerificationType.TAX, "verify_tax", digital_id)
        if period_end < period_start:
            return self._record_result(
                "verify_tax",
                digital_id,
                False,
                role,
                "reporting period end must be after start",
                "denied",
            )
        if as_of is None:
            as_of = self._today()
        if period_end > as_of:
            return self._record_result(
                "verify_tax",
                digital_id,
                False,
                role,
                "reporting period has not ended",
                "denied",
            )
        identity = self._find_identity("verify_tax", digital_id, role)
        if identity is None:
            return VerificationResult(False, "identity not found")
        if identity.status is not Status.ACTIVE:
            return self._record_result(
                "verify_tax",
                digital_id,
                False,
                role,
                "identity is not active",
                "failed",
            )
        elif self._was_suspended_during(identity, period_start, period_end):
            return self._record_result(
                "verify_tax",
                digital_id,
                False,
                role,
                "identity was suspended during reporting period",
                "failed",
            )
        return self._record_result(
            "verify_tax",
            digital_id,
            True,
            role,
            "tax verification passed",
            "passed",
        )

    def verify_driving_licence(
        self,
        digital_id: str,
        role: Role,
        as_of: date | None = None,
        restriction_keywords: Iterable[str] | None = None,
    ) -> VerificationResult:
        self._ensure_can_verify(
            role,
            VerificationType.DRIVING_LICENCE,
            "verify_driving",
            digital_id,
        )
        if as_of is None:
            as_of = self._today()
        identity = self._find_identity("verify_driving", digital_id, role)
        if identity is None:
            return VerificationResult(False, "identity not found")
        if identity.status is not Status.ACTIVE:
            return self._record_result(
                "verify_driving",
                digital_id,
                False,
                role,
                "identity is not active",
                "failed",
            )

        active = self._active_restrictions(identity.restrictions, as_of)
        filtered = self._filter_restrictions(active, restriction_keywords)
        if filtered:
            return self._record_result(
                "verify_driving",
                digital_id,
                False,
                role,
                "active restrictions present",
                "failed",
            )
        return self._record_result(
            "verify_driving",
            digital_id,
            True,
            role,
            "driving licence verification passed",
            "passed",
        )

    def verify_local_authority(
        self,
        digital_id: str,
        role: Role,
        required_locality: str | None = None,
    ) -> VerificationResult:
        self._ensure_can_verify(
            role,
            VerificationType.LOCAL_AUTHORITY,
            "verify_local",
            digital_id,
        )
        identity = self._find_identity("verify_local", digital_id, role)
        if identity is None:
            return VerificationResult(False, "identity not found")
        if identity.status is not Status.ACTIVE:
            return self._record_result(
                "verify_local",
                digital_id,
                False,
                role,
                "identity is not active",
                "failed",
            )
        address = identity.mutable.address.strip()
        if not address:
            return self._record_result(
                "verify_local",
                digital_id,
                False,
                role,
                "address is required",
                "failed",
            )
        if required_locality and required_locality.lower() not in address.lower():
            return self._record_result(
                "verify_local",
                digital_id,
                False,
                role,
                "address does not match locality",
                "failed",
            )
        return self._record_result(
            "verify_local",
            digital_id,
            True,
            role,
            "local authority verification passed",
            "passed",
        )

    def verify_bank_employer(self, digital_id: str, role: Role) -> VerificationResult:
        self._ensure_can_verify(role, VerificationType.BANK_EMPLOYER, "verify_bank", digital_id)
        identity = self._find_identity("verify_bank", digital_id, role)
        if identity is None:
            return VerificationResult(False, "identity not found")
        if identity.status is Status.ACTIVE:
            return self._record_result(
                "verify_bank",
                digital_id,
                True,
                role,
                "identity is active",
                "passed",
            )
        return self._record_result(
            "verify_bank",
            digital_id,
            False,
            role,
            "identity is not active",
            "failed",
        )

    def _active_restrictions(
        self,
        restrictions: Iterable[Restriction],
        as_of: date,
    ) -> list[Restriction]:
        return [restriction for restriction in restrictions if restriction.is_active_on(as_of)]

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

    def _was_suspended_during(
        self,
        identity: DigitalId,
        period_start: date,
        period_end: date,
    ) -> bool:
        entries = sorted(identity.status_history, key=lambda entry: entry.changed_at)
        suspended_start: date | None = None

        for entry in entries:
            if entry.to_status is Status.SUSPENDED:
                suspended_start = entry.changed_at.date()
            if entry.from_status is Status.SUSPENDED:
                start_date = suspended_start or period_start
                end_date = entry.changed_at.date()
                if self._overlaps_period(start_date, end_date, period_start, period_end):
                    return True
                suspended_start = None

        if suspended_start is not None:
            if self._overlaps_period(suspended_start, period_end, period_start, period_end):
                return True

        return False

    def _overlaps_period(
        self,
        start: date,
        end: date,
        period_start: date,
        period_end: date,
    ) -> bool:
        return start <= period_end and end >= period_start

    def _ensure_can_verify(
        self,
        role: Role,
        verification: VerificationType,
        action: str,
        target_id: str,
    ) -> None:
        try:
            self._auth.ensure_can_verify(role, verification)
        except AuthorizationError as exc:
            self._record_denied(action, target_id, role, str(exc))
            raise

    def _find_identity(self, action: str, digital_id: str, role: Role) -> DigitalId | None:
        try:
            return self._repository.get_by_id(digital_id)
        except NotFoundError:
            self._record_denied(action, digital_id, role, "identity not found")
            return None

    def _record_result(
        self,
        action: str,
        target_id: str,
        eligible: bool,
        actor: Role,
        reason: str,
        outcome: str,
    ) -> VerificationResult:
        self._record(action, target_id, eligible, actor, reason, outcome)
        return VerificationResult(eligible, reason)

    def _record(
        self,
        action: str,
        target_id: str,
        eligible: bool,
        actor: Role,
        reason: str,
        outcome: str,
    ) -> None:
        if self._audit_log is None:
            return
        self._audit_log.record(
            build_audit_entry(
                action=action,
                actor=actor.value,
                target_id=target_id,
                details={
                    "eligible": str(eligible).lower(),
                    "outcome": outcome,
                    "reason": reason,
                },
            )
        )

    def _record_denied(self, action: str, target_id: str, actor: Role, reason: str) -> None:
        self._record(action, target_id or "unknown", False, actor, reason, "denied")

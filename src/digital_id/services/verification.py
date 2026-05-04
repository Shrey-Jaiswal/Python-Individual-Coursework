"""Verification strategies for different authorities."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from digital_id.domain import DigitalId, Restriction, Status


@dataclass(frozen=True)
class VerificationResult:
    eligible: bool
    reason: str


class VerificationService:
    """Applies organisation-specific verification rules."""

    def verify_tax(
        self,
        identity: DigitalId,
        period_start: date,
        period_end: date,
        as_of: date | None = None,
    ) -> VerificationResult:
        if period_end < period_start:
            return VerificationResult(False, "reporting period end must be after start")
        if as_of is None:
            as_of = date.today()
        if period_end > as_of:
            return VerificationResult(False, "reporting period has not ended")
        if identity.status is not Status.ACTIVE:
            return VerificationResult(False, "identity is not active")
        return VerificationResult(True, "tax verification passed")

    def verify_driving_licence(
        self,
        identity: DigitalId,
        as_of: date | None = None,
        restriction_keywords: Iterable[str] | None = None,
    ) -> VerificationResult:
        if as_of is None:
            as_of = date.today()
        if identity.status is not Status.ACTIVE:
            return VerificationResult(False, "identity is not active")

        active = self._active_restrictions(identity.restrictions, as_of)
        filtered = self._filter_restrictions(active, restriction_keywords)
        if filtered:
            return VerificationResult(False, "active restrictions present")
        return VerificationResult(True, "driving licence verification passed")

    def verify_local_authority(
        self,
        identity: DigitalId,
        required_locality: str | None = None,
    ) -> VerificationResult:
        if identity.status is not Status.ACTIVE:
            return VerificationResult(False, "identity is not active")
        address = identity.mutable.address.strip()
        if not address:
            return VerificationResult(False, "address is required")
        if required_locality and required_locality.lower() not in address.lower():
            return VerificationResult(False, "address does not match locality")
        return VerificationResult(True, "local authority verification passed")

    def verify_bank_employer(self, identity: DigitalId) -> VerificationResult:
        if identity.status is Status.ACTIVE:
            return VerificationResult(True, "identity is active")
        return VerificationResult(False, "identity is not active")

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

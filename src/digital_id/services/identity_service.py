"""Identity management service for create, update, and status changes."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from digital_id.domain import (
    DigitalId,
    IdentityAttributes,
    InvalidRestrictionError,
    InvalidStatusTransition,
    MutableAttributes,
    Restriction,
    Status,
)
from digital_id.persistence.errors import DuplicateIdentityError, NotFoundError
from digital_id.persistence.repository import DigitalIdRepository
from digital_id.services.audit_log import AuditLog, build_audit_entry
from digital_id.services.authorization import AuthorizationError, AuthorizationService, Role
from digital_id.services.validation import ValidationError, ValidationService


class IdentityUpdateNotAllowedError(RuntimeError):
    pass


class IdentityService:
    """Application service for managing identities.

    Idempotency:
    - create_identity returns an existing identity when all fields match.
    - update_mutable returns the existing identity when updates are unchanged.
    """

    def __init__(
        self,
        repository: DigitalIdRepository,
        auth_service: AuthorizationService,
        validation_service: ValidationService,
        audit_log: AuditLog | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._auth = auth_service
        self._validator = validation_service
        self._audit_log = audit_log
        self._clock = clock or (lambda: datetime.now(UTC))

    def create_identity(
        self,
        identity: IdentityAttributes,
        mutable: MutableAttributes,
        role: Role,
    ) -> DigitalId:
        try:
            self._ensure_central(role)
            self._validator.validate_identity(identity)
            self._validator.validate_mutable(mutable)
        except (AuthorizationError, ValidationError) as exc:
            self._record_denied("identity_created", role, identity.digital_id, str(exc))
            raise

        existing = self._find_existing(identity)
        if existing is not None:
            if existing.identity == identity and existing.mutable == mutable:
                self._record(
                    action="identity_created",
                    actor=role.value,
                    target_id=identity.digital_id,
                    details={
                        "outcome": "no_op",
                        "reason": "matching identity already exists",
                    },
                )
                return existing
            self._record_denied(
                "identity_created",
                role,
                identity.digital_id,
                "identity already exists with different attributes",
            )
            raise DuplicateIdentityError("Identity already exists with different attributes.")

        digital_id = DigitalId(identity=identity, mutable=mutable)
        self._repository.add(digital_id)
        self._record(
            action="identity_created",
            actor=role.value,
            target_id=identity.digital_id,
            details={"national_id": identity.national_id, "outcome": "success"},
        )
        return digital_id

    def update_mutable(self, digital_id: str, updates: MutableAttributes, role: Role) -> DigitalId:
        try:
            self._ensure_central(role)
            identity = self._repository.get_by_id(digital_id)
        except (AuthorizationError, NotFoundError) as exc:
            self._record_denied("identity_updated", role, digital_id, str(exc))
            raise
        if identity.status is Status.REVOKED:
            self._record_denied(
                "identity_updated",
                role,
                digital_id,
                "cannot update a revoked identity",
            )
            raise IdentityUpdateNotAllowedError("Cannot update a revoked identity.")
        try:
            self._validator.validate_mutable(updates)
        except ValidationError as exc:
            self._record_denied("identity_updated", role, digital_id, str(exc))
            raise
        if updates == identity.mutable:
            self._record(
                action="identity_updated",
                actor=role.value,
                target_id=identity.identity.digital_id,
                details={"outcome": "no_op", "reason": "mutable attributes unchanged"},
            )
            return identity

        identity.update_mutable(updates)
        self._repository.update(identity)
        self._record(
            action="identity_updated",
            actor=role.value,
            target_id=identity.identity.digital_id,
            details={"address": updates.address, "email": updates.email, "outcome": "success"},
        )
        return identity

    def change_status(
        self,
        digital_id: str,
        next_status: Status,
        reason: str,
        role: Role,
    ) -> DigitalId:
        try:
            identity = self._repository.get_by_id(digital_id)
            self._auth.ensure_can_change(role, identity.status, next_status)
            changed = identity.change_status(next_status, reason, changed_at=self._clock())
        except (NotFoundError, AuthorizationError, InvalidStatusTransition) as exc:
            self._record_denied("status_changed", role, digital_id, str(exc))
            raise
        if not changed:
            self._record(
                action="status_changed",
                actor=role.value,
                target_id=identity.identity.digital_id,
                details={
                    "to": next_status.value,
                    "reason": reason,
                    "outcome": "no_op",
                },
            )
            return identity
        self._repository.update(identity)
        self._record(
            action="status_changed",
            actor=role.value,
            target_id=identity.identity.digital_id,
            details={"to": next_status.value, "reason": reason, "outcome": "success"},
        )
        return identity

    def add_restriction(
        self,
        digital_id: str,
        restriction: Restriction,
        role: Role,
    ) -> DigitalId:
        try:
            self._ensure_central(role)
            identity = self._repository.get_by_id(digital_id)
            self._ensure_not_revoked(identity, "restriction_added")
            self._validator.validate_restriction(restriction)
        except (
            AuthorizationError,
            NotFoundError,
            IdentityUpdateNotAllowedError,
            ValidationError,
        ) as exc:
            self._record_denied("restriction_added", role, digital_id, str(exc))
            raise

        identity.add_restriction(restriction)
        self._repository.update(identity)
        self._record(
            action="restriction_added",
            actor=role.value,
            target_id=identity.identity.digital_id,
            details={"restriction": restriction.name, "outcome": "success"},
        )
        return identity

    def replace_restrictions(
        self,
        digital_id: str,
        restrictions: Iterable[Restriction],
        role: Role,
    ) -> DigitalId:
        try:
            self._ensure_central(role)
            identity = self._repository.get_by_id(digital_id)
            self._ensure_not_revoked(identity, "restrictions_replaced")
            prepared = list(restrictions)
            for restriction in prepared:
                self._validator.validate_restriction(restriction)
        except (
            AuthorizationError,
            NotFoundError,
            IdentityUpdateNotAllowedError,
            ValidationError,
        ) as exc:
            self._record_denied("restrictions_replaced", role, digital_id, str(exc))
            raise

        try:
            identity.replace_restrictions(prepared)
        except InvalidRestrictionError as exc:
            self._record_denied("restrictions_replaced", role, digital_id, str(exc))
            raise ValidationError(str(exc)) from exc
        self._repository.update(identity)
        self._record(
            action="restrictions_replaced",
            actor=role.value,
            target_id=identity.identity.digital_id,
            details={"count": str(len(prepared)), "outcome": "success"},
        )
        return identity

    def _ensure_central(self, role: Role) -> None:
        if role is not Role.CENTRAL:
            raise AuthorizationError("Only central authority may perform this operation.")

    def _ensure_not_revoked(self, identity: DigitalId, action: str) -> None:
        if identity.status is Status.REVOKED:
            raise IdentityUpdateNotAllowedError(f"Cannot perform {action} on a revoked identity.")

    def _find_existing(self, identity: IdentityAttributes) -> DigitalId | None:
        try:
            return self._repository.get_by_id(identity.digital_id)
        except NotFoundError:
            pass
        try:
            return self._repository.get_by_national_id(identity.national_id)
        except NotFoundError:
            return None

    def _record(self, action: str, actor: str, target_id: str, details: dict[str, str]) -> None:
        if self._audit_log is None:
            return
        self._audit_log.record(
            build_audit_entry(
                action=action,
                actor=actor,
                target_id=target_id,
                details=details,
            )
        )

    def _record_denied(self, action: str, role: Role, target_id: str, reason: str) -> None:
        self._record(
            action=action,
            actor=role.value,
            target_id=target_id or "unknown",
            details={"outcome": "denied", "reason": reason},
        )

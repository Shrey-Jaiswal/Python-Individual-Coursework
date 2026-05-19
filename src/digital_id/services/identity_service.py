"""Identity management service for create, update, and status changes."""

from __future__ import annotations

from digital_id.domain import DigitalId, IdentityAttributes, MutableAttributes, Status
from digital_id.persistence.errors import DuplicateIdentityError, NotFoundError
from digital_id.persistence.repository import DigitalIdRepository
from digital_id.services.authorization import AuthorizationError, AuthorizationService, Role
from digital_id.services.validation import ValidationService


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
    ) -> None:
        self._repository = repository
        self._auth = auth_service
        self._validator = validation_service

    def create_identity(
        self,
        identity: IdentityAttributes,
        mutable: MutableAttributes,
        role: Role,
    ) -> DigitalId:
        self._ensure_central(role)
        self._validator.validate_identity(identity)

        existing = self._find_existing(identity)
        if existing is not None:
            if existing.identity == identity and existing.mutable == mutable:
                return existing
            raise DuplicateIdentityError("Identity already exists with different attributes.")

        digital_id = DigitalId(identity=identity, mutable=mutable)
        self._repository.add(digital_id)
        return digital_id

    def update_mutable(self, digital_id: str, updates: MutableAttributes, role: Role) -> DigitalId:
        self._ensure_central(role)
        identity = self._repository.get_by_id(digital_id)
        if identity.status is Status.REVOKED:
            raise IdentityUpdateNotAllowedError("Cannot update a revoked identity.")
        if updates == identity.mutable:
            return identity

        identity.update_mutable(updates)
        self._repository.update(identity)
        return identity

    def change_status(
        self,
        digital_id: str,
        next_status: Status,
        reason: str,
        role: Role,
    ) -> DigitalId:
        identity = self._repository.get_by_id(digital_id)
        self._auth.ensure_can_change(role, identity.status, next_status)
        identity.change_status(next_status, reason)
        self._repository.update(identity)
        return identity

    def _ensure_central(self, role: Role) -> None:
        if role is not Role.CENTRAL:
            raise AuthorizationError("Only central authority may perform this operation.")

    def _find_existing(self, identity: IdentityAttributes) -> DigitalId | None:
        try:
            return self._repository.get_by_id(identity.digital_id)
        except NotFoundError:
            pass
        try:
            return self._repository.get_by_national_id(identity.national_id)
        except NotFoundError:
            return None

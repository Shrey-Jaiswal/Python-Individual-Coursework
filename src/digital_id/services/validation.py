"""Validation utilities for Digital ID entities."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from digital_id.domain import (
    IdentityAttributes,
    InvalidRestrictionError,
    MutableAttributes,
    Restriction,
)


class ValidationError(Exception):
    pass


class ValidationService:
    """Basic validation checks used by higher-level services or CLI."""

    def __init__(self, today_provider: Callable[[], date] | None = None) -> None:
        self._today = today_provider or date.today

    def validate_identity(self, identity: IdentityAttributes) -> None:
        if not identity.digital_id.strip():
            raise ValidationError("digital_id must not be empty")
        if not identity.national_id.strip():
            raise ValidationError("national_id must not be empty")
        if not identity.date_of_birth.strip():
            raise ValidationError("date_of_birth must not be empty")
        try:
            date_of_birth = date.fromisoformat(identity.date_of_birth)
        except ValueError as exc:
            raise ValidationError("date_of_birth must be YYYY-MM-DD") from exc
        if date_of_birth > self._today():
            raise ValidationError("date_of_birth cannot be in the future")

    def validate_restriction(self, restriction: Restriction) -> None:
        try:
            restriction.validate()
        except InvalidRestrictionError as exc:
            raise ValidationError(str(exc)) from exc

    def validate_mutable(self, mutable: MutableAttributes) -> None:
        name = mutable.name.strip()
        if not name:
            raise ValidationError("name must not be empty")

        address = mutable.address.strip()
        if not address:
            raise ValidationError("address must not be empty")

        email = mutable.email.strip()
        if not email:
            raise ValidationError("email must not be empty")
        if "@" not in email or "." not in email:
            raise ValidationError("email must contain @ and .")

        phone = mutable.phone.strip()
        if not phone:
            raise ValidationError("phone must not be empty")
        normalized = phone[1:] if phone.startswith("+") else phone
        if not normalized.isdigit():
            raise ValidationError("phone must contain digits only")

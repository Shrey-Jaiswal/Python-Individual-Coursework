"""Validation utilities for Digital ID entities."""

from __future__ import annotations

from typing import Any

from digital_id.domain import IdentityAttributes, Restriction, InvalidRestrictionError


class ValidationError(Exception):
    pass


class ValidationService:
    """Basic validation checks used by higher-level services or CLI."""

    def validate_identity(self, identity: IdentityAttributes) -> None:
        if not identity.digital_id:
            raise ValidationError("digital_id must not be empty")
        if not identity.national_id:
            raise ValidationError("national_id must not be empty")
        # date_of_birth left as string for this coursework; ensure non-empty
        if not identity.date_of_birth:
            raise ValidationError("date_of_birth must not be empty")

    def validate_restriction(self, restriction: Restriction) -> None:
        try:
            restriction.validate()
        except InvalidRestrictionError as exc:
            raise ValidationError(str(exc)) from exc

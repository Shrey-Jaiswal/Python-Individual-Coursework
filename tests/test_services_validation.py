from datetime import date

import pytest

from digital_id.domain import IdentityAttributes, Restriction
from digital_id.services import ValidationError, ValidationService


def test_validate_identity_rejects_empty_fields() -> None:
    svc = ValidationService()
    bad = IdentityAttributes(digital_id="", national_id="", date_of_birth="")
    with pytest.raises(ValidationError):
        svc.validate_identity(bad)


def test_validate_restriction_uses_domain_validation() -> None:
    svc = ValidationService()
    r = Restriction(name="r", start=date(2026, 5, 2), end=date(2026, 5, 1))
    with pytest.raises(ValidationError):
        svc.validate_restriction(r)

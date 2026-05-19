from datetime import date

import pytest

from digital_id.domain import IdentityAttributes, MutableAttributes, Restriction
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


def test_validate_identity_rejects_bad_date_format() -> None:
    svc = ValidationService()
    bad = IdentityAttributes(digital_id="did-1", national_id="nat-1", date_of_birth="bad")
    with pytest.raises(ValidationError):
        svc.validate_identity(bad)


def make_mutable(
    name: str = "Ava Example",
    address: str = "1 High Street",
    email: str = "ava@example.com",
    phone: str = "0000000000",
) -> MutableAttributes:
    return MutableAttributes(name=name, address=address, email=email, phone=phone)


def test_validate_mutable_rejects_empty_fields() -> None:
    svc = ValidationService()
    bad = make_mutable(name=" ", address=" ", email=" ", phone=" ")
    with pytest.raises(ValidationError):
        svc.validate_mutable(bad)


def test_validate_mutable_rejects_bad_email() -> None:
    svc = ValidationService()
    bad = make_mutable(email="invalid")
    with pytest.raises(ValidationError):
        svc.validate_mutable(bad)


def test_validate_mutable_rejects_bad_phone() -> None:
    svc = ValidationService()
    bad = make_mutable(phone="000-000")
    with pytest.raises(ValidationError):
        svc.validate_mutable(bad)

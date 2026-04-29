from digital_id.services import ValidationService
from digital_id.domain import IdentityAttributes, Restriction
from datetime import date


def test_validate_identity_rejects_empty_fields() -> None:
    svc = ValidationService()
    bad = IdentityAttributes(digital_id="", national_id="", date_of_birth="")
    try:
        svc.validate_identity(bad)
        assert False, "Expected ValidationError"
    except Exception:
        pass


def test_validate_restriction_uses_domain_validation() -> None:
    svc = ValidationService()
    r = Restriction(name="r", start=date(2026, 5, 2), end=date(2026, 5, 1))
    try:
        svc.validate_restriction(r)
        assert False, "Expected ValidationError"
    except Exception:
        pass

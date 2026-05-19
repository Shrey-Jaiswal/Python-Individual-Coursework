from datetime import date

import pytest

from digital_id.domain import DigitalId, IdentityAttributes, MutableAttributes, Restriction, Status
from digital_id.services import AuthorizationError, Role, VerificationService


def make_identity(
    status: Status = Status.ACTIVE,
    address: str = "1 High Street, London",
    restrictions: list[Restriction] | None = None,
) -> DigitalId:
    identity = IdentityAttributes(
        digital_id="did-1",
        national_id="nat-1",
        date_of_birth="1990-01-01",
    )
    mutable = MutableAttributes(
        name="Ava Example",
        address=address,
        email="ava@example.com",
        phone="0000000000",
    )
    return DigitalId(
        identity=identity,
        mutable=mutable,
        status=status,
        restrictions=restrictions or [],
    )


def test_tax_verification_passes_for_active_completed_period() -> None:
    service = VerificationService()
    identity = make_identity()

    result = service.verify_tax(
        identity,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 4, 1),
    )

    assert result.eligible is True


def test_tax_verification_rejects_invalid_period() -> None:
    service = VerificationService()
    identity = make_identity()

    result = service.verify_tax(
        identity,
        period_start=date(2026, 4, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 5, 1),
    )

    assert result.eligible is False


def test_tax_verification_rejects_inactive_status() -> None:
    service = VerificationService()
    identity = make_identity(status=Status.SUSPENDED)

    result = service.verify_tax(
        identity,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 4, 1),
    )

    assert result.eligible is False


def test_tax_verification_rejects_unfinished_period() -> None:
    service = VerificationService()
    identity = make_identity()

    result = service.verify_tax(
        identity,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 6, 1),
    )

    assert result.eligible is False


def test_driving_verification_rejects_active_restriction() -> None:
    service = VerificationService()
    restriction = Restriction(name="driving_suspension", start=date(2026, 1, 1))
    identity = make_identity(restrictions=[restriction])

    result = service.verify_driving_licence(
        identity,
        role=Role.DRIVING_LICENCE_AUTHORITY,
        as_of=date(2026, 2, 1),
    )

    assert result.eligible is False


def test_driving_verification_allows_non_matching_restriction_keywords() -> None:
    service = VerificationService()
    restriction = Restriction(name="tax_hold", start=date(2026, 1, 1))
    identity = make_identity(restrictions=[restriction])

    result = service.verify_driving_licence(
        identity,
        role=Role.DRIVING_LICENCE_AUTHORITY,
        as_of=date(2026, 2, 1),
        restriction_keywords=["driving"],
    )

    assert result.eligible is True


def test_driving_verification_rejects_inactive_status() -> None:
    service = VerificationService()
    identity = make_identity(status=Status.SUSPENDED)

    result = service.verify_driving_licence(
        identity,
        role=Role.DRIVING_LICENCE_AUTHORITY,
        as_of=date(2026, 2, 1),
    )

    assert result.eligible is False


def test_driving_verification_passes_without_restrictions() -> None:
    service = VerificationService()
    identity = make_identity()

    result = service.verify_driving_licence(
        identity,
        role=Role.DRIVING_LICENCE_AUTHORITY,
        as_of=date(2026, 2, 1),
    )

    assert result.eligible is True


def test_local_authority_requires_matching_locality() -> None:
    service = VerificationService()
    identity = make_identity(address="10 Hill Road, Leeds")

    result = service.verify_local_authority(
        identity,
        role=Role.LOCAL,
        required_locality="London",
    )

    assert result.eligible is False


def test_local_authority_allows_matching_locality() -> None:
    service = VerificationService()
    identity = make_identity(address="10 Hill Road, London")

    result = service.verify_local_authority(
        identity,
        role=Role.LOCAL,
        required_locality="London",
    )

    assert result.eligible is True


def test_local_authority_rejects_missing_address() -> None:
    service = VerificationService()
    identity = make_identity(address=" ")

    result = service.verify_local_authority(identity, role=Role.LOCAL)

    assert result.eligible is False


def test_bank_employer_returns_validity_only() -> None:
    service = VerificationService()
    active = make_identity(status=Status.ACTIVE)
    suspended = make_identity(status=Status.SUSPENDED)

    assert service.verify_bank_employer(active, role=Role.BANK_EMPLOYER).eligible is True
    assert service.verify_bank_employer(suspended, role=Role.BANK_EMPLOYER).eligible is False


def test_verification_rejects_unauthorized_role() -> None:
    service = VerificationService()
    identity = make_identity()

    with pytest.raises(AuthorizationError):
        service.verify_tax(
            identity,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            role=Role.BANK_EMPLOYER,
            as_of=date(2026, 4, 1),
        )

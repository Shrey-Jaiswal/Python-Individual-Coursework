from datetime import date, datetime

import pytest

from digital_id.domain import (
    DigitalId,
    IdentityAttributes,
    MutableAttributes,
    Restriction,
    Status,
    StatusHistoryEntry,
)
from digital_id.persistence import InMemoryRepository
from digital_id.services import AuditLog, AuthorizationError, Role, VerificationService


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


def make_service(identity: DigitalId) -> tuple[VerificationService, str]:
    repo = InMemoryRepository()
    repo.add(identity)
    return VerificationService(repo), identity.identity.digital_id


def make_service_with_today(identity: DigitalId, today: date) -> tuple[VerificationService, str]:
    repo = InMemoryRepository()
    repo.add(identity)
    return VerificationService(repo, today_provider=lambda: today), identity.identity.digital_id


def test_tax_verification_passes_for_active_completed_period() -> None:
    service, digital_id = make_service(make_identity())

    result = service.verify_tax(
        digital_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 4, 1),
    )

    assert result.eligible is True


def test_tax_verification_uses_injected_today() -> None:
    service, digital_id = make_service_with_today(make_identity(), date(2026, 4, 1))

    result = service.verify_tax(
        digital_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
    )

    assert result.eligible is True


def test_tax_verification_rejects_invalid_period() -> None:
    service, digital_id = make_service(make_identity())

    result = service.verify_tax(
        digital_id,
        period_start=date(2026, 4, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 5, 1),
    )

    assert result.eligible is False


def test_tax_verification_rejects_inactive_status() -> None:
    service, digital_id = make_service(make_identity(status=Status.SUSPENDED))

    result = service.verify_tax(
        digital_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 4, 1),
    )

    assert result.eligible is False


def test_tax_verification_rejects_unfinished_period() -> None:
    service, digital_id = make_service(make_identity())

    result = service.verify_tax(
        digital_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 6, 1),
    )

    assert result.eligible is False


def test_tax_verification_rejects_suspension_in_period() -> None:
    identity = make_identity()
    identity.status_history = [
        StatusHistoryEntry(
            from_status=Status.ACTIVE,
            to_status=Status.SUSPENDED,
            changed_at=datetime(2026, 2, 1, 9, 0),
            reason="review",
        ),
        StatusHistoryEntry(
            from_status=Status.SUSPENDED,
            to_status=Status.ACTIVE,
            changed_at=datetime(2026, 2, 10, 9, 0),
            reason="cleared",
        ),
    ]
    service, digital_id = make_service(identity)

    result = service.verify_tax(
        digital_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 4, 1),
    )

    assert result.eligible is False


def test_tax_verification_allows_no_suspension_in_period() -> None:
    identity = make_identity()
    identity.status_history = [
        StatusHistoryEntry(
            from_status=Status.ACTIVE,
            to_status=Status.SUSPENDED,
            changed_at=datetime(2025, 12, 1, 9, 0),
            reason="review",
        ),
        StatusHistoryEntry(
            from_status=Status.SUSPENDED,
            to_status=Status.ACTIVE,
            changed_at=datetime(2025, 12, 5, 9, 0),
            reason="cleared",
        ),
    ]
    service, digital_id = make_service(identity)

    result = service.verify_tax(
        digital_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 4, 1),
    )

    assert result.eligible is True


def test_tax_verification_rejects_open_suspension_in_period() -> None:
    identity = make_identity()
    identity.status_history = [
        StatusHistoryEntry(
            from_status=Status.ACTIVE,
            to_status=Status.SUSPENDED,
            changed_at=datetime(2026, 2, 1, 9, 0),
            reason="review",
        )
    ]
    service, digital_id = make_service(identity)

    result = service.verify_tax(
        digital_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 4, 1),
    )

    assert result.eligible is False


def test_driving_verification_rejects_active_restriction() -> None:
    restriction = Restriction(name="driving_suspension", start=date(2026, 1, 1))
    service, digital_id = make_service(make_identity(restrictions=[restriction]))

    result = service.verify_driving_licence(
        digital_id,
        role=Role.DRIVING_LICENCE_AUTHORITY,
        as_of=date(2026, 2, 1),
    )

    assert result.eligible is False


def test_driving_verification_allows_non_matching_restriction_keywords() -> None:
    restriction = Restriction(name="tax_hold", start=date(2026, 1, 1))
    service, digital_id = make_service(make_identity(restrictions=[restriction]))

    result = service.verify_driving_licence(
        digital_id,
        role=Role.DRIVING_LICENCE_AUTHORITY,
        as_of=date(2026, 2, 1),
        restriction_keywords=["driving"],
    )

    assert result.eligible is True


def test_driving_verification_rejects_inactive_status() -> None:
    service, digital_id = make_service(make_identity(status=Status.SUSPENDED))

    result = service.verify_driving_licence(
        digital_id,
        role=Role.DRIVING_LICENCE_AUTHORITY,
        as_of=date(2026, 2, 1),
    )

    assert result.eligible is False


def test_driving_verification_passes_without_restrictions() -> None:
    service, digital_id = make_service(make_identity())

    result = service.verify_driving_licence(
        digital_id,
        role=Role.DRIVING_LICENCE_AUTHORITY,
        as_of=date(2026, 2, 1),
    )

    assert result.eligible is True


def test_driving_verification_uses_injected_today() -> None:
    restriction = Restriction(name="driving_suspension", start=date(2026, 2, 1))
    service, digital_id = make_service_with_today(
        make_identity(restrictions=[restriction]),
        date(2026, 1, 1),
    )

    result = service.verify_driving_licence(
        digital_id,
        role=Role.DRIVING_LICENCE_AUTHORITY,
    )

    assert result.eligible is True


def test_local_authority_requires_matching_locality() -> None:
    service, digital_id = make_service(make_identity(address="10 Hill Road, Leeds"))

    result = service.verify_local_authority(
        digital_id,
        role=Role.LOCAL,
        required_locality="London",
    )

    assert result.eligible is False


def test_local_authority_allows_matching_locality() -> None:
    service, digital_id = make_service(make_identity(address="10 Hill Road, London"))

    result = service.verify_local_authority(
        digital_id,
        role=Role.LOCAL,
        required_locality="London",
    )

    assert result.eligible is True


def test_local_authority_rejects_missing_address() -> None:
    service, digital_id = make_service(make_identity(address=" "))

    result = service.verify_local_authority(digital_id, role=Role.LOCAL)

    assert result.eligible is False


def test_bank_employer_returns_validity_only() -> None:
    service, active_id = make_service(make_identity(status=Status.ACTIVE))
    result = service.verify_bank_employer(active_id, role=Role.BANK_EMPLOYER)
    assert result.eligible is True

    service, suspended_id = make_service(make_identity(status=Status.SUSPENDED))
    result = service.verify_bank_employer(suspended_id, role=Role.BANK_EMPLOYER)
    assert result.eligible is False


def test_verification_rejects_unauthorized_role() -> None:
    service, digital_id = make_service(make_identity())

    with pytest.raises(AuthorizationError):
        service.verify_tax(
            digital_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            role=Role.BANK_EMPLOYER,
            as_of=date(2026, 4, 1),
        )


def test_missing_identity_paths_return_limited_failure() -> None:
    repo = InMemoryRepository()
    service = VerificationService(repo)

    assert (
        service.verify_tax(
            "missing",
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            role=Role.TAX_AUTHORITY,
            as_of=date(2026, 4, 1),
        ).reason
        == "identity not found"
    )
    assert (
        service.verify_driving_licence("missing", role=Role.DRIVING_LICENCE_AUTHORITY).reason
        == "identity not found"
    )
    assert (
        service.verify_local_authority("missing", role=Role.LOCAL).reason
        == "identity not found"
    )


def test_missing_identity_is_denied_and_audited() -> None:
    repo = InMemoryRepository()
    audit = AuditLog()
    service = VerificationService(repo, audit_log=audit)

    result = service.verify_bank_employer("missing-id", role=Role.BANK_EMPLOYER)

    assert result.eligible is False
    assert result.reason == "identity not found"
    [entry] = audit.list_all()
    assert entry.action == "verify_bank"
    assert entry.details["outcome"] == "denied"

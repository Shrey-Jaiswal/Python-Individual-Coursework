import pytest

from digital_id.domain import IdentityAttributes, InvalidStatusTransition, MutableAttributes, Status
from digital_id.persistence import DuplicateIdentityError, InMemoryRepository
from digital_id.services import (
    AuthorizationError,
    AuthorizationService,
    IdentityService,
    IdentityUpdateNotAllowedError,
    Role,
    ValidationError,
    ValidationService,
)


def make_identity(
    digital_id: str = "did-1",
    national_id: str = "nat-1",
    date_of_birth: str = "1990-01-01",
) -> IdentityAttributes:
    return IdentityAttributes(
        digital_id=digital_id,
        national_id=national_id,
        date_of_birth=date_of_birth,
    )


def make_mutable(
    name: str = "Ava Example",
    address: str = "1 High Street",
    email: str = "ava@example.com",
    phone: str = "0000000000",
) -> MutableAttributes:
    return MutableAttributes(name=name, address=address, email=email, phone=phone)


def make_service() -> IdentityService:
    repo = InMemoryRepository()
    auth = AuthorizationService()
    validator = ValidationService()
    return IdentityService(repo, auth, validator)


def test_create_identity_central_success() -> None:
    service = make_service()
    identity = make_identity()
    mutable = make_mutable()

    created = service.create_identity(identity, mutable, Role.CENTRAL)

    assert created.identity == identity
    assert created.mutable == mutable


def test_create_identity_rejects_non_central() -> None:
    service = make_service()
    with pytest.raises(AuthorizationError):
        service.create_identity(make_identity(), make_mutable(), Role.LOCAL)


def test_create_identity_is_idempotent_for_same_payload() -> None:
    service = make_service()
    identity = make_identity()
    mutable = make_mutable()

    first = service.create_identity(identity, mutable, Role.CENTRAL)
    second = service.create_identity(identity, mutable, Role.CENTRAL)

    assert first is second


def test_create_identity_conflict_on_different_payload() -> None:
    service = make_service()
    identity = make_identity()
    service.create_identity(identity, make_mutable(), Role.CENTRAL)

    with pytest.raises(DuplicateIdentityError):
        service.create_identity(identity, make_mutable(name="Other"), Role.CENTRAL)


def test_create_identity_rejects_bad_date() -> None:
    service = make_service()
    bad = make_identity(date_of_birth="bad-date")
    with pytest.raises(ValidationError):
        service.create_identity(bad, make_mutable(), Role.CENTRAL)


def test_create_identity_rejects_bad_mutable() -> None:
    service = make_service()
    identity = make_identity()
    bad_mutable = make_mutable(email="invalid")
    with pytest.raises(ValidationError):
        service.create_identity(identity, bad_mutable, Role.CENTRAL)


def test_update_mutable_idempotent() -> None:
    service = make_service()
    identity = make_identity()
    mutable = make_mutable()
    service.create_identity(identity, mutable, Role.CENTRAL)

    updated = service.update_mutable(identity.digital_id, mutable, Role.CENTRAL)

    assert updated.mutable == mutable


def test_update_mutable_rejects_revoked() -> None:
    service = make_service()
    identity = make_identity()
    service.create_identity(identity, make_mutable(), Role.CENTRAL)
    service.change_status(identity.digital_id, Status.REVOKED, "fraud", Role.CENTRAL)

    with pytest.raises(IdentityUpdateNotAllowedError):
        service.update_mutable(identity.digital_id, make_mutable(name="New"), Role.CENTRAL)


def test_update_mutable_rejects_invalid_fields() -> None:
    service = make_service()
    identity = make_identity()
    service.create_identity(identity, make_mutable(), Role.CENTRAL)

    with pytest.raises(ValidationError):
        service.update_mutable(identity.digital_id, make_mutable(phone="000-000"), Role.CENTRAL)


def test_change_status_rejects_invalid_transition() -> None:
    service = make_service()
    identity = make_identity()
    service.create_identity(identity, make_mutable(), Role.CENTRAL)
    service.change_status(identity.digital_id, Status.REVOKED, "fraud", Role.CENTRAL)

    with pytest.raises(InvalidStatusTransition):
        service.change_status(identity.digital_id, Status.ACTIVE, "appeal", Role.CENTRAL)


def test_change_status_respects_authorization() -> None:
    service = make_service()
    identity = make_identity()
    service.create_identity(identity, make_mutable(), Role.CENTRAL)

    with pytest.raises(AuthorizationError):
        service.change_status(identity.digital_id, Status.REVOKED, "fraud", Role.LOCAL)

from datetime import date

import pytest

from digital_id.domain import (
    DigitalId,
    IdentityAttributes,
    ImmutableAttributeError,
    InvalidRestrictionError,
    InvalidStatusTransition,
    MutableAttributes,
    Restriction,
    Status,
)


def make_identity() -> DigitalId:
    identity = IdentityAttributes(
        digital_id="did-123",
        national_id="nat-999",
        date_of_birth="1990-01-01",
    )
    mutable = MutableAttributes(
        name="Ava Example",
        address="1 High Street",
        email="ava@example.com",
        phone="0000000000",
    )
    return DigitalId(identity=identity, mutable=mutable)


def test_immutable_identity_cannot_change() -> None:
    digital_id = make_identity()
    other = IdentityAttributes(
        digital_id="did-999",
        national_id="nat-999",
        date_of_birth="1990-01-01",
    )
    with pytest.raises(ImmutableAttributeError):
        digital_id.update_immutable(other)


def test_status_transition_records_history() -> None:
    digital_id = make_identity()
    digital_id.change_status(Status.SUSPENDED, reason="manual review")

    assert digital_id.status is Status.SUSPENDED
    assert len(digital_id.status_history) == 1
    entry = digital_id.status_history[0]
    assert entry.from_status is Status.ACTIVE
    assert entry.to_status is Status.SUSPENDED
    assert entry.reason == "manual review"


def test_revoked_cannot_transition() -> None:
    digital_id = make_identity()
    digital_id.change_status(Status.REVOKED, reason="fraud")
    with pytest.raises(InvalidStatusTransition):
        digital_id.change_status(Status.ACTIVE, reason="appeal")


def test_restriction_validation_rejects_invalid_period() -> None:
    restriction = Restriction(
        name="driving_restriction",
        start=date(2026, 5, 1),
        end=date(2026, 4, 1),
    )
    with pytest.raises(InvalidRestrictionError):
        restriction.validate()


def test_restriction_is_active_on_bounds() -> None:
    restriction = Restriction(
        name="travel_hold",
        start=date(2026, 5, 1),
        end=date(2026, 5, 3),
    )

    assert restriction.is_active_on(date(2026, 5, 1)) is True
    assert restriction.is_active_on(date(2026, 5, 2)) is True
    assert restriction.is_active_on(date(2026, 5, 3)) is True
    assert restriction.is_active_on(date(2026, 4, 30)) is False
    assert restriction.is_active_on(date(2026, 5, 4)) is False


def test_restriction_validation_rejects_empty_name() -> None:
    restriction = Restriction(name=" ")

    with pytest.raises(InvalidRestrictionError):
        restriction.validate()

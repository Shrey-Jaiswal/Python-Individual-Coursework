import pytest

from digital_id.domain import Status
from digital_id.services import (
    AuthorizationError,
    AuthorizationService,
    Role,
    VerificationType,
)


def test_central_can_revoke() -> None:
    svc = AuthorizationService()
    assert svc.can_change_status(Role.CENTRAL, Status.ACTIVE, Status.REVOKED)


def test_local_cannot_change_status() -> None:
    svc = AuthorizationService()
    assert not svc.can_change_status(Role.LOCAL, Status.ACTIVE, Status.SUSPENDED)
    assert not svc.can_change_status(Role.LOCAL, Status.SUSPENDED, Status.ACTIVE)
    assert not svc.can_change_status(Role.LOCAL, Status.ACTIVE, Status.REVOKED)


def test_auditor_cannot_change_status() -> None:
    svc = AuthorizationService()
    with pytest.raises(AuthorizationError):
        svc.ensure_can_change(Role.AUDITOR, Status.ACTIVE, Status.SUSPENDED)


def test_local_cannot_change_status_via_ensure() -> None:
    svc = AuthorizationService()
    with pytest.raises(AuthorizationError):
        svc.ensure_can_change(Role.LOCAL, Status.ACTIVE, Status.SUSPENDED)


def test_verification_roles_are_scoped() -> None:
    svc = AuthorizationService()
    assert svc.can_verify(Role.TAX_AUTHORITY, VerificationType.TAX)
    assert svc.can_verify(Role.DRIVING_LICENCE_AUTHORITY, VerificationType.DRIVING_LICENCE)
    assert svc.can_verify(Role.LOCAL, VerificationType.LOCAL_AUTHORITY)
    assert svc.can_verify(Role.BANK_EMPLOYER, VerificationType.BANK_EMPLOYER)


def test_verification_rejects_wrong_role() -> None:
    svc = AuthorizationService()
    with pytest.raises(AuthorizationError):
        svc.ensure_can_verify(Role.BANK_EMPLOYER, VerificationType.TAX)

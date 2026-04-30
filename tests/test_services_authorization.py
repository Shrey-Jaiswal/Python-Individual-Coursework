import pytest

from digital_id.domain import Status
from digital_id.services import AuthorizationError, AuthorizationService, Role


def test_central_can_revoke() -> None:
    svc = AuthorizationService()
    assert svc.can_change_status(Role.CENTRAL, Status.ACTIVE, Status.REVOKED)


def test_local_cannot_revoke() -> None:
    svc = AuthorizationService()
    assert not svc.can_change_status(Role.LOCAL, Status.ACTIVE, Status.REVOKED)


def test_local_can_suspend_and_reactivate() -> None:
    svc = AuthorizationService()
    assert svc.can_change_status(Role.LOCAL, Status.ACTIVE, Status.SUSPENDED)
    assert svc.can_change_status(Role.LOCAL, Status.SUSPENDED, Status.ACTIVE)


def test_auditor_cannot_change_status() -> None:
    svc = AuthorizationService()
    with pytest.raises(AuthorizationError):
        svc.ensure_can_change(Role.AUDITOR, Status.ACTIVE, Status.SUSPENDED)


def test_local_cannot_revoke_via_ensure() -> None:
    svc = AuthorizationService()
    with pytest.raises(AuthorizationError):
        svc.ensure_can_change(Role.LOCAL, Status.ACTIVE, Status.REVOKED)

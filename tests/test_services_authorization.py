from digital_id.services import AuthorizationService, Role
from digital_id.domain import Status


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

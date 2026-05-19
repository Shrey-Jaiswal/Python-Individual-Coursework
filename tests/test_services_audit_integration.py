from digital_id.domain import IdentityAttributes, MutableAttributes, Status
from digital_id.persistence import InMemoryRepository
from digital_id.services import (
    AuditLog,
    AuthorizationService,
    IdentityService,
    Role,
    ValidationService,
    VerificationService,
)


def make_identity() -> IdentityAttributes:
    return IdentityAttributes(
        digital_id="did-1",
        national_id="nat-1",
        date_of_birth="1990-01-01",
    )


def make_mutable(address: str = "1 High Street") -> MutableAttributes:
    return MutableAttributes(
        name="Ava Example",
        address=address,
        email="ava@example.com",
        phone="0000000000",
    )


def test_identity_service_records_audit_entries() -> None:
    log = AuditLog()
    service = IdentityService(
        InMemoryRepository(),
        AuthorizationService(),
        ValidationService(),
        audit_log=log,
    )

    identity = make_identity()
    service.create_identity(identity, make_mutable(), Role.CENTRAL)
    service.update_mutable(identity.digital_id, make_mutable(address="2 High Street"), Role.CENTRAL)
    service.change_status(identity.digital_id, Status.SUSPENDED, "review", Role.CENTRAL)

    actions = [entry.action for entry in log.list_all()]
    assert actions == ["identity_created", "identity_updated", "status_changed"]


def test_verification_service_records_audit_entries() -> None:
    log = AuditLog()
    repo = InMemoryRepository()

    identity = make_identity()
    mutable = make_mutable()

    from digital_id.domain import DigitalId

    did = DigitalId(identity=identity, mutable=mutable)
    repo.add(did)
    verification = VerificationService(repo, audit_log=log)
    verification.verify_bank_employer(identity.digital_id, role=Role.BANK_EMPLOYER)

    entries = log.list_all()
    assert len(entries) == 1
    assert entries[0].action == "verify_bank"
    assert entries[0].actor == Role.BANK_EMPLOYER.value
    assert entries[0].details["outcome"] == "passed"

"""Scripted demo scenario for the Digital ID backend."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from digital_id.domain import IdentityAttributes, MutableAttributes, Restriction, Status
from digital_id.persistence import InMemoryRepository
from digital_id.persistence.errors import DuplicateIdentityError
from digital_id.services import (
    AuditLog,
    AuthorizationError,
    AuthorizationService,
    IdentityService,
    Role,
    ValidationService,
    VerificationService,
)


@dataclass
class DemoContext:
    repository: InMemoryRepository
    identity_service: IdentityService
    verification_service: VerificationService
    audit_log: AuditLog


def build_demo_context() -> DemoContext:
    repository = InMemoryRepository()
    audit_log = AuditLog()
    auth = AuthorizationService()
    validator = ValidationService()
    identity_service = IdentityService(repository, auth, validator, audit_log)
    verification_service = VerificationService(audit_log=audit_log)
    return DemoContext(
        repository=repository,
        identity_service=identity_service,
        verification_service=verification_service,
        audit_log=audit_log,
    )


def run_scripted_demo(
    context: DemoContext,
    audit_path: Path | None = None,
    output: Callable[[str], None] | None = None,
) -> list[str]:
    lines: list[str] = []

    def emit(message: str) -> None:
        lines.append(message)
        if output is not None:
            output(message)

    emit("=== Scripted demo ===")

    identity = IdentityAttributes(
        digital_id="did-1",
        national_id="nat-1",
        date_of_birth="1990-01-01",
    )
    mutable = MutableAttributes(
        name="Ava Example",
        address="1 High Street, London",
        email="ava@example.com",
        phone="0000000000",
    )

    created = context.identity_service.create_identity(identity, mutable, Role.CENTRAL)
    emit("Create identity: OK")

    updated_mutable = MutableAttributes(
        name=mutable.name,
        address="2 High Street, London",
        email=mutable.email,
        phone=mutable.phone,
    )
    context.identity_service.update_mutable(
        created.identity.digital_id,
        updated_mutable,
        Role.CENTRAL,
    )
    emit("Update identity: OK")

    try:
        context.identity_service.create_identity(
            identity,
            MutableAttributes(
                name="Other",
                address="99 Example Road",
                email="other@example.com",
                phone="0000000000",
            ),
            Role.CENTRAL,
        )
        emit("Duplicate identity: OK")
    except DuplicateIdentityError:
        emit("Duplicate identity: FAIL")

    try:
        context.identity_service.change_status(
            created.identity.digital_id,
            Status.REVOKED,
            "fraud",
            Role.LOCAL,
        )
        emit("Unauthorized revoke: OK")
    except AuthorizationError:
        emit("Unauthorized revoke: FAIL")

    context.identity_service.change_status(
        created.identity.digital_id,
        Status.SUSPENDED,
        "review",
        Role.CENTRAL,
    )
    emit("Suspend identity: OK")

    tax_result = context.verification_service.verify_tax(
        created,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        as_of=date(2026, 4, 1),
    )
    emit(f"Tax verification while suspended: {'OK' if tax_result.eligible else 'FAIL'}")

    context.identity_service.change_status(
        created.identity.digital_id,
        Status.ACTIVE,
        "appeal granted",
        Role.CENTRAL,
    )
    emit("Reactivate identity: OK")

    created.add_restriction(Restriction(name="driving_suspension", start=date(2026, 1, 1)))
    context.repository.update(created)

    driving_result = context.verification_service.verify_driving_licence(
        created,
        as_of=date(2026, 2, 1),
        restriction_keywords=["driving"],
    )
    emit(f"Driving verification with restriction: {'OK' if driving_result.eligible else 'FAIL'}")

    created.replace_restrictions([])
    context.repository.update(created)

    driving_result = context.verification_service.verify_driving_licence(
        created,
        as_of=date(2026, 2, 1),
        restriction_keywords=["driving"],
    )
    emit(f"Driving verification after clear: {'OK' if driving_result.eligible else 'FAIL'}")

    local_result = context.verification_service.verify_local_authority(
        created,
        required_locality="Leeds",
    )
    emit(f"Local authority check mismatch: {'OK' if local_result.eligible else 'FAIL'}")

    local_result = context.verification_service.verify_local_authority(
        created,
        required_locality="London",
    )
    emit(f"Local authority check match: {'OK' if local_result.eligible else 'FAIL'}")

    bank_result = context.verification_service.verify_bank_employer(created)
    emit(f"Bank/employer check: {'OK' if bank_result.eligible else 'FAIL'}")

    emit(f"Audit entries recorded: {len(context.audit_log.list_all())}")

    if audit_path is not None:
        context.audit_log.export_json(audit_path)
        emit(f"Audit export: {audit_path}")
    else:
        emit("Audit export: skipped")

    return lines

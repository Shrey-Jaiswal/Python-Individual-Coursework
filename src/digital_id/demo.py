"""Scripted demo scenario for the Digital ID backend."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from digital_id.domain import (
    IdentityAttributes,
    ImmutableAttributeError,
    InvalidStatusTransition,
    MutableAttributes,
    Restriction,
    Status,
)
from digital_id.persistence import DigitalIdRepository, InMemoryRepository
from digital_id.persistence.errors import DuplicateIdentityError
from digital_id.services import (
    AuditLog,
    AuthorizationError,
    AuthorizationService,
    IdentityService,
    IdentityUpdateNotAllowedError,
    Role,
    ValidationService,
    VerificationService,
)


@dataclass
class DemoContext:
    repository: DigitalIdRepository
    identity_service: IdentityService
    verification_service: VerificationService
    audit_log: AuditLog


def build_demo_context(
    repository: DigitalIdRepository | None = None,
    audit_log: AuditLog | None = None,
) -> DemoContext:
    if repository is None:
        repository = InMemoryRepository()
    if audit_log is None:
        audit_log = AuditLog()
    auth = AuthorizationService()
    validator = ValidationService()

    def demo_clock() -> datetime:
        return datetime(2026, 2, 15, 12, 0, tzinfo=UTC)

    identity_service = IdentityService(repository, auth, validator, audit_log, clock=demo_clock)
    verification_service = VerificationService(
        repository,
        auth_service=auth,
        audit_log=audit_log,
    )
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
    step = 0

    def emit(message: str) -> None:
        lines.append(message)
        if output is not None:
            output(message)

    def emit_step(label: str, outcome: str) -> None:
        nonlocal step
        step += 1
        emit(f"{step:02d} {label:<30} {outcome}")

    def format_expected(eligible: bool, expected: bool) -> str:
        status = "ELIGIBLE" if eligible else "INELIGIBLE"
        suffix = "expected" if eligible == expected else "unexpected"
        return f"{status} ({suffix})"

    emit("Scripted demo")

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
    emit_step("Create identity", "PASS")

    context.identity_service.change_status(
        created.digital_id,
        Status.ACTIVE,
        "already active",
        Role.CENTRAL,
    )
    emit_step("Repeat active status", "NO-OP (expected)")

    updated_mutable = MutableAttributes(
        name=mutable.name,
        address="2 High Street, London",
        email=mutable.email,
        phone=mutable.phone,
    )
    context.identity_service.update_mutable(
        created.digital_id,
        updated_mutable,
        Role.CENTRAL,
    )
    emit_step("Update identity", "PASS")

    try:
        agg = context.repository.get_by_id(created.digital_id)
        agg.update_immutable(
            IdentityAttributes(
                digital_id=created.digital_id,
                national_id="changed-national-id",
                date_of_birth=created.date_of_birth,
            )
        )
        immutable_outcome = "ACCEPTED (unexpected)"
    except ImmutableAttributeError:
        immutable_outcome = "REJECTED (expected)"
    emit_step("Domain immutable update", immutable_outcome)

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
        duplicate_outcome = "ACCEPTED (unexpected)"
    except DuplicateIdentityError:
        duplicate_outcome = "REJECTED (expected)"
    emit_step("Duplicate identity", duplicate_outcome)

    try:
        context.identity_service.change_status(
            created.digital_id,
            Status.REVOKED,
            "fraud",
            Role.LOCAL,
        )
        revoke_outcome = "ACCEPTED (unexpected)"
    except AuthorizationError:
        revoke_outcome = "REJECTED (expected)"
    emit_step("Unauthorized revoke", revoke_outcome)

    try:
        context.verification_service.verify_tax(
            created.digital_id,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 3, 31),
            role=Role.BANK_EMPLOYER,
            as_of=date(2026, 4, 1),
        )
        verify_outcome = "ACCEPTED (unexpected)"
    except AuthorizationError:
        verify_outcome = "REJECTED (expected)"
    emit_step("Unauthorized verification", verify_outcome)

    context.identity_service.change_status(
        created.digital_id,
        Status.SUSPENDED,
        "review",
        Role.CENTRAL,
    )
    emit_step("Suspend identity", "PASS")

    tax_result = context.verification_service.verify_tax(
        created.digital_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 4, 1),
    )
    emit_step(
        "Tax verification (suspended)",
        format_expected(tax_result.eligible, expected=False),
    )

    context.identity_service.change_status(
        created.digital_id,
        Status.ACTIVE,
        "appeal granted",
        Role.CENTRAL,
    )
    emit_step("Reactivate identity", "PASS")

    tax_result = context.verification_service.verify_tax(
        created.digital_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 4, 1),
    )
    emit_step(
        "Tax verification (history)",
        format_expected(tax_result.eligible, expected=False),
    )

    unfinished_tax = context.verification_service.verify_tax(
        created.digital_id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        role=Role.TAX_AUTHORITY,
        as_of=date(2026, 4, 1),
    )
    emit_step(
        "Tax period check failure",
        format_expected(unfinished_tax.eligible, expected=False),
    )

    context.identity_service.add_restriction(
        created.digital_id,
        Restriction(name="driving_suspension", start=date(2026, 1, 1)),
        Role.CENTRAL,
    )
    emit_step("Add restriction", "PASS")

    try:
        context.identity_service.add_restriction(
            created.digital_id,
            Restriction(name="local_hold", start=date(2026, 1, 1)),
            Role.LOCAL,
        )
        restriction_outcome = "ACCEPTED (unexpected)"
    except AuthorizationError:
        restriction_outcome = "REJECTED (expected)"
    emit_step("Unauthorized restriction", restriction_outcome)

    driving_result = context.verification_service.verify_driving_licence(
        created.digital_id,
        role=Role.DRIVING_LICENCE_AUTHORITY,
        as_of=date(2026, 2, 1),
        restriction_keywords=["driving"],
    )
    emit_step(
        "Driving verification (restriction)",
        format_expected(driving_result.eligible, expected=False),
    )

    context.identity_service.replace_restrictions(created.digital_id, [], Role.CENTRAL)
    emit_step("Clear restrictions", "PASS")

    driving_result = context.verification_service.verify_driving_licence(
        created.digital_id,
        role=Role.DRIVING_LICENCE_AUTHORITY,
        as_of=date(2026, 2, 1),
        restriction_keywords=["driving"],
    )
    emit_step(
        "Driving verification (cleared)",
        format_expected(driving_result.eligible, expected=True),
    )

    local_result = context.verification_service.verify_local_authority(
        created.digital_id,
        role=Role.LOCAL,
        required_locality="Leeds",
    )
    emit_step(
        "Local authority (mismatch)",
        format_expected(local_result.eligible, expected=False),
    )

    local_result = context.verification_service.verify_local_authority(
        created.digital_id,
        role=Role.LOCAL,
        required_locality="London",
    )
    emit_step(
        "Local authority (match)",
        format_expected(local_result.eligible, expected=True),
    )

    bank_result = context.verification_service.verify_bank_employer(
        created.digital_id,
        role=Role.BANK_EMPLOYER,
    )
    emit_step(
        "Bank/employer check",
        format_expected(bank_result.eligible, expected=True),
    )

    missing_result = context.verification_service.verify_bank_employer(
        "missing-id",
        role=Role.BANK_EMPLOYER,
    )
    emit_step(
        "Missing identity lookup",
        format_expected(missing_result.eligible, expected=False),
    )

    context.identity_service.change_status(
        created.digital_id,
        Status.REVOKED,
        "fraud confirmed",
        Role.CENTRAL,
    )
    emit_step("Revoke identity", "PASS")

    try:
        context.identity_service.update_mutable(
            created.digital_id,
            MutableAttributes(
                name=mutable.name,
                address="3 High Street, London",
                email=mutable.email,
                phone=mutable.phone,
            ),
            Role.CENTRAL,
        )
        update_revoked = "ACCEPTED (unexpected)"
    except IdentityUpdateNotAllowedError:
        update_revoked = "REJECTED (expected)"
    emit_step("Update revoked identity", update_revoked)

    try:
        context.identity_service.change_status(
            created.digital_id,
            Status.ACTIVE,
            "appeal",
            Role.CENTRAL,
        )
        reactivate_revoked = "ACCEPTED (unexpected)"
    except InvalidStatusTransition:
        reactivate_revoked = "REJECTED (expected)"
    emit_step("Reactivate revoked identity", reactivate_revoked)

    audit_entries = len(context.audit_log.list_all())

    if audit_path is not None:
        context.audit_log.export_json(audit_path)
        export_label = str(audit_path)
    else:
        export_label = "skipped"

    emit(f"Audit entries: {audit_entries}")
    emit(f"Audit export: {export_label}")

    return lines

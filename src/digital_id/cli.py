"""Console entrypoint for the Digital ID backend."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from digital_id.demo import DemoContext, build_demo_context, run_scripted_demo
from digital_id.domain import IdentityAttributes, MutableAttributes, Status
from digital_id.services import Role


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Digital ID backend demo runner")
    parser.add_argument(
        "--scripted-only",
        action="store_true",
        help="Run scripted demo only and skip interactive menu",
    )
    parser.add_argument(
        "--audit-path",
        default="audit_log.json",
        help="Path to write audit log JSON (scripted demo)",
    )
    args = parser.parse_args(argv)

    context = build_demo_context()
    audit_path = Path(args.audit_path) if args.audit_path else None
    run_scripted_demo(context, audit_path=audit_path, output=print)

    if args.scripted_only:
        return 0

    run_interactive_menu(context, input_fn=input, output=print)
    return 0


def run_interactive_menu(
    context: DemoContext,
    input_fn: Callable[[str], str],
    output: Callable[[str], None],
) -> None:
    output("=== Interactive menu ===")
    while True:
        output("1) List identities")
        output("2) Create identity")
        output("3) Update mutable fields")
        output("4) Change status")
        output("5) Verify identity")
        output("6) Export audit log")
        output("0) Exit")
        choice = input_fn("Select option: ").strip()

        if choice == "1":
            identities = context.repository.list_all()
            if not identities:
                output("No identities available.")
                continue
            for entry in identities:
                summary = (
                    f"{entry.identity.digital_id} | {entry.status.value} | "
                    f"{entry.mutable.name} | {entry.mutable.address}"
                )
                output(summary)
        elif choice == "2":
            identity = _prompt_identity(input_fn)
            mutable = _prompt_mutable(input_fn)
            try:
                context.identity_service.create_identity(identity, mutable, Role.CENTRAL)
                output("Created identity.")
            except Exception as exc:
                output(f"Error: {exc}")
        elif choice == "3":
            digital_id = input_fn("Digital ID: ").strip()
            mutable = _prompt_mutable(input_fn)
            try:
                context.identity_service.update_mutable(digital_id, mutable, Role.CENTRAL)
                output("Updated identity.")
            except Exception as exc:
                output(f"Error: {exc}")
        elif choice == "4":
            digital_id = input_fn("Digital ID: ").strip()
            status_value = input_fn("New status (active/suspended/revoked): ").strip().lower()
            reason = input_fn("Reason: ").strip() or "unspecified"
            try:
                status = Status(status_value)
            except ValueError:
                output("Invalid status.")
                continue
            try:
                context.identity_service.change_status(digital_id, status, reason, Role.CENTRAL)
                output("Status updated.")
            except Exception as exc:
                output(f"Error: {exc}")
        elif choice == "5":
            _handle_verification(context, input_fn, output)
        elif choice == "6":
            path_value = input_fn("Audit path (default audit_log.json): ").strip()
            path = Path(path_value) if path_value else Path("audit_log.json")
            try:
                context.audit_log.export_json(path)
                output(f"Audit log exported to {path}")
            except Exception as exc:
                output(f"Error: {exc}")
        elif choice == "0":
            output("Goodbye.")
            return
        else:
            output("Unknown option.")


def _prompt_identity(input_fn: Callable[[str], str]) -> IdentityAttributes:
    digital_id = input_fn("Digital ID: ").strip()
    national_id = input_fn("National ID: ").strip()
    date_of_birth = input_fn("Date of birth (YYYY-MM-DD): ").strip()
    return IdentityAttributes(
        digital_id=digital_id,
        national_id=national_id,
        date_of_birth=date_of_birth,
    )


def _prompt_mutable(input_fn: Callable[[str], str]) -> MutableAttributes:
    name = input_fn("Name: ").strip()
    address = input_fn("Address: ").strip()
    email = input_fn("Email: ").strip()
    phone = input_fn("Phone: ").strip()
    return MutableAttributes(
        name=name,
        address=address,
        email=email,
        phone=phone,
    )


def _handle_verification(
    context: DemoContext,
    input_fn: Callable[[str], str],
    output: Callable[[str], None],
) -> None:
    output("a) Tax authority")
    output("b) Driving licence")
    output("c) Local authority")
    output("d) Bank/employer")
    choice = input_fn("Select verification: ").strip().lower()
    digital_id = input_fn("Digital ID: ").strip()

    try:
        identity = context.repository.get_by_id(digital_id)
    except Exception as exc:
        output(f"Error: {exc}")
        return

    if choice == "a":
        try:
            period_start = _prompt_date(input_fn, "Period start (YYYY-MM-DD): ")
            period_end = _prompt_date(input_fn, "Period end (YYYY-MM-DD): ")
        except ValueError as exc:
            output(str(exc))
            return
        result = context.verification_service.verify_tax(
            identity,
            period_start,
            period_end,
            role=Role.TAX_AUTHORITY,
        )
    elif choice == "b":
        keywords_raw = input_fn(
            "Restriction keywords (comma separated, optional): "
        ).strip()
        keywords = (
            [k.strip() for k in keywords_raw.split(",") if k.strip()]
            if keywords_raw
            else None
        )
        result = context.verification_service.verify_driving_licence(
            identity,
            role=Role.DRIVING_LICENCE_AUTHORITY,
            restriction_keywords=keywords,
        )
    elif choice == "c":
        locality = input_fn("Required locality (optional): ").strip() or None
        result = context.verification_service.verify_local_authority(
            identity,
            role=Role.LOCAL,
            required_locality=locality,
        )
    elif choice == "d":
        result = context.verification_service.verify_bank_employer(
            identity,
            role=Role.BANK_EMPLOYER,
        )
    else:
        output("Unknown verification type.")
        return

    output(f"Eligible: {result.eligible} ({result.reason})")


def _prompt_date(input_fn: Callable[[str], str], label: str) -> date:
    value = input_fn(label).strip()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.") from exc


if __name__ == "__main__":
    raise SystemExit(main())

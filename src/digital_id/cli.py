"""Console entrypoint for the Digital ID backend."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from digital_id.demo import DemoContext, build_demo_context, run_scripted_demo
from digital_id.domain import IdentityAttributes, MutableAttributes, Status
from digital_id.persistence import JsonBackedRepository
from digital_id.services import AuditLog, Role

# ANSI Colors and Styles
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
UNDERLINE = "\033[4m"

# Text Colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[97m"
GRAY = "\033[90m"


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
    parser.add_argument(
        "--store-path",
        help="Path to JSON identity store for persistent interactive runs",
    )
    parser.add_argument(
        "--interactive-only",
        action="store_true",
        help="Skip the scripted demo and open the interactive menu",
    )
    args = parser.parse_args(argv)
    if args.scripted_only and args.interactive_only:
        parser.error("--scripted-only and --interactive-only cannot be used together")

    context = (
        _build_runtime_context(args.store_path, args.audit_path)
        if args.interactive_only
        else build_demo_context()
    )
    if not args.interactive_only:
        audit_path = Path(args.audit_path) if args.audit_path else None
        run_scripted_demo(context, audit_path=audit_path, output=print)

    if args.scripted_only:
        return 0

    if args.store_path and not args.interactive_only:
        context = _build_runtime_context(args.store_path, args.audit_path)
    run_interactive_menu(context, input_fn=input, output=print)
    return 0


def _build_runtime_context(store_path: str | None, audit_path: str | None) -> DemoContext:
    audit_log = AuditLog(Path(audit_path)) if audit_path else AuditLog()
    if store_path is None:
        return build_demo_context(audit_log=audit_log)
    repository = JsonBackedRepository.from_path(Path(store_path))
    return build_demo_context(repository=repository, audit_log=audit_log)


def _print_header(output: Callable[[str], None]) -> None:
    output(
        f"\n{CYAN}{BOLD}┌────────────────────────────────"
        f"────────────────────────┐{RESET}"
    )
    output(f"{CYAN}{BOLD}│             DIGITAL IDENTITY CONTROL SYSTEM            │{RESET}")
    output(f"{CYAN}{BOLD}│              Coursework Backend Terminal               │{RESET}")
    output(
        f"{CYAN}{BOLD}└────────────────────────────────"
        f"────────────────────────┘{RESET}\n"
    )


def _print_success(message: str, output: Callable[[str], None]) -> None:
    output(f"\n{GREEN}{BOLD}✔ SUCCESS: {message}{RESET}\n")


def _print_error(message: str, output: Callable[[str], None]) -> None:
    output(f"\n{RED}{BOLD}✘ ERROR: {message}{RESET}\n")


def _print_info(message: str, output: Callable[[str], None]) -> None:
    output(f"{GRAY}ℹ {message}{RESET}")


def _render_table(headers: list[str], rows: list[list[str]], output: Callable[[str], None]) -> None:
    # Calculate widths based on raw string lengths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(val))

    # Top border
    top = f"{CYAN}┌" + f"{CYAN}─" * (widths[0] + 2)
    for w in widths[1:]:
        top += "┬" + "─" * (w + 2)
    top += f"┐{RESET}"
    output(top)

    # Headers
    header_line = f"{CYAN}│{RESET}"
    for i, h in enumerate(headers):
        header_line += f" {BOLD}{WHITE}{h:<{widths[i]}}{RESET} {CYAN}│{RESET}"
    output(header_line)

    # Divider
    divider = f"{CYAN}├" + "─" * (widths[0] + 2)
    for w in widths[1:]:
        divider += "┼" + "─" * (w + 2)
    divider += f"┤{RESET}"
    output(divider)

    # Rows
    for row in rows:
        row_line = f"{CYAN}│{RESET}"
        for i, val in enumerate(row):
            if i == 1:  # Status column
                if val == "ACTIVE":
                    formatted = f"{GREEN}{BOLD}{val:<{widths[i]}}{RESET}"
                elif val == "SUSPENDED":
                    formatted = f"{YELLOW}{BOLD}{val:<{widths[i]}}{RESET}"
                elif val == "REVOKED":
                    formatted = f"{RED}{BOLD}{val:<{widths[i]}}{RESET}"
                else:
                    formatted = f"{val:<{widths[i]}}"
            else:
                formatted = f"{val:<{widths[i]}}"
            row_line += f" {formatted} {CYAN}│{RESET}"
        output(row_line)

    # Bottom border
    bottom = f"{CYAN}└" + "─" * (widths[0] + 2)
    for w in widths[1:]:
        bottom += "┴" + "─" * (w + 2)
    bottom += f"┘{RESET}"
    output(bottom)


def run_interactive_menu(
    context: DemoContext,
    input_fn: Callable[[str], str],
    output: Callable[[str], None],
) -> None:
    _print_header(output)

    while True:
        output(
            f"{CYAN}{BOLD}┌─── CONTROL CENTER ─────────────────────────────────────┐{RESET}"
        )
        output(
            f"{CYAN}{BOLD}│{RESET}  {BOLD}[1]{RESET} List All Registered Identities"
            f"                    {CYAN}{BOLD}│{RESET}"
        )
        output(
            f"{CYAN}{BOLD}│{RESET}  {BOLD}[2]{RESET} Create New Digital Identity"
            f"                       {CYAN}{BOLD}│{RESET}"
        )
        output(
            f"{CYAN}{BOLD}│{RESET}  {BOLD}[3]{RESET} Update Mutable Attributes "
            f"(Address, Phone, etc)   {CYAN}{BOLD}│{RESET}"
        )
        output(
            f"{CYAN}{BOLD}│{RESET}  {BOLD}[4]{RESET} Transition Lifecycle Status"
            f"                       {CYAN}{BOLD}│{RESET}"
        )
        output(
            f"{CYAN}{BOLD}│{RESET}  {BOLD}[5]{RESET} Perform Verification Audit Checks"
            f"                 {CYAN}{BOLD}│{RESET}"
        )
        output(
            f"{CYAN}{BOLD}│{RESET}  {BOLD}[6]{RESET} Export Safe JSON Audit Trail"
            f"                      {CYAN}{BOLD}│{RESET}"
        )
        output(
            f"{CYAN}{BOLD}│{RESET}  {BOLD}[0]{RESET} Terminate Console Session"
            f"                         {CYAN}{BOLD}│{RESET}"
        )
        output(
            f"{CYAN}{BOLD}└────────────────────────────────────────────────────────┘{RESET}"
        )

        choice = input_fn(
            f"{CYAN}{BOLD}❯{RESET} {BOLD}Select option{RESET} "
            f"{GRAY}[0-6]{RESET}: "
        ).strip()

        if choice == "1":
            identities = context.identity_service.list_identities(Role.CENTRAL)
            if not identities:
                _print_info("No identities available.", output)
                output("")
                continue

            headers = ["Digital ID", "Status", "Name", "Email", "Address"]
            rows = []
            for entry in identities:
                rows.append([
                    entry.digital_id,
                    entry.status.value.upper(),
                    entry.name,
                    entry.email,
                    entry.address,
                ])
            _render_table(headers, rows, output)
            output("")
        elif choice == "2":
            output(
                f"\n{CYAN}{BOLD}┌─── REGISTER IDENTITY ──────────────────────────────────┐{RESET}"
            )
            output(
                f"{CYAN}{BOLD}│{RESET} Please provide core identity details below:           "
                f"{CYAN}{BOLD}│{RESET}"
            )
            output(
                f"{CYAN}{BOLD}└────────────────────────────────────────────────────────┘{RESET}"
            )
            identity = _prompt_identity(input_fn)
            output(
                f"\n{CYAN}{BOLD}┌─── MUTABLE ATTRIBUTES ─────────────────────────────────┐{RESET}"
            )
            output(
                f"{CYAN}{BOLD}│{RESET} Please provide mutable profile attributes below:      "
                f"{CYAN}{BOLD}│{RESET}"
            )
            output(
                f"{CYAN}{BOLD}└────────────────────────────────────────────────────────┘{RESET}"
            )
            mutable = _prompt_mutable(input_fn)
            try:
                context.identity_service.create_identity(identity, mutable, Role.CENTRAL)
                _print_success("Created identity.", output)
            except Exception as exc:
                _print_error(str(exc), output)
        elif choice == "3":
            output(
                f"\n{CYAN}{BOLD}┌─── UPDATE PROFILE ─────────────────────────────────────┐{RESET}"
            )
            output(
                f"{CYAN}{BOLD}│{RESET} Retrieve and modify mutable attributes of a record:    "
                f"{CYAN}{BOLD}│{RESET}"
            )
            output(
                f"{CYAN}{BOLD}└────────────────────────────────────────────────────────┘{RESET}"
            )
            digital_id = input_fn(f"  {CYAN}❯{RESET} {BOLD}Digital ID{RESET}: ").strip()
            if not digital_id:
                _print_error("Digital ID is required.", output)
                continue
            output(f"\n{CYAN}  Enter updated attributes below:{RESET}")
            mutable = _prompt_mutable(input_fn)
            try:
                context.identity_service.update_mutable(digital_id, mutable, Role.CENTRAL)
                _print_success("Updated identity.", output)
            except Exception as exc:
                _print_error(str(exc), output)
        elif choice == "4":
            output(
                f"\n{CYAN}{BOLD}┌─── LIFECYCLE TRANSITION ───────────────────────────────┐{RESET}"
            )
            output(
                f"{CYAN}{BOLD}│{RESET} Move a Digital ID record between lifecycle statuses:   "
                f"{CYAN}{BOLD}│{RESET}"
            )
            output(
                f"{CYAN}{BOLD}└────────────────────────────────────────────────────────┘{RESET}"
            )
            digital_id = input_fn(f"  {CYAN}❯{RESET} {BOLD}Digital ID{RESET}: ").strip()
            if not digital_id:
                _print_error("Digital ID is required.", output)
                continue

            output(
                f"  Available statuses: {GREEN}active{RESET}, "
                f"{YELLOW}suspended{RESET}, {RED}revoked{RESET}"
            )
            status_value = input_fn(
                f"  {CYAN}❯{RESET} {BOLD}New status (active/suspended/revoked){RESET}: "
            ).strip().lower()
            reason = input_fn(f"  {CYAN}❯{RESET} {BOLD}Reason{RESET}: ").strip() or "unspecified"
            try:
                status = Status(status_value)
            except ValueError:
                _print_error("Invalid status.", output)
                continue
            try:
                context.identity_service.change_status(digital_id, status, reason, Role.CENTRAL)
                _print_success("Status updated.", output)
            except Exception as exc:
                _print_error(str(exc), output)
        elif choice == "5":
            _handle_verification(context, input_fn, output)
        elif choice == "6":
            output(
                f"\n{CYAN}{BOLD}┌─── AUDIT EXPORT ───────────────────────────────────────┐{RESET}"
            )
            output(
                f"{CYAN}{BOLD}│{RESET} Dump full chronological trace of system log actions:   "
                f"{CYAN}{BOLD}│{RESET}"
            )
            output(
                f"{CYAN}{BOLD}└────────────────────────────────────────────────────────┘{RESET}"
            )
            path_value = input_fn(
                f"  {CYAN}❯{RESET} {BOLD}Audit path (default audit_log.json){RESET}: "
            ).strip()
            path = Path(path_value) if path_value else Path("audit_log.json")
            try:
                context.audit_log.export_json(path)
                _print_success(f"Audit log exported to {path}", output)
            except Exception as exc:
                _print_error(str(exc), output)
        elif choice == "0":
            output(
                f"\n{CYAN}{BOLD}┌────────────────────────────────"
                f"────────────────────────┐{RESET}"
            )
            output(f"{CYAN}{BOLD}│              Exiting Digital ID Control System         │{RESET}")
            output(f"{CYAN}{BOLD}│                        Goodbye!                        │{RESET}")
            output(
                f"{CYAN}{BOLD}└────────────────────────────────"
                f"────────────────────────┘{RESET}\n"
            )
            return
        else:
            _print_error("Unknown option.", output)


def _prompt_identity(input_fn: Callable[[str], str]) -> IdentityAttributes:
    digital_id = input_fn(f"  {CYAN}❯{RESET} {BOLD}Digital ID{RESET}: ").strip()
    national_id = input_fn(f"  {CYAN}❯{RESET} {BOLD}National ID{RESET}: ").strip()
    date_of_birth = input_fn(
        f"  {CYAN}❯{RESET} {BOLD}Date of birth (YYYY-MM-DD){RESET}: "
    ).strip()
    return IdentityAttributes(
        digital_id=digital_id,
        national_id=national_id,
        date_of_birth=date_of_birth,
    )


def _prompt_mutable(input_fn: Callable[[str], str]) -> MutableAttributes:
    name = input_fn(f"  {CYAN}❯{RESET} {BOLD}Name{RESET}: ").strip()
    address = input_fn(f"  {CYAN}❯{RESET} {BOLD}Address{RESET}: ").strip()
    email = input_fn(f"  {CYAN}❯{RESET} {BOLD}Email{RESET}: ").strip()
    phone = input_fn(f"  {CYAN}❯{RESET} {BOLD}Phone{RESET}: ").strip()
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
    output(
        f"\n{CYAN}{BOLD}┌─── VERIFICATION PORTAL ────────────────────────────────┐{RESET}"
    )
    output(
        f"{CYAN}{BOLD}│{RESET} Select the verification authority role:               "
        f"{CYAN}{BOLD}│{RESET}"
    )
    output(
        f"{CYAN}{BOLD}├────────────────────────────────────────────────────────┤{RESET}"
    )
    output(
        f"{CYAN}{BOLD}│{RESET}  {BOLD}[a]{RESET} Tax Authority Verification                        "
        f"{CYAN}{BOLD}│{RESET}"
    )
    output(
        f"{CYAN}{BOLD}│{RESET}  {BOLD}[b]{RESET} Driving Licence Authority Verification            "
        f"{CYAN}{BOLD}│{RESET}"
    )
    output(
        f"{CYAN}{BOLD}│{RESET}  {BOLD}[c]{RESET} Local Authority Location Verification            "
        f"{CYAN}{BOLD}│{RESET}"
    )
    output(
        f"{CYAN}{BOLD}│{RESET}  {BOLD}[d]{RESET} Bank / Employer General Verification             "
        f"{CYAN}{BOLD}│{RESET}"
    )
    output(
        f"{CYAN}{BOLD}└────────────────────────────────────────────────────────┘{RESET}"
    )
    choice = input_fn(f"  {CYAN}❯{RESET} {BOLD}Select verification{RESET}: ").strip().lower()
    digital_id = input_fn(f"  {CYAN}❯{RESET} {BOLD}Digital ID{RESET}: ").strip()

    if choice == "a":
        try:
            period_start = _prompt_date(
                input_fn,
                f"  {CYAN}❯{RESET} {BOLD}Period start (YYYY-MM-DD){RESET}: "
            )
            period_end = _prompt_date(
                input_fn,
                f"  {CYAN}❯{RESET} {BOLD}Period end (YYYY-MM-DD){RESET}: "
            )
        except ValueError as exc:
            _print_error(str(exc), output)
            return
        result = context.verification_service.verify_tax(
            digital_id,
            period_start,
            period_end,
            role=Role.TAX_AUTHORITY,
        )
    elif choice == "b":
        keywords_raw = input_fn(
            f"  {CYAN}❯{RESET} "
            f"{BOLD}Restriction keywords (comma separated, optional){RESET}: "
        ).strip()
        keywords = (
            [k.strip() for k in keywords_raw.split(",") if k.strip()]
            if keywords_raw
            else None
        )
        result = context.verification_service.verify_driving_licence(
            digital_id,
            role=Role.DRIVING_LICENCE_AUTHORITY,
            restriction_keywords=keywords,
        )
    elif choice == "c":
        locality = input_fn(
            f"  {CYAN}❯{RESET} {BOLD}Required locality (optional){RESET}: "
        ).strip() or None
        result = context.verification_service.verify_local_authority(
            digital_id,
            role=Role.LOCAL,
            required_locality=locality,
        )
    elif choice == "d":
        result = context.verification_service.verify_bank_employer(
            digital_id,
            role=Role.BANK_EMPLOYER,
        )
    else:
        _print_error("Unknown verification type.", output)
        return

    # Print a beautiful verification card report
    output(
        f"\n{CYAN}{BOLD}┌─── VERIFICATION DECISION CARD ─────────────────────────┐{RESET}"
    )
    status_label = (
        f"{GREEN}{BOLD}PASS (ELIGIBLE){RESET}"
        if result.eligible
        else f"{RED}{BOLD}FAIL (INELIGIBLE){RESET}"
    )
    output(f"{CYAN}{BOLD}│{RESET}  {BOLD}Eligible:{RESET} {status_label:<47} {CYAN}{BOLD}│{RESET}")
    reason_label = result.reason
    if len(reason_label) > 42:
        reason_label = reason_label[:39] + "..."
    output(f"{CYAN}{BOLD}│{RESET}  {BOLD}Reason:{RESET}   {reason_label:<41} {CYAN}{BOLD}│{RESET}")
    output(f"{CYAN}{BOLD}└────────────────────────────────────────────────────────┘{RESET}\n")


def _prompt_date(input_fn: Callable[[str], str], label: str) -> date:
    value = input_fn(label).strip()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.") from exc


if __name__ == "__main__":
    raise SystemExit(main())

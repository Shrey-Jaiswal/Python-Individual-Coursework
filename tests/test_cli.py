import runpy
from pathlib import Path

import pytest

import digital_id.cli
from digital_id.cli import main, run_interactive_menu
from digital_id.demo import build_demo_context
from digital_id.domain import IdentityAttributes, MutableAttributes
from digital_id.services import Role


def test_cli_verification_flow_outputs_result() -> None:
    context = build_demo_context()
    identity = IdentityAttributes(
        digital_id="did-1",
        national_id="nat-1",
        date_of_birth="1990-01-01",
    )
    mutable = MutableAttributes(
        name="Ava Example",
        address="1 High Street",
        email="ava@example.com",
        phone="0000000000",
    )
    context.identity_service.create_identity(identity, mutable, Role.CENTRAL)

    inputs = [
        "5",  # verify identity
        "d",  # bank/employer
        "did-1",
        "0",  # exit
    ]
    outputs: list[str] = []

    def input_fn(_: str) -> str:
        if not inputs:
            raise AssertionError("No more inputs available")
        return inputs.pop(0)

    def output_fn(message: str) -> None:
        outputs.append(message)

    run_interactive_menu(context, input_fn=input_fn, output=output_fn)

    assert any(line.startswith("Eligible:") for line in outputs)


def test_cli_create_and_list_identity() -> None:
    context = build_demo_context()

    inputs = [
        "2",
        "did-1",
        "nat-1",
        "1990-01-01",
        "Ava Example",
        "1 High Street",
        "ava@example.com",
        "0000000000",
        "1",
        "0",
    ]
    outputs: list[str] = []

    def input_fn(_: str) -> str:
        if not inputs:
            raise AssertionError("No more inputs available")
        return inputs.pop(0)

    def output_fn(message: str) -> None:
        outputs.append(message)

    run_interactive_menu(context, input_fn=input_fn, output=output_fn)

    assert "Created identity." in outputs
    assert any("did-1 | active" in line for line in outputs)


def test_cli_update_and_status_change() -> None:
    context = build_demo_context()
    identity = IdentityAttributes(
        digital_id="did-1",
        national_id="nat-1",
        date_of_birth="1990-01-01",
    )
    mutable = MutableAttributes(
        name="Ava Example",
        address="1 High Street",
        email="ava@example.com",
        phone="0000000000",
    )
    context.identity_service.create_identity(identity, mutable, Role.CENTRAL)

    inputs = [
        "3",
        "did-1",
        "Ava Example",
        "2 High Street",
        "ava@example.com",
        "0000000000",
        "4",
        "did-1",
        "suspended",
        "review",
        "0",
    ]
    outputs: list[str] = []

    def input_fn(_: str) -> str:
        if not inputs:
            raise AssertionError("No more inputs available")
        return inputs.pop(0)

    def output_fn(message: str) -> None:
        outputs.append(message)

    run_interactive_menu(context, input_fn=input_fn, output=output_fn)

    assert "Updated identity." in outputs
    assert "Status updated." in outputs


def test_cli_tax_verification_rejects_invalid_date() -> None:
    context = build_demo_context()
    identity = IdentityAttributes(
        digital_id="did-1",
        national_id="nat-1",
        date_of_birth="1990-01-01",
    )
    mutable = MutableAttributes(
        name="Ava Example",
        address="1 High Street",
        email="ava@example.com",
        phone="0000000000",
    )
    context.identity_service.create_identity(identity, mutable, Role.CENTRAL)

    inputs = [
        "5",
        "a",
        "did-1",
        "bad-date",
        "0",
    ]
    outputs: list[str] = []

    def input_fn(_: str) -> str:
        if not inputs:
            raise AssertionError("No more inputs available")
        return inputs.pop(0)

    def output_fn(message: str) -> None:
        outputs.append(message)

    run_interactive_menu(context, input_fn=input_fn, output=output_fn)

    assert any("Invalid date format" in line for line in outputs)


def test_main_scripted_only_exports_audit(tmp_path: Path) -> None:
    audit_path = tmp_path / "audit.json"

    result = main(["--scripted-only", "--audit-path", str(audit_path)])

    assert result == 0
    assert audit_path.exists()


def test_module_entrypoint_uses_cli_main(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(digital_id.cli, "main", lambda: 0)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("digital_id.__main__", run_name="__main__")

    assert exc.value.code == 0


def test_cli_empty_list_invalid_status_export_and_unknown(tmp_path: Path) -> None:
    context = build_demo_context()
    audit_path = tmp_path / "audit.json"

    inputs = [
        "1",
        "4",
        "missing",
        "invalid",
        "reason",
        "6",
        str(audit_path),
        "x",
        "0",
    ]
    outputs: list[str] = []

    def input_fn(_: str) -> str:
        if not inputs:
            raise AssertionError("No more inputs available")
        return inputs.pop(0)

    run_interactive_menu(context, input_fn=input_fn, output=outputs.append)

    assert "No identities available." in outputs
    assert "Invalid status." in outputs
    assert any(line.startswith("Audit log exported") for line in outputs)
    assert "Unknown option." in outputs


def test_cli_tax_driving_and_local_verification_paths() -> None:
    context = build_demo_context()
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
    context.identity_service.create_identity(identity, mutable, Role.CENTRAL)

    inputs = [
        "5",
        "a",
        "did-1",
        "2026-01-01",
        "2026-03-31",
        "5",
        "b",
        "did-1",
        "driving",
        "5",
        "c",
        "did-1",
        "London",
        "5",
        "z",
        "did-1",
        "0",
    ]
    outputs: list[str] = []

    def input_fn(_: str) -> str:
        if not inputs:
            raise AssertionError("No more inputs available")
        return inputs.pop(0)

    run_interactive_menu(context, input_fn=input_fn, output=outputs.append)

    assert sum(line.startswith("Eligible:") for line in outputs) == 3
    assert "Unknown verification type." in outputs

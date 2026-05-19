from digital_id.cli import run_interactive_menu
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

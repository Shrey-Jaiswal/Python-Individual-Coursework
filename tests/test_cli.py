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

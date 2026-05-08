from pathlib import Path

from digital_id.demo import build_demo_context, run_scripted_demo


def test_scripted_demo_outputs_and_audit(tmp_path: Path) -> None:
    context = build_demo_context()
    audit_path = tmp_path / "audit.json"

    lines = run_scripted_demo(context, audit_path=audit_path)

    assert any(line.startswith("  01. Create identity") for line in lines)
    assert any(line.startswith("  03. Duplicate identity") for line in lines)
    assert any(line.startswith("  04. Unauthorized revoke") for line in lines)
    assert any(line.startswith("  06. Tax verification (suspended)") for line in lines)
    assert "Audit:" in lines
    assert "  Entries recorded: 10" in lines
    assert audit_path.exists()
    assert len(context.audit_log.list_all()) == 10

from pathlib import Path

from digital_id.demo import build_demo_context, run_scripted_demo


def test_scripted_demo_outputs_and_audit(tmp_path: Path) -> None:
    context = build_demo_context()
    audit_path = tmp_path / "audit.json"

    lines = run_scripted_demo(context, audit_path=audit_path)

    assert "01. Create identity: PASS" in lines
    assert "03. Duplicate identity: REJECTED (expected)" in lines
    assert "04. Unauthorized revoke: REJECTED (expected)" in lines
    assert "06. Tax verification (suspended): INELIGIBLE (expected)" in lines
    assert "Audit entries recorded: 10" in lines
    assert audit_path.exists()
    assert len(context.audit_log.list_all()) == 10

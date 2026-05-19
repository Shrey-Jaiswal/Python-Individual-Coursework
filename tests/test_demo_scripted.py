from pathlib import Path

from digital_id.demo import build_demo_context, run_scripted_demo


def test_scripted_demo_outputs_and_audit(tmp_path: Path) -> None:
    context = build_demo_context()
    audit_path = tmp_path / "audit.json"

    lines = run_scripted_demo(context, audit_path=audit_path)

    assert "Create identity: OK" in lines
    assert "Duplicate identity: FAIL" in lines
    assert "Unauthorized revoke: FAIL" in lines
    assert "Tax verification while suspended: FAIL" in lines
    assert "Audit entries recorded: 10" in lines
    assert audit_path.exists()
    assert len(context.audit_log.list_all()) == 10

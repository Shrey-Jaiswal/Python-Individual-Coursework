from pathlib import Path

from digital_id.demo import build_demo_context, run_scripted_demo


def test_scripted_demo_outputs_and_audit(tmp_path: Path) -> None:
    context = build_demo_context()
    audit_path = tmp_path / "audit.json"

    lines = run_scripted_demo(context, audit_path=audit_path)

    assert any(line.startswith("01 Create identity") for line in lines)
    assert any(line.startswith("02 Repeat active status") for line in lines)
    assert any(line.startswith("05 Duplicate identity") for line in lines)
    assert any(line.startswith("06 Unauthorized revoke") for line in lines)
    assert any(line.startswith("07 Unauthorized verification") for line in lines)
    assert any(line.startswith("09 Tax verification (suspended)") for line in lines)
    assert any(line.startswith("11 Tax verification (history)") for line in lines)
    assert any(line.startswith("13 Add restriction") for line in lines)
    assert any(line.startswith("21 Missing identity lookup") for line in lines)
    assert any(line.startswith("24 Reactivate revoked identity") for line in lines)
    assert "Audit entries: 23" in lines
    assert audit_path.exists()
    assert len(context.audit_log.list_all()) == 23

import json
from datetime import datetime
from pathlib import Path

import pytest

from digital_id.domain import AuditEntry
from digital_id.persistence import PersistenceError
from digital_id.services import AuditLog, build_audit_entry


def test_audit_log_records_entries() -> None:
    log = AuditLog()
    entry = build_audit_entry("create", "central", "did-1", {"field": "value"})

    log.record(entry)

    entries = log.list_all()
    assert entries == [entry]


def test_audit_log_exports_json(tmp_path: Path) -> None:
    log = AuditLog()
    entry = AuditEntry(
        action="update",
        actor="central",
        target_id="did-2",
        timestamp=datetime(2026, 5, 19, 10, 0, 0),
        details={"field": "value"},
    )
    log.record(entry)

    path = tmp_path / "audit.json"
    log.export_json(path)

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["action"] == "update"
    assert data[0]["timestamp"] == "2026-05-19T10:00:00"


def test_audit_log_persists_each_record(tmp_path: Path) -> None:
    path = tmp_path / "audit.json"
    log = AuditLog(path)

    log.record(build_audit_entry("create", "central", "did-1", {"outcome": "success"}))

    reloaded = AuditLog(path)
    [entry] = reloaded.list_all()
    assert entry.action == "create"
    assert entry.details == {"outcome": "success"}


def test_audit_log_rejects_invalid_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "audit.json"
    path.write_text('{"not": "a-list"}', encoding="utf-8")

    with pytest.raises(PersistenceError, match="root must be a list"):
        AuditLog(path)

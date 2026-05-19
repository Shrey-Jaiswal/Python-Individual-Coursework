"""Audit logging utilities."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from digital_id.domain import AuditEntry
from digital_id.persistence.errors import PersistenceError


class AuditLog:
    """In-memory audit log with optional JSON export."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, entry: AuditEntry) -> None:
        self._entries.append(entry)

    def list_all(self) -> list[AuditEntry]:
        return list(self._entries)

    def export_json(self, path: Path) -> None:
        data = [self._to_dict(entry) for entry in self._entries]
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self._to_json(data), encoding="utf-8")
        except OSError as exc:
            raise PersistenceError("Unable to write audit log.") from exc

    def _to_dict(self, entry: AuditEntry) -> dict[str, str | dict[str, str]]:
        data = asdict(entry)
        data["timestamp"] = entry.timestamp.isoformat()
        return data

    def _to_json(self, payload: Iterable[dict[str, str | dict[str, str]]]) -> str:
        import json

        return json.dumps(list(payload), indent=2, sort_keys=True)


def build_audit_entry(
    action: str,
    actor: str,
    target_id: str,
    details: dict[str, str],
) -> AuditEntry:
    return AuditEntry(
        action=action,
        actor=actor,
        target_id=target_id,
        timestamp=datetime.utcnow(),
        details=details,
    )

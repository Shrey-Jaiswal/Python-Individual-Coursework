"""Audit logging utilities."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from digital_id.domain import AuditEntry
from digital_id.persistence.errors import PersistenceError


class AuditLog:
    """In-memory audit log with optional JSON export."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path
        self._entries: list[AuditEntry] = self._load(path) if path else []

    def record(self, entry: AuditEntry) -> None:
        self._entries.append(entry)
        if self._path is not None:
            self.export_json(self._path)

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
        return json.dumps(list(payload), indent=2, sort_keys=True)

    def _load(self, path: Path) -> list[AuditEntry]:
        if not path.exists():
            return []
        try:
            payload: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PersistenceError("Unable to read audit log.") from exc
        if not isinstance(payload, list):
            raise PersistenceError("Invalid audit log format: root must be a list")
        return [self._entry_from_dict(item) for item in payload]

    def _entry_from_dict(self, value: object) -> AuditEntry:
        if not isinstance(value, dict):
            raise PersistenceError("Invalid audit log entry: entry must be an object")
        details = value.get("details", {})
        if not isinstance(details, dict) or not all(
            isinstance(key, str) and isinstance(item, str) for key, item in details.items()
        ):
            raise PersistenceError("Invalid audit log entry: details must contain text values")
        try:
            action = self._require_str(value, "action")
            actor = self._require_str(value, "actor")
            target_id = self._require_str(value, "target_id")
            timestamp = datetime.fromisoformat(self._require_str(value, "timestamp"))
        except ValueError as exc:
            raise PersistenceError("Invalid audit log entry timestamp.") from exc
        return AuditEntry(
            action=action,
            actor=actor,
            target_id=target_id,
            timestamp=timestamp,
            details=dict(details),
        )

    def _require_str(self, data: dict[object, object], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise PersistenceError(f"Invalid audit log entry: {key} must be text")
        return value


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
        timestamp=datetime.now(UTC),
        details=details,
    )

"""JSON persistence for Digital IDs."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from digital_id.domain import (
    DigitalId,
    IdentityAttributes,
    MutableAttributes,
    Restriction,
    Status,
    StatusHistoryEntry,
)
from digital_id.domain.errors import InvalidRestrictionError
from digital_id.persistence.errors import PersistenceError, SchemaVersionError

_SCHEMA_VERSION = 1


class JsonStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> list[DigitalId]:
        if not self._path.exists():
            return []
        try:
            data: object = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PersistenceError("Unable to read JSON store.") from exc
        data_dict = self._ensure_dict(data, "root")

        version = data_dict.get("schema_version")
        if version != _SCHEMA_VERSION:
            raise SchemaVersionError(f"Unsupported schema version: {version}")
        items = self._ensure_list(data_dict.get("identities", []), "identities")
        return [self._digital_id_from_dict(self._ensure_dict(item, "identity")) for item in items]

    def save(self, identities: Iterable[DigitalId]) -> None:
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "identities": [self._digital_id_to_dict(identity) for identity in identities],
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        except OSError as exc:
            raise PersistenceError("Unable to write JSON store.") from exc

    def _digital_id_to_dict(self, identity: DigitalId) -> dict[str, object]:
        return {
            "identity": asdict(identity.identity),
            "mutable": asdict(identity.mutable),
            "status": identity.status.value,
            "restrictions": [self._restriction_to_dict(r) for r in identity.restrictions],
            "status_history": [self._history_to_dict(h) for h in identity.status_history],
        }

    def _digital_id_from_dict(self, data: dict[str, object]) -> DigitalId:
        identity_data = self._ensure_dict(data.get("identity", {}), "identity")
        mutable_data = self._ensure_dict(data.get("mutable", {}), "mutable")
        identity = IdentityAttributes(
            digital_id=str(identity_data.get("digital_id", "")),
            national_id=str(identity_data.get("national_id", "")),
            date_of_birth=str(identity_data.get("date_of_birth", "")),
        )
        mutable = MutableAttributes(
            name=str(mutable_data.get("name", "")),
            address=str(mutable_data.get("address", "")),
            email=str(mutable_data.get("email", "")),
            phone=str(mutable_data.get("phone", "")),
        )
        status_value = str(data.get("status", Status.ACTIVE.value))
        try:
            status = Status(status_value)
        except ValueError as exc:
            raise PersistenceError("Invalid status value in JSON store.") from exc
        restrictions_items = self._ensure_list(data.get("restrictions", []), "restrictions")
        history_items = self._ensure_list(data.get("status_history", []), "status_history")
        restrictions = [
            self._restriction_from_dict(self._ensure_dict(item, "restriction"))
            for item in restrictions_items
        ]
        history = [
            self._history_from_dict(self._ensure_dict(item, "history"))
            for item in history_items
        ]
        return DigitalId(
            identity=identity,
            mutable=mutable,
            status=status,
            restrictions=restrictions,
            status_history=history,
        )

    def _restriction_to_dict(self, restriction: Restriction) -> dict[str, object]:
        return {
            "name": restriction.name,
            "start": restriction.start.isoformat() if restriction.start else None,
            "end": restriction.end.isoformat() if restriction.end else None,
        }

    def _restriction_from_dict(self, data: dict[str, object]) -> Restriction:
        start = self._parse_date(data.get("start"))
        end = self._parse_date(data.get("end"))
        restriction = Restriction(name=str(data.get("name", "")), start=start, end=end)
        try:
            restriction.validate()
        except InvalidRestrictionError as exc:
            raise PersistenceError("Invalid restriction in JSON store.") from exc
        return restriction

    def _history_to_dict(self, entry: StatusHistoryEntry) -> dict[str, object]:
        return {
            "from_status": entry.from_status.value,
            "to_status": entry.to_status.value,
            "changed_at": entry.changed_at.isoformat(),
            "reason": entry.reason,
        }

    def _history_from_dict(self, data: dict[str, object]) -> StatusHistoryEntry:
        try:
            from_status = Status(str(data.get("from_status", Status.ACTIVE.value)))
            to_status = Status(str(data.get("to_status", Status.ACTIVE.value)))
        except ValueError as exc:
            raise PersistenceError("Invalid status history value in JSON store.") from exc
        changed_at = self._parse_datetime(data.get("changed_at"))
        return StatusHistoryEntry(
            from_status=from_status,
            to_status=to_status,
            changed_at=changed_at,
            reason=str(data.get("reason", "")),
        )

    def _parse_date(self, value: object) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise PersistenceError("Invalid date value in JSON store.") from exc

    def _parse_datetime(self, value: object) -> datetime:
        if not value:
            return datetime.utcnow()
        try:
            return datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise PersistenceError("Invalid datetime value in JSON store.") from exc

    def _ensure_dict(self, value: object, label: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise PersistenceError(f"Invalid JSON store format: {label} must be an object")
        if not all(isinstance(key, str) for key in value):
            raise PersistenceError(f"Invalid JSON store format: {label} keys must be strings")
        return dict(value)

    def _ensure_list(self, value: object, label: str) -> list[object]:
        if not isinstance(value, list):
            raise PersistenceError(f"Invalid JSON store format: {label} must be a list")
        return list(value)

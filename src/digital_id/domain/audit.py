"""Audit log entry model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuditEntry:
    action: str
    actor: str
    target_id: str
    timestamp: datetime
    details: dict[str, str]

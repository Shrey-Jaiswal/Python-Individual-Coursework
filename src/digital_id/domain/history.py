"""Status change history records for Digital IDs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from digital_id.domain.status import Status


@dataclass(frozen=True)
class StatusHistoryEntry:
    from_status: Status
    to_status: Status
    changed_at: datetime
    reason: str

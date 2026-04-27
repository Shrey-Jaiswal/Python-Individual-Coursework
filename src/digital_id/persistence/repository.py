"""Repository interface for Digital IDs."""

from __future__ import annotations

from typing import Protocol

from digital_id.domain import DigitalId


class DigitalIdRepository(Protocol):
    def add(self, digital_id: DigitalId) -> None:
        ...

    def get_by_id(self, digital_id: str) -> DigitalId:
        ...

    def get_by_national_id(self, national_id: str) -> DigitalId:
        ...

    def update(self, digital_id: DigitalId) -> None:
        ...

    def remove(self, digital_id: str) -> None:
        ...

    def list_all(self) -> list[DigitalId]:
        ...

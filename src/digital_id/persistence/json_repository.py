"""Repository implementation backed by the JSON store."""

from __future__ import annotations

from pathlib import Path

from digital_id.domain import DigitalId
from digital_id.persistence.in_memory import InMemoryRepository
from digital_id.persistence.json_store import JsonStore
from digital_id.persistence.repository import DigitalIdRepository


class JsonBackedRepository(DigitalIdRepository):
    """Repository adapter that persists each mutation to a JSON file."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store
        self._inner = InMemoryRepository()
        for identity in store.load():
            self._inner.add(identity)

    @classmethod
    def from_path(cls, path: Path) -> JsonBackedRepository:
        return cls(JsonStore(path))

    def add(self, digital_id: DigitalId) -> None:
        self._inner.add(digital_id)
        self._persist()

    def get_by_id(self, digital_id: str) -> DigitalId:
        return self._inner.get_by_id(digital_id)

    def get_by_national_id(self, national_id: str) -> DigitalId:
        return self._inner.get_by_national_id(national_id)

    def update(self, digital_id: DigitalId) -> None:
        self._inner.update(digital_id)
        self._persist()

    def remove(self, digital_id: str) -> None:
        self._inner.remove(digital_id)
        self._persist()

    def list_all(self) -> list[DigitalId]:
        return self._inner.list_all()

    def _persist(self) -> None:
        self._store.save(self._inner.list_all())

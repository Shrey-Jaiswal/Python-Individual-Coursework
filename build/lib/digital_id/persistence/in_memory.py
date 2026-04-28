"""In-memory repository implementation."""

from __future__ import annotations

from digital_id.domain import DigitalId
from digital_id.persistence.errors import DuplicateIdentityError, NotFoundError
from digital_id.persistence.repository import DigitalIdRepository


class InMemoryRepository(DigitalIdRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, DigitalId] = {}
        self._by_national_id: dict[str, DigitalId] = {}

    def add(self, digital_id: DigitalId) -> None:
        identity = digital_id.identity
        if identity.digital_id in self._by_id or identity.national_id in self._by_national_id:
            raise DuplicateIdentityError("Identity already exists.")
        self._by_id[identity.digital_id] = digital_id
        self._by_national_id[identity.national_id] = digital_id

    def get_by_id(self, digital_id: str) -> DigitalId:
        identity = self._by_id.get(digital_id)
        if identity is None:
            raise NotFoundError(f"Digital ID '{digital_id}' not found.")
        return identity

    def get_by_national_id(self, national_id: str) -> DigitalId:
        identity = self._by_national_id.get(national_id)
        if identity is None:
            raise NotFoundError(f"National ID '{national_id}' not found.")
        return identity

    def update(self, digital_id: DigitalId) -> None:
        identity = digital_id.identity
        if identity.digital_id not in self._by_id:
            raise NotFoundError(f"Digital ID '{identity.digital_id}' not found.")
        self._by_id[identity.digital_id] = digital_id
        self._by_national_id[identity.national_id] = digital_id

    def remove(self, digital_id: str) -> None:
        identity = self._by_id.pop(digital_id, None)
        if identity is None:
            raise NotFoundError(f"Digital ID '{digital_id}' not found.")
        self._by_national_id.pop(identity.identity.national_id, None)

    def list_all(self) -> list[DigitalId]:
        return [self._by_id[key] for key in sorted(self._by_id)]

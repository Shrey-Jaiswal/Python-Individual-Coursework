"""In-memory repository implementation."""

from __future__ import annotations

from copy import deepcopy

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
        stored = deepcopy(digital_id)
        self._by_id[identity.digital_id] = stored
        self._by_national_id[identity.national_id] = stored

    def get_by_id(self, digital_id: str) -> DigitalId:
        identity = self._by_id.get(digital_id)
        if identity is None:
            raise NotFoundError(f"Digital ID '{digital_id}' not found.")
        return deepcopy(identity)

    def get_by_national_id(self, national_id: str) -> DigitalId:
        identity = self._by_national_id.get(national_id)
        if identity is None:
            raise NotFoundError(f"National ID '{national_id}' not found.")
        return deepcopy(identity)

    def update(self, digital_id: DigitalId) -> None:
        identity = digital_id.identity
        current = self._by_id.get(identity.digital_id)
        if current is None:
            raise NotFoundError(f"Digital ID '{identity.digital_id}' not found.")
        if current.identity.national_id != identity.national_id:
            raise DuplicateIdentityError("National ID cannot be changed for an existing identity.")
        stored = deepcopy(digital_id)
        self._by_id[identity.digital_id] = stored
        self._by_national_id[identity.national_id] = stored

    def remove(self, digital_id: str) -> None:
        identity = self._by_id.pop(digital_id, None)
        if identity is None:
            raise NotFoundError(f"Digital ID '{digital_id}' not found.")
        self._by_national_id.pop(identity.identity.national_id, None)

    def list_all(self) -> list[DigitalId]:
        return [deepcopy(self._by_id[key]) for key in sorted(self._by_id)]

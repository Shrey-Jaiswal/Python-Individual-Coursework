"""Persistence adapters and repositories."""

from digital_id.persistence.errors import (
	DuplicateIdentityError,
	NotFoundError,
	PersistenceError,
	SchemaVersionError,
)
from digital_id.persistence.in_memory import InMemoryRepository
from digital_id.persistence.json_repository import JsonBackedRepository
from digital_id.persistence.json_store import JsonStore
from digital_id.persistence.repository import DigitalIdRepository

__all__ = [
	"DuplicateIdentityError",
	"NotFoundError",
	"PersistenceError",
	"SchemaVersionError",
	"InMemoryRepository",
	"JsonBackedRepository",
	"JsonStore",
	"DigitalIdRepository",
]

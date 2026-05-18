"""Domain models and rules."""

from digital_id.domain.digital_id import DigitalId, IdentityAttributes, MutableAttributes
from digital_id.domain.errors import (
	DomainError,
	ImmutableAttributeError,
	InvalidRestrictionError,
	InvalidStatusTransition,
)
from digital_id.domain.history import StatusHistoryEntry
from digital_id.domain.restrictions import Restriction
from digital_id.domain.status import Status

__all__ = [
	"DigitalId",
	"IdentityAttributes",
	"MutableAttributes",
	"DomainError",
	"ImmutableAttributeError",
	"InvalidRestrictionError",
	"InvalidStatusTransition",
	"StatusHistoryEntry",
	"Restriction",
	"Status",
]

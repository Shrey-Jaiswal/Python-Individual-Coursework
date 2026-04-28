"""Domain-specific errors for Digital ID rules."""


class DomainError(ValueError):
    """Base class for domain rule violations."""


class ImmutableAttributeError(DomainError):
    """Raised when attempting to change an immutable field."""


class InvalidStatusTransition(DomainError):
    """Raised when a status transition is not allowed."""


class InvalidRestrictionError(DomainError):
    """Raised when a restriction definition is invalid."""

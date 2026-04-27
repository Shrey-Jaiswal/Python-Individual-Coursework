"""Persistence and repository errors."""


class PersistenceError(RuntimeError):
    """Base class for persistence failures."""


class NotFoundError(PersistenceError):
    """Raised when an identity cannot be found."""


class DuplicateIdentityError(PersistenceError):
    """Raised when an identity conflicts with an existing record."""


class SchemaVersionError(PersistenceError):
    """Raised when a persistence schema version is unsupported."""

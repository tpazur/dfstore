class DFStoreError(Exception):
    """Base exception for all dfstore errors."""


class DFNotFoundError(DFStoreError):
    """Raised when a DataFrame name is not found in the store."""


class DFNameConflictError(DFStoreError):
    """Reserved for future concurrent-write conflict detection."""

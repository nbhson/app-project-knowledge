"""Exception hierarchy for PKH."""

from __future__ import annotations


class PKHError(Exception):
    """Base exception for all PKH errors."""

    def __init__(self, message: str = "", *, code: str = "", details: dict | None = None):
        super().__init__(message)
        self.code = code or self.__class__.__name__
        self.details = details or {}


class ValidationError(PKHError):
    """Model validation failures."""

    pass


class ConfigurationError(PKHError):
    """Config loading / validation errors."""

    pass


class SourceError(PKHError):
    """Connector failures."""

    pass


class StorageError(PKHError):
    """DB / vector / graph storage failures."""

    pass


class ExtractionError(PKHError):
    """Extraction pipeline failures."""

    pass


class RetrievalError(PKHError):
    """Query / retrieval failures."""

    pass


class AdapterError(PKHError):
    """LLM adapter failures."""

    pass


class GovernanceError(PKHError):
    """RBAC / audit violations."""

    pass


class LifecycleError(PKHError):
    """Invalid lifecycle transitions."""

    def __init__(
        self,
        message: str = "",
        *,
        from_state: str | None = None,
        to_state: str | None = None,
    ):
        super().__init__(
            message,
            code="LIFECYCLE_INVALID_TRANSITION",
            details={"from_state": from_state, "to_state": to_state},
        )
        self.from_state = from_state
        self.to_state = to_state

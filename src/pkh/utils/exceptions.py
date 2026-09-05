"""Exception hierarchy for PKH."""

from __future__ import annotations


class PKHError(Exception):
    """Base exception for all PKH errors."""

    pass


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

    pass

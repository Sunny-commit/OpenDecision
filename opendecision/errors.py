"""OpenDecision exception hierarchy."""

class OpenDecisionError(Exception):
    """Base error for OpenDecision."""

class ContractValidationError(OpenDecisionError):
    """Raised when decision input or provider output violates its contract."""

class ProviderError(OpenDecisionError):
    """Raised when a decision provider cannot return a valid answer."""

class ProvidersExhaustedError(ProviderError):
    """Raised when every provider in a fallback chain fails."""

class ReviewLoopError(OpenDecisionError):
    """Raised when an action exceeds the configured review-attempt limit."""

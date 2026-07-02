class AppError(Exception):
    """Base class for expected application errors."""


class ConfigurationError(AppError):
    """Raised when runtime configuration is invalid or unsupported."""


class DocumentConversionError(AppError):
    """Raised when a document cannot be converted to markdown."""


class LLMError(AppError):
    """Raised when an LLM provider call fails or returns unusable data."""


class ValidationError(AppError):
    """Raised when user input fails application-level validation."""


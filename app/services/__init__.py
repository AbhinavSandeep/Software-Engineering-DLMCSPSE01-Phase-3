"""Service layer: business rules, independent of HTTP and templates."""


class ValidationError(ValueError):
    """Raised when user or file input breaks a business rule."""

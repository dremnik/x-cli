"""Error types for xcli."""


class XcliError(Exception):
    """Base error for xcli failures."""


class UsageError(XcliError):
    """Raised when command arguments are invalid."""


class AuthError(XcliError):
    """Raised for auth/token issues."""


class ApiError(XcliError):
    """Raised for API failures."""

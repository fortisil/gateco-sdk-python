"""Error hierarchy for the Gateco SDK.

Maps backend error codes and HTTP status codes to typed exceptions.
"""

from __future__ import annotations


class GatecoError(Exception):
    """Base exception for all Gateco SDK errors.

    Attributes:
        code: Machine-readable error code from the API (e.g. ``RESOURCE_NOT_FOUND``).
        message: Human-readable description of the error.
        status_code: HTTP status code returned by the API.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        *,
        code: str = "UNKNOWN_ERROR",
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(code={self.code!r}, "
            f"message={self.message!r}, status_code={self.status_code})"
        )


class AuthenticationError(GatecoError):
    """Raised when the API returns 401 (invalid / expired credentials)."""

    def __init__(
        self,
        message: str = "Authentication failed",
        *,
        code: str = "AUTH_INVALID_CREDENTIALS",
    ) -> None:
        super().__init__(message, code=code, status_code=401)


class AuthorizationError(GatecoError):
    """Raised when the API returns 403 (insufficient permissions)."""

    def __init__(
        self,
        message: str = "Permission denied",
        *,
        code: str = "AUTH_PERMISSION_DENIED",
    ) -> None:
        super().__init__(message, code=code, status_code=403)


class NotFoundError(GatecoError):
    """Raised when the API returns 404."""

    def __init__(
        self,
        message: str = "Resource not found",
        *,
        code: str = "RESOURCE_NOT_FOUND",
    ) -> None:
        super().__init__(message, code=code, status_code=404)


class ConflictError(GatecoError):
    """Raised when the API returns 409 (e.g. duplicate resource)."""

    def __init__(
        self,
        message: str = "Conflict",
        *,
        code: str = "CONFLICT",
    ) -> None:
        super().__init__(message, code=code, status_code=409)


class EntitlementError(GatecoError):
    """Raised when the API returns 403 with ENTITLEMENT_REQUIRED.

    Attributes:
        upgrade_to: The plan tier that grants the required entitlement.
    """

    def __init__(
        self,
        message: str = "Entitlement required",
        *,
        code: str = "ENTITLEMENT_REQUIRED",
        upgrade_to: str | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=403)
        self.upgrade_to = upgrade_to


class RateLimitError(GatecoError):
    """Raised when the API returns 429.

    Attributes:
        retry_after: Seconds to wait before retrying (from ``Retry-After`` header).
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        code: str = "RATE_LIMIT_EXCEEDED",
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, code=code, status_code=429)
        self.retry_after = retry_after


class ValidationError(GatecoError):
    """Raised when the API returns 422 (request validation failure)."""

    def __init__(
        self,
        message: str = "Validation error",
        *,
        code: str = "VALIDATION_ERROR",
    ) -> None:
        super().__init__(message, code=code, status_code=422)


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------

_STATUS_TO_ERROR: dict[int, type[GatecoError]] = {
    401: AuthenticationError,
    404: NotFoundError,
    409: ConflictError,
    422: ValidationError,
    429: RateLimitError,
}

_CODE_TO_ERROR: dict[str, type[GatecoError]] = {
    "AUTH_INVALID_CREDENTIALS": AuthenticationError,
    "AUTH_PERMISSION_DENIED": AuthorizationError,
    "ENTITLEMENT_REQUIRED": EntitlementError,
    "RESOURCE_NOT_FOUND": NotFoundError,
    "CONFLICT": ConflictError,
    "VALIDATION_ERROR": ValidationError,
    "RATE_LIMIT_EXCEEDED": RateLimitError,
    "INTERNAL_ERROR": GatecoError,
}


def error_from_response(
    status_code: int,
    body: dict | None,
    *,
    retry_after: float | None = None,
) -> GatecoError:
    """Build the most specific ``GatecoError`` subclass from an API response.

    Args:
        status_code: HTTP status code.
        body: Parsed JSON body (may be ``None``).
        retry_after: Value of the ``Retry-After`` header, if present.

    Returns:
        An instance of the appropriate ``GatecoError`` subclass.
    """
    code = "UNKNOWN_ERROR"
    message = "An unexpected error occurred"
    upgrade_to: str | None = None

    if body and isinstance(body.get("error"), dict):
        err = body["error"]
        code = err.get("code", code)
        message = err.get("message", message)
        upgrade_to = err.get("upgrade_to")

    # Prefer code-based lookup, fall back to status-based lookup.
    cls = _CODE_TO_ERROR.get(code) or _STATUS_TO_ERROR.get(status_code, GatecoError)

    if cls is EntitlementError:
        return EntitlementError(message, code=code, upgrade_to=upgrade_to)
    if cls is RateLimitError:
        return RateLimitError(message, code=code, retry_after=retry_after)

    return cls(message, code=code) if cls is not GatecoError else GatecoError(
        message, code=code, status_code=status_code
    )

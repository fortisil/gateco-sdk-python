"""MCP tool handler functions — standalone async functions testable without MCP.

Each handler builds an ``AsyncGatecoClient``, calls the SDK, formats the
response, and returns a plain string.  Errors are caught and returned as
descriptive error strings (the MCP server layer marks them ``is_error=True``).
"""

from __future__ import annotations

from typing import Any

from gateco_sdk.errors import (
    AuthenticationError,
    AuthorizationError,
    EntitlementError,
    GatecoError,
    LlmCreditExhaustedError,
    LlmKeyNotConfiguredError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from gateco_sdk.mcp.formatters import (
    format_answer,
    format_connectors,
    format_principal,
    format_principals,
    format_retrieval,
    format_simulation,
)


def _handle_error(exc: GatecoError) -> str:
    """Map a ``GatecoError`` to a human-readable error string."""
    if isinstance(exc, AuthenticationError):
        return "Authentication failed. Run `gateco login` or set GATECO_API_KEY."
    if isinstance(exc, EntitlementError):
        upgrade = f" Requires {exc.upgrade_to} plan." if exc.upgrade_to else ""
        return f"Entitlement required.{upgrade} {exc.message}"
    if isinstance(exc, NotFoundError):
        return f"Not found: {exc.message}"
    if isinstance(exc, AuthorizationError):
        return f"Permission denied: {exc.message}"
    if isinstance(exc, ValidationError):
        return f"Invalid request: {exc.message}"
    if isinstance(exc, RateLimitError):
        retry = f" Retry after {exc.retry_after}s." if exc.retry_after else ""
        return f"Rate limited.{retry}"
    if isinstance(exc, LlmCreditExhaustedError):
        return (
            "Answer synthesis unavailable: your organization's 100 free synthesis calls "
            "are exhausted. Add your OpenAI API key in Organization Settings "
            "(https://app.gateco.ai/organization) to continue."
        )
    if isinstance(exc, LlmKeyNotConfiguredError):
        return (
            "Answer synthesis unavailable: this organization is on the free plan and "
            "has no OpenAI API key configured. Add one in Organization Settings "
            "(https://app.gateco.ai/organization) to enable answer synthesis."
        )
    return f"Gateco error: {exc.message}"


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def handle_retrieve(
    connector_id: str,
    query: str,
    principal_id: str | None = None,
    top_k: int = 10,
    search_mode: str = "vector",
    alpha: float | None = None,
    pattern_type: str | None = None,
    case_sensitive: bool | None = None,
    email: str | None = None,
) -> str:
    """Permission-aware retrieval with configurable search mode.

    Either ``principal_id`` or ``email`` must be supplied.  When only
    ``email`` is provided the principal is resolved before executing the
    retrieval.
    """
    from gateco_sdk.cli import _get_client

    if not principal_id and not email:
        raise _ToolError("Either 'principal_id' or 'email' must be provided.")

    try:
        async with _get_client() as client:
            resolved_id = principal_id
            if not resolved_id:
                principal = await client.principals.resolve(email=email)
                resolved_id = principal.id

            kwargs: dict[str, Any] = {
                "query": query,
                "principal_id": resolved_id,
                "connector_id": connector_id,
                "top_k": top_k,
                "search_mode": search_mode,
            }
            if alpha is not None:
                kwargs["alpha"] = alpha
            if pattern_type is not None:
                kwargs["pattern_type"] = pattern_type
            if case_sensitive is not None:
                kwargs["case_sensitive"] = case_sensitive

            result = await client.retrievals.execute(**kwargs)
        return format_retrieval(result)
    except GatecoError as exc:
        raise _ToolError(_handle_error(exc)) from exc


async def handle_ask(
    connector_id: str,
    query: str,
    principal_id: str | None = None,
    top_k: int = 15,
    search_mode: str = "vector",
    alpha: float | None = None,
    email: str | None = None,
) -> str:
    """Grounded answer synthesis (Growth+).

    Either ``principal_id`` or ``email`` must be supplied.  When only
    ``email`` is provided the principal is resolved before executing the
    answer synthesis.
    """
    from gateco_sdk.cli import _get_client

    if not principal_id and not email:
        raise _ToolError("Either 'principal_id' or 'email' must be provided.")

    try:
        async with _get_client() as client:
            resolved_id = principal_id
            if not resolved_id:
                principal = await client.principals.resolve(email=email)
                resolved_id = principal.id

            kwargs: dict[str, Any] = {
                "principal_id": resolved_id,
                "connector_id": connector_id,
                "top_k": top_k,
            }
            if search_mode != "grep":
                kwargs["search_mode"] = search_mode
            if alpha is not None:
                kwargs["alpha"] = alpha

            result = await client.answers.execute(query, **kwargs)
        output = format_answer(result)
        if result.cap_reached:
            output += (
                "\n\n> **Key rotation reminder:** your organization has reached its "
                "configured query cap. Rotate your OpenAI API key in "
                "Organization Settings (https://app.gateco.ai/organization) "
                "to reset the counter."
            )
        return output
    except GatecoError as exc:
        raise _ToolError(_handle_error(exc)) from exc


async def handle_check_access(
    principal_id: str,
    connector_id: str | None = None,
    resource_ids: list[str] | None = None,
) -> str:
    """Dry-run access simulation (Growth+)."""
    from gateco_sdk.cli import _get_client

    try:
        async with _get_client() as client:
            result = await client.simulator.run(
                principal_id,
                connector_id=connector_id,
                resource_ids=resource_ids,
            )
        return format_simulation(result)
    except GatecoError as exc:
        raise _ToolError(_handle_error(exc)) from exc


async def handle_list_connectors(
    page: int = 1,
    per_page: int = 20,
) -> str:
    """List connectors."""
    from gateco_sdk.cli import _get_client

    try:
        async with _get_client() as client:
            result = await client.connectors.list(page=page, per_page=per_page)
        return format_connectors(result)
    except GatecoError as exc:
        raise _ToolError(_handle_error(exc)) from exc


async def handle_list_principals(
    page: int = 1,
    per_page: int = 20,
) -> str:
    """List principals."""
    from gateco_sdk.cli import _get_client

    try:
        async with _get_client() as client:
            result = await client.principals.list(page=page, per_page=per_page)
        return format_principals(result)
    except GatecoError as exc:
        raise _ToolError(_handle_error(exc)) from exc


async def handle_resolve_principal(
    email: str | None,
    provider_subject: str | None,
    identity_provider_id: str | None,
) -> str:
    """Resolve a principal by email or provider subject ID."""
    from gateco_sdk.cli import _get_client

    if not email and not provider_subject:
        raise _ToolError(
            "At least one of 'email' or 'provider_subject' must be provided."
        )

    try:
        async with _get_client() as client:
            principal = await client.principals.resolve(
                email=email,
                provider_subject=provider_subject,
                identity_provider_id=identity_provider_id,
            )
        return format_principal(principal)
    except GatecoError as exc:
        raise _ToolError(_handle_error(exc)) from exc


# ---------------------------------------------------------------------------
# Error type for tool-level errors (distinct from SDK errors)
# ---------------------------------------------------------------------------


class _ToolError(Exception):
    """Raised by tool handlers to signal an error to the MCP layer."""

    pass

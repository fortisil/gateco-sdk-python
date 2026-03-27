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
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from gateco_sdk.mcp.formatters import (
    format_answer,
    format_connectors,
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
    return f"Gateco error: {exc.message}"


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def handle_retrieve(
    connector_id: str,
    query: str,
    principal_id: str,
    top_k: int = 10,
    search_mode: str = "vector",
    alpha: float | None = None,
    pattern_type: str | None = None,
    case_sensitive: bool | None = None,
) -> str:
    """Permission-aware retrieval with configurable search mode."""
    from gateco_sdk.cli import _get_client

    try:
        kwargs: dict[str, Any] = {
            "query": query,
            "principal_id": principal_id,
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

        async with _get_client() as client:
            result = await client.retrievals.execute(**kwargs)
        return format_retrieval(result)
    except GatecoError as exc:
        raise _ToolError(_handle_error(exc)) from exc


async def handle_ask(
    connector_id: str,
    query: str,
    principal_id: str,
    top_k: int = 15,
    search_mode: str = "vector",
    alpha: float | None = None,
) -> str:
    """Grounded answer synthesis (Pro+)."""
    from gateco_sdk.cli import _get_client

    try:
        kwargs: dict[str, Any] = {
            "principal_id": principal_id,
            "connector_id": connector_id,
            "top_k": top_k,
        }
        if search_mode != "grep":
            kwargs["search_mode"] = search_mode
        if alpha is not None:
            kwargs["alpha"] = alpha

        async with _get_client() as client:
            result = await client.answers.execute(
                query,
                **kwargs,
            )
        return format_answer(result)
    except GatecoError as exc:
        raise _ToolError(_handle_error(exc)) from exc


async def handle_check_access(
    principal_id: str,
    connector_id: str | None = None,
    resource_ids: list[str] | None = None,
) -> str:
    """Dry-run access simulation (Pro+)."""
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


# ---------------------------------------------------------------------------
# Error type for tool-level errors (distinct from SDK errors)
# ---------------------------------------------------------------------------


class _ToolError(Exception):
    """Raised by tool handlers to signal an error to the MCP layer."""

    pass

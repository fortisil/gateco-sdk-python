"""Gateco MCP Server — Model Context Protocol integration.

Requires the ``mcp`` optional dependency::

    pip install gateco[mcp]

Usage::

    # As a CLI subcommand
    gateco mcp serve

    # As a direct entry point (for MCP host configs)
    gateco-mcp

    # Programmatically
    from gateco_sdk.mcp import create_server, run_stdio
    server = create_server()
    run_stdio()
"""

from __future__ import annotations


def _check_mcp_installed() -> None:
    """Raise a clear error if the ``mcp`` package is not installed."""
    try:
        import mcp  # noqa: F401
    except ImportError:
        raise ImportError(
            "The 'mcp' package is required for the Gateco MCP server.\n"
            "Install it with: pip install gateco[mcp]"
        ) from None


def create_server() -> "mcp.server.fastmcp.FastMCP":  # type: ignore[name-defined]
    """Create and return a configured Gateco MCP server instance."""
    _check_mcp_installed()
    from gateco_sdk.mcp.server import create_server as _create

    return _create()


def run_stdio() -> None:
    """Blocking entry point — create server and run on stdio transport.

    This is the ``gateco-mcp`` console script entry point.
    """
    _check_mcp_installed()
    from gateco_sdk.mcp.server import create_server as _create

    server = _create()
    server.run(transport="stdio")

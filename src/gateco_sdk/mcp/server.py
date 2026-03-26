"""MCP Server definition — tool registration via FastMCP decorators."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from gateco_sdk.mcp.tools import (
    _ToolError,
    handle_ask,
    handle_check_access,
    handle_list_connectors,
    handle_list_principals,
    handle_retrieve,
)


def create_server() -> FastMCP:
    """Create a Gateco MCP server with all tools registered."""
    server = FastMCP("gateco")

    @server.tool()
    async def gateco_retrieve(
        connector_id: str,
        query: str,
        principal_id: str,
        top_k: int = 10,
    ) -> str:
        """Permission-aware vector retrieval through Gateco.

        Searches a connector (vector DB) for chunks matching the query,
        then applies policy filtering based on the principal's identity.
        Only allowed chunks are returned; denied content is never exposed.

        Args:
            connector_id: Connector (vector DB) to search.
            query: Natural language search query.
            principal_id: Identity performing the request.
            top_k: Max results (default: 10).
        """
        try:
            return await handle_retrieve(connector_id, query, principal_id, top_k)
        except _ToolError as exc:
            raise ValueError(str(exc)) from exc

    @server.tool()
    async def gateco_ask(
        connector_id: str,
        query: str,
        principal_id: str,
        top_k: int = 15,
    ) -> str:
        """Grounded answer synthesis through Gateco (Pro+ plan required).

        Retrieves policy-filtered chunks and synthesizes a natural language
        answer with citations. Denied chunks are never included in the
        LLM context.

        Args:
            connector_id: Connector to search.
            query: Natural language question.
            principal_id: Identity performing the request.
            top_k: Max context chunks (default: 15).
        """
        try:
            return await handle_ask(connector_id, query, principal_id, top_k)
        except _ToolError as exc:
            raise ValueError(str(exc)) from exc

    @server.tool()
    async def gateco_check_access(
        principal_id: str,
        connector_id: str | None = None,
        resource_ids: list[str] | None = None,
    ) -> str:
        """Dry-run access simulation through Gateco (Pro+ plan required).

        Evaluates what a principal can and cannot access without
        performing an actual retrieval. Useful for debugging policy
        configurations.

        Args:
            principal_id: Identity to simulate for.
            connector_id: Optional — scope to a specific connector.
            resource_ids: Optional — specific resource IDs to evaluate.
        """
        try:
            return await handle_check_access(
                principal_id,
                connector_id=connector_id,
                resource_ids=resource_ids,
            )
        except _ToolError as exc:
            raise ValueError(str(exc)) from exc

    @server.tool()
    async def gateco_list_connectors(
        page: int = 1,
        per_page: int = 20,
    ) -> str:
        """List configured connectors in Gateco.

        Returns connector names, types, policy readiness levels (L0-L4),
        status, and IDs.

        Args:
            page: Page number (default: 1).
            per_page: Items per page (default: 20).
        """
        try:
            return await handle_list_connectors(page, per_page)
        except _ToolError as exc:
            raise ValueError(str(exc)) from exc

    @server.tool()
    async def gateco_list_principals(
        page: int = 1,
        per_page: int = 20,
    ) -> str:
        """List identity principals known to Gateco.

        Returns principal names, emails, groups, roles, and IDs.

        Args:
            page: Page number (default: 1).
            per_page: Items per page (default: 20).
        """
        try:
            return await handle_list_principals(page, per_page)
        except _ToolError as exc:
            raise ValueError(str(exc)) from exc

    return server

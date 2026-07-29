"""MCP Server definition — tool registration via FastMCP decorators."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from gateco_sdk.mcp.tools import (
    _ToolError,
    handle_ask,
    handle_check_access,
    handle_list_connectors,
    handle_list_groups,
    handle_list_principals,
    handle_resolve_principal,
    handle_retrieve,
)


def create_server() -> FastMCP:
    """Create a Gateco MCP server with all tools registered."""
    server = FastMCP("gateco")

    @server.tool()
    async def gateco_retrieve(
        connector_id: str,
        query: str,
        principal_id: str | None = None,
        email: str | None = None,
        top_k: int = 10,
        search_mode: str = "vector",
        alpha: float | None = None,
        pattern_type: str | None = None,
        case_sensitive: bool | None = None,
    ) -> str:
        """Permission-aware retrieval through Gateco.

        Searches a connector (vector DB) for chunks matching the query,
        then applies policy filtering based on the principal's identity.
        Only allowed chunks are returned; denied content is never exposed.

        Supports four search modes:
        - vector: Semantic similarity (ANN) — default
        - keyword: Ranked full-text search (BM25/FTS)
        - hybrid: Combined vector + keyword with configurable alpha weight
        - grep: Deterministic exact-match (substring or regex)

        Args:
            connector_id: Connector (vector DB) to search.
            query: Search query text.
            principal_id: Identity performing the request (UUID). Mutually
                exclusive alternative to email.
            email: Email address of the principal. When provided and
                principal_id is absent, the principal is resolved first.
            top_k: Max results (default: 10).
            search_mode: Search mode (default: "vector").
            alpha: Hybrid weight 0.0-1.0 (1.0=all-vector, 0.0=all-keyword). Hybrid only.
            pattern_type: "substring" or "regex". Grep only.
            case_sensitive: Case-sensitive matching. Grep only.
        """
        try:
            return await handle_retrieve(
                connector_id, query, principal_id, top_k,
                search_mode=search_mode,
                alpha=alpha,
                pattern_type=pattern_type,
                case_sensitive=case_sensitive,
                email=email,
            )
        except _ToolError as exc:
            raise ValueError(str(exc)) from exc

    @server.tool()
    async def gateco_ask(
        connector_id: str,
        query: str,
        principal_id: str | None = None,
        email: str | None = None,
        top_k: int = 15,
        search_mode: str = "vector",
        alpha: float | None = None,
    ) -> str:
        """Grounded answer synthesis through Gateco (Growth+ plan required).

        Retrieves policy-filtered chunks and synthesizes a natural language
        answer with citations. Denied chunks are never included in the
        LLM context.

        Supports vector, keyword, and hybrid search modes (not grep).

        Args:
            connector_id: Connector to search.
            query: Natural language question.
            principal_id: Identity performing the request (UUID). Mutually
                exclusive alternative to email.
            email: Email address of the principal. When provided and
                principal_id is absent, the principal is resolved first.
            top_k: Max context chunks (default: 15).
            search_mode: Search mode — "vector", "keyword", or "hybrid" (not grep).
            alpha: Hybrid weight 0.0-1.0. Hybrid only.
        """
        try:
            return await handle_ask(
                connector_id, query, principal_id, top_k,
                search_mode=search_mode,
                alpha=alpha,
                email=email,
            )
        except _ToolError as exc:
            raise ValueError(str(exc)) from exc

    @server.tool()
    async def gateco_check_access(
        principal_id: str,
        connector_id: str | None = None,
        resource_ids: list[str] | None = None,
    ) -> str:
        """Dry-run access simulation through Gateco (Growth+ plan required).

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

    @server.tool()
    async def gateco_list_groups(
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
    ) -> str:
        """List IdP-synced groups known to Gateco.

        Returns group names, source identity providers, live member counts
        (active members only), and IDs.

        Args:
            page: Page number (default: 1).
            per_page: Items per page (default: 20).
            search: Optional case-insensitive substring filter on group name.
        """
        try:
            return await handle_list_groups(page, per_page, search)
        except _ToolError as exc:
            raise ValueError(str(exc)) from exc

    @server.tool()
    async def gateco_resolve_principal(
        email: str | None = None,
        provider_subject: str | None = None,
        identity_provider_id: str | None = None,
    ) -> str:
        """Resolve a principal by email or provider subject ID.

        Looks up a principal in Gateco's identity store using a human-readable
        identifier (email) or the provider-native subject ID (e.g. an Okta user
        ID, Google sub claim, or AWS external ID).  Returns principal details
        including groups, roles, and attributes.

        At least one of email or provider_subject must be provided.

        Args:
            email: Email address of the principal to resolve.
            provider_subject: Provider-native subject identifier.
            identity_provider_id: Optional UUID to scope the lookup to a single
                identity provider.
        """
        try:
            return await handle_resolve_principal(
                email, provider_subject, identity_provider_id
            )
        except _ToolError as exc:
            raise ValueError(str(exc)) from exc

    return server

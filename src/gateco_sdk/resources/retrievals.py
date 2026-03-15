"""Retrievals resource — execute, list, get."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk._pagination import AsyncPaginator, Page
from gateco_sdk.types.retrievals import SecuredRetrieval

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class RetrievalsResource:
    """Namespace for retrieval endpoints.

    Accessed as ``client.retrievals``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def execute(
        self,
        query_vector: list[float] | None = None,
        *,
        principal_id: str,
        connector_id: str,
        query: str | None = None,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
        include_unresolved: bool | None = None,
    ) -> SecuredRetrieval:
        """Execute a permission-gated retrieval.

        Args:
            query_vector: Optional embedding vector for similarity search.
            principal_id: Identity of the requesting principal.
            connector_id: Connector to search against.
            query: Optional text query (used when the backend embeds for you).
            top_k: Maximum number of results to return.
            filters: Optional filter dict for scoping results.
            include_unresolved: Whether to include unresolved results.
        """
        body: dict[str, Any] = {
            "principal_id": principal_id,
            "connector_id": connector_id,
        }
        if query_vector is not None:
            body["query_vector"] = query_vector
        if query is not None:
            body["query"] = query
        if top_k is not None:
            body["top_k"] = top_k
        if filters is not None:
            body["filters"] = filters
        if include_unresolved is not None:
            body["include_unresolved"] = include_unresolved

        data = await self._client._request(
            "POST", "/api/retrievals/execute", json=body
        )
        return SecuredRetrieval.model_validate(data)

    async def list(
        self,
        page: int = 1,
        per_page: int = 20,
        **filters: Any,
    ) -> Page[SecuredRetrieval]:
        """Fetch a single page of retrieval records."""
        params: dict[str, Any] = {"page": page, "per_page": per_page, **filters}
        raw = await self._client._request(
            "GET", "/api/retrievals", params=params
        )
        items_raw = raw.get("data", []) if raw else []
        meta = (raw or {}).get("meta", {}).get("pagination", {})
        items = [SecuredRetrieval.model_validate(r) for r in items_raw]
        return Page[SecuredRetrieval](
            items=items,
            page=meta.get("page", page),
            per_page=meta.get("per_page", per_page),
            total=meta.get("total", len(items)),
            total_pages=meta.get("total_pages", 1),
        )

    def list_all(
        self, per_page: int = 100, **filters: Any
    ) -> AsyncPaginator[SecuredRetrieval]:
        """Return an async iterator over all retrieval records."""

        async def _fetch(page: int, pp: int) -> dict[str, Any]:
            return await self._client._request(
                "GET",
                "/api/retrievals",
                params={"page": page, "per_page": pp, **filters},
            ) or {}

        return AsyncPaginator[SecuredRetrieval](
            _fetch, SecuredRetrieval, per_page=per_page
        )

    async def get(self, retrieval_id: str) -> SecuredRetrieval:
        """Get a single retrieval by ID."""
        data = await self._client._request(
            "GET", f"/api/retrievals/{retrieval_id}"
        )
        return SecuredRetrieval.model_validate(data)

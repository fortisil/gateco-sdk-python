"""Connectors resource — CRUD, test, bind, config, coverage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk._pagination import AsyncPaginator, Page
from gateco_sdk.types.connectors import (
    ApplySuggestionsResponse,
    BindingEntry,
    BindResult,
    ClassificationSuggestion,
    Connector,
    CoverageDetail,
    SuggestClassificationsResponse,
    TestConnectorResponse,
)

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class ConnectorsResource:
    """Namespace for connector endpoints.

    Accessed as ``client.connectors``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list(self, page: int = 1, per_page: int = 20) -> Page[Connector]:
        """Fetch a single page of connectors."""
        raw = await self._client._request(
            "GET",
            "/api/connectors",
            params={"page": page, "per_page": per_page},
        )
        items_raw = raw.get("data", []) if raw else []
        meta = (raw or {}).get("meta", {}).get("pagination", {})
        items = [Connector.model_validate(c) for c in items_raw]
        return Page[Connector](
            items=items,
            page=meta.get("page", page),
            per_page=meta.get("per_page", per_page),
            total=meta.get("total", len(items)),
            total_pages=meta.get("total_pages", 1),
        )

    def list_all(self, per_page: int = 100) -> AsyncPaginator[Connector]:
        """Return an async iterator that lazily paginates through all connectors."""

        async def _fetch(page: int, pp: int) -> dict[str, Any]:
            return await self._client._request(
                "GET", "/api/connectors", params={"page": page, "per_page": pp}
            ) or {}

        return AsyncPaginator[Connector](_fetch, Connector, per_page=per_page)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def get(self, connector_id: str) -> Connector:
        """Get a single connector by ID."""
        data = await self._client._request("GET", f"/api/connectors/{connector_id}")
        return Connector.model_validate(data)

    async def create(
        self,
        name: str,
        type: str,
        config: dict[str, Any] | None = None,
        *,
        metadata_resolution_mode: str | None = None,
    ) -> Connector:
        """Create a new connector."""
        body: dict[str, Any] = {"name": name, "type": type}
        if config is not None:
            body["config"] = config
        if metadata_resolution_mode is not None:
            body["metadata_resolution_mode"] = metadata_resolution_mode
        data = await self._client._request("POST", "/api/connectors", json=body)
        return Connector.model_validate(data)

    async def update(
        self,
        connector_id: str,
        *,
        name: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> Connector:
        """Update an existing connector."""
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if config is not None:
            body["config"] = config
        data = await self._client._request(
            "PATCH", f"/api/connectors/{connector_id}", json=body
        )
        return Connector.model_validate(data)

    async def delete(self, connector_id: str) -> None:
        """Delete a connector."""
        await self._client._request("DELETE", f"/api/connectors/{connector_id}")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def test(self, connector_id: str) -> TestConnectorResponse:
        """Test connectivity for a connector."""
        data = await self._client._request(
            "POST", f"/api/connectors/{connector_id}/test"
        )
        return TestConnectorResponse.model_validate(data)

    async def bind(
        self,
        connector_id: str,
        bindings: list[BindingEntry] | list[dict[str, Any]],
    ) -> BindResult:
        """Bind external resources to vector IDs."""
        entries = [
            b.model_dump() if isinstance(b, BindingEntry) else b for b in bindings
        ]
        data = await self._client._request(
            "POST",
            f"/api/connectors/{connector_id}/bind",
            json={"bindings": entries},
        )
        return BindResult.model_validate(data)

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    async def get_search_config(self, connector_id: str) -> dict[str, Any]:
        """Get the search configuration for a connector."""
        data = await self._client._request(
            "GET", f"/api/connectors/{connector_id}/search-config"
        )
        return data or {}

    async def update_search_config(
        self, connector_id: str, search_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Update the search configuration for a connector."""
        data = await self._client._request(
            "PATCH",
            f"/api/connectors/{connector_id}/search-config",
            json=search_config,
        )
        return data or {}

    async def get_ingestion_config(self, connector_id: str) -> dict[str, Any]:
        """Get the ingestion configuration for a connector."""
        data = await self._client._request(
            "GET", f"/api/connectors/{connector_id}/ingestion-config"
        )
        return data or {}

    async def update_ingestion_config(
        self, connector_id: str, ingestion_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Update the ingestion configuration for a connector."""
        data = await self._client._request(
            "PATCH",
            f"/api/connectors/{connector_id}/ingestion-config",
            json=ingestion_config,
        )
        return data or {}

    # ------------------------------------------------------------------
    # Coverage
    # ------------------------------------------------------------------

    async def get_coverage(self, connector_id: str) -> CoverageDetail:
        """Get binding coverage for a connector."""
        data = await self._client._request(
            "GET", f"/api/connectors/{connector_id}/coverage"
        )
        return CoverageDetail.model_validate(data)

    # ------------------------------------------------------------------
    # Classification suggestions
    # ------------------------------------------------------------------

    async def suggest_classifications(
        self,
        connector_id: str,
        *,
        scan_limit: int = 1000,
        grouping_strategy: str = "individual",
        grouping_pattern: str | None = None,
        sample_size: int = 10,
    ) -> SuggestClassificationsResponse:
        """Generate classification suggestions for unmanaged vectors.

        Uses rule-based pattern matching on resource keys.
        """
        body: dict[str, Any] = {
            "scan_limit": scan_limit,
            "grouping_strategy": grouping_strategy,
            "sample_size": sample_size,
        }
        if grouping_pattern is not None:
            body["grouping_pattern"] = grouping_pattern
        data = await self._client._request(
            "POST",
            f"/api/connectors/{connector_id}/suggest-classifications",
            json=body,
        )
        return SuggestClassificationsResponse.model_validate(data)

    async def apply_suggestions(
        self,
        connector_id: str,
        suggestions: list[ClassificationSuggestion] | list[dict[str, Any]],
    ) -> ApplySuggestionsResponse:
        """Apply approved classification suggestions."""
        entries = [
            s.model_dump() if isinstance(s, ClassificationSuggestion) else s
            for s in suggestions
        ]
        data = await self._client._request(
            "POST",
            f"/api/connectors/{connector_id}/apply-suggestions",
            json={"suggestions": entries},
        )
        return ApplySuggestionsResponse.model_validate(data)

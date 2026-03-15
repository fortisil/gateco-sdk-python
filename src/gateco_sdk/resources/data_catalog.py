"""Data catalog resource — list, detail, update."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk._pagination import AsyncPaginator, Page
from gateco_sdk.types.data_catalog import GatedResource, GatedResourceDetail

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class DataCatalogResource:
    """Namespace for data catalog endpoints.

    Accessed as ``client.data_catalog``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list(
        self,
        page: int = 1,
        per_page: int = 20,
        *,
        classification: str | None = None,
        sensitivity: str | None = None,
        domain: str | None = None,
        label: str | None = None,
        source_connector_id: str | None = None,
    ) -> Page[GatedResource]:
        """Fetch a single page of gated resources from the data catalog."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if classification is not None:
            params["classification"] = classification
        if sensitivity is not None:
            params["sensitivity"] = sensitivity
        if domain is not None:
            params["domain"] = domain
        if label is not None:
            params["label"] = label
        if source_connector_id is not None:
            params["source_connector_id"] = source_connector_id

        raw = await self._client._request(
            "GET", "/api/data-catalog", params=params
        )
        items_raw = raw.get("data", []) if raw else []
        meta = (raw or {}).get("meta", {}).get("pagination", {})
        items = [GatedResource.model_validate(r) for r in items_raw]
        return Page[GatedResource](
            items=items,
            page=meta.get("page", page),
            per_page=meta.get("per_page", per_page),
            total=meta.get("total", len(items)),
            total_pages=meta.get("total_pages", 1),
        )

    def list_all(
        self,
        per_page: int = 100,
        *,
        classification: str | None = None,
        sensitivity: str | None = None,
        domain: str | None = None,
        label: str | None = None,
        source_connector_id: str | None = None,
    ) -> AsyncPaginator[GatedResource]:
        """Return an async iterator that lazily paginates through all resources."""

        async def _fetch(page: int, pp: int) -> dict[str, Any]:
            params: dict[str, Any] = {"page": page, "per_page": pp}
            if classification is not None:
                params["classification"] = classification
            if sensitivity is not None:
                params["sensitivity"] = sensitivity
            if domain is not None:
                params["domain"] = domain
            if label is not None:
                params["label"] = label
            if source_connector_id is not None:
                params["source_connector_id"] = source_connector_id
            return await self._client._request(
                "GET", "/api/data-catalog", params=params
            ) or {}

        return AsyncPaginator[GatedResource](
            _fetch, GatedResource, per_page=per_page
        )

    # ------------------------------------------------------------------
    # Detail + Update
    # ------------------------------------------------------------------

    async def get(self, resource_id: str) -> GatedResourceDetail:
        """Get detailed information for a single resource."""
        data = await self._client._request(
            "GET", f"/api/data-catalog/{resource_id}"
        )
        return GatedResourceDetail.model_validate(data)

    async def update(
        self,
        resource_id: str,
        *,
        classification: str | None = None,
        sensitivity: str | None = None,
        domain: str | None = None,
        labels: list[str] | None = None,
        encryption_mode: str | None = None,
    ) -> GatedResource:
        """Update metadata on a gated resource."""
        body: dict[str, Any] = {}
        if classification is not None:
            body["classification"] = classification
        if sensitivity is not None:
            body["sensitivity"] = sensitivity
        if domain is not None:
            body["domain"] = domain
        if labels is not None:
            body["labels"] = labels
        if encryption_mode is not None:
            body["encryption_mode"] = encryption_mode
        data = await self._client._request(
            "PATCH", f"/api/data-catalog/{resource_id}", json=body
        )
        return GatedResource.model_validate(data)

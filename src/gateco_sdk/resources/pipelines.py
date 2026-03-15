"""Pipelines resource — CRUD + runs."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk._pagination import AsyncPaginator, Page
from gateco_sdk.types.pipelines import Pipeline, PipelineRun

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class PipelinesResource:
    """Namespace for pipeline endpoints.

    Accessed as ``client.pipelines``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list(self, page: int = 1, per_page: int = 20) -> Page[Pipeline]:
        """Fetch a single page of pipelines."""
        raw = await self._client._request(
            "GET",
            "/api/pipelines",
            params={"page": page, "per_page": per_page},
        )
        items_raw = raw.get("data", []) if raw else []
        meta = (raw or {}).get("meta", {}).get("pagination", {})
        items = [Pipeline.model_validate(p) for p in items_raw]
        return Page[Pipeline](
            items=items,
            page=meta.get("page", page),
            per_page=meta.get("per_page", per_page),
            total=meta.get("total", len(items)),
            total_pages=meta.get("total_pages", 1),
        )

    def list_all(self, per_page: int = 100) -> AsyncPaginator[Pipeline]:
        """Return an async iterator that lazily paginates through all pipelines."""

        async def _fetch(page: int, pp: int) -> dict[str, Any]:
            return await self._client._request(
                "GET", "/api/pipelines", params={"page": page, "per_page": pp}
            ) or {}

        return AsyncPaginator[Pipeline](_fetch, Pipeline, per_page=per_page)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def get(self, pipeline_id: str) -> Pipeline:
        """Get a single pipeline by ID."""
        data = await self._client._request(
            "GET", f"/api/pipelines/{pipeline_id}"
        )
        return Pipeline.model_validate(data)

    async def create(
        self,
        name: str,
        source_connector_id: str,
        *,
        envelope_config: dict[str, Any] | None = None,
        schedule: str = "manual",
    ) -> Pipeline:
        """Create a new pipeline."""
        body: dict[str, Any] = {
            "name": name,
            "source_connector_id": source_connector_id,
            "schedule": schedule,
        }
        if envelope_config is not None:
            body["envelope_config"] = envelope_config
        data = await self._client._request("POST", "/api/pipelines", json=body)
        return Pipeline.model_validate(data)

    async def update(
        self,
        pipeline_id: str,
        *,
        name: str | None = None,
        envelope_config: dict[str, Any] | None = None,
        status: str | None = None,
        schedule: str | None = None,
    ) -> Pipeline:
        """Update an existing pipeline."""
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if envelope_config is not None:
            body["envelope_config"] = envelope_config
        if status is not None:
            body["status"] = status
        if schedule is not None:
            body["schedule"] = schedule
        data = await self._client._request(
            "PATCH", f"/api/pipelines/{pipeline_id}", json=body
        )
        return Pipeline.model_validate(data)

    # ------------------------------------------------------------------
    # Runs
    # ------------------------------------------------------------------

    async def get_runs(self, pipeline_id: str) -> list[PipelineRun]:
        """List runs for a pipeline."""
        raw = await self._client._request(
            "GET", f"/api/pipelines/{pipeline_id}/runs"
        )
        items_raw = raw.get("data", []) if raw else []
        return [PipelineRun.model_validate(r) for r in items_raw]

    async def run(self, pipeline_id: str) -> dict[str, Any]:
        """Trigger a pipeline run."""
        data = await self._client._request(
            "POST", f"/api/pipelines/{pipeline_id}/run"
        )
        return data or {}

"""Simulator resource — dry-run and live preview policy evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from gateco_sdk.types.simulator import SimulationRequest, SimulationResult

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class SimulatorResource:
    """Namespace for access simulator endpoints.

    Accessed as ``client.simulator``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def run(
        self,
        principal_id: str,
        *,
        query: str | None = None,
        connector_id: str | None = None,
        resource_ids: list[str] | None = None,
    ) -> SimulationResult:
        """Run a dry-run policy simulation for a principal against resources.

        Args:
            principal_id: The ID of the principal to simulate for.
            query: Optional query string to scope the simulation.
            connector_id: Optional connector ID to scope resources.
            resource_ids: Optional explicit list of resource IDs to evaluate.

        Returns:
            Simulation result with outcome, counts, policy trace, and denial reasons.
        """
        body = SimulationRequest(
            principal_id=principal_id,
            query=query,
            connector_id=connector_id,
            resource_ids=resource_ids,
        )
        data = await self._client._request(
            "POST", "/api/simulator/run", json=body.model_dump(exclude_none=True)
        )
        return SimulationResult.model_validate(data)

    async def run_preview(
        self,
        principal_id: str,
        connector_id: str,
        query: str,
        *,
        top_k: int = 10,
        search_mode: Literal["vector", "keyword", "hybrid"] = "vector",
        alpha: float | None = None,
    ) -> dict[str, Any]:
        """Execute a live preview — real search + policy evaluation for a single principal (Pro+ only).

        Denied results contain metadata and denial reasons but no content.
        ``top_k`` is capped at 20 server-side.

        Args:
            principal_id: The ID of the principal to simulate for.
            connector_id: The connector to search against.
            query: Natural-language search query.
            top_k: Maximum results to return (capped at 20).
            search_mode: Search mode — vector, keyword, or hybrid.
            alpha: Hybrid alpha (0.0 = pure keyword, 1.0 = pure vector).
        """
        body: dict[str, Any] = {
            "principal_id": principal_id,
            "connector_id": connector_id,
            "query": query,
            "top_k": top_k,
            "search_mode": search_mode,
        }
        if alpha is not None:
            body["alpha"] = alpha
        data = await self._client._request(
            "POST", "/api/simulator/preview", json=body
        )
        return data or {}

    async def run_batch_preview(
        self,
        principal_ids: list[str],
        connector_id: str,
        query: str,
        *,
        top_k: int = 10,
        search_mode: Literal["vector", "keyword", "hybrid"] = "vector",
        alpha: float | None = None,
    ) -> dict[str, Any]:
        """Execute a batch live preview — one search, up to 5 principals (Pro+ only).

        Runs the search once then fans out policy evaluation across all specified
        principals in parallel. Returns a result matrix per principal.

        Args:
            principal_ids: Up to 5 principal IDs to evaluate.
            connector_id: The connector to search against.
            query: Natural-language search query.
            top_k: Maximum results per evaluation (capped at 20).
            search_mode: Search mode — vector, keyword, or hybrid.
            alpha: Hybrid alpha (0.0 = pure keyword, 1.0 = pure vector).
        """
        body: dict[str, Any] = {
            "principal_ids": principal_ids,
            "connector_id": connector_id,
            "query": query,
            "top_k": top_k,
            "search_mode": search_mode,
        }
        if alpha is not None:
            body["alpha"] = alpha
        data = await self._client._request(
            "POST", "/api/simulator/preview-batch", json=body
        )
        return data or {}

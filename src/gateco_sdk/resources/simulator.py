"""Simulator resource — dry-run policy evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

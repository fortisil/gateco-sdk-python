"""Dashboard resource — aggregated stats."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gateco_sdk.types.dashboard import DashboardStats

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class DashboardResource:
    """Namespace for dashboard endpoints.

    Accessed as ``client.dashboard``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def get_stats(self) -> DashboardStats:
        """Fetch aggregated dashboard statistics.

        Returns:
            Dashboard stats including retrieval counts, connector status,
            IDP status, coverage metrics, and recent denied retrievals.
        """
        data = await self._client._request("GET", "/api/dashboard/stats")
        return DashboardStats.model_validate(data)

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

    async def get_stats(self, *, sparklines: bool = False) -> DashboardStats:
        """Fetch aggregated dashboard statistics.

        Args:
            sparklines: When True, includes 24h hourly + 7d daily sparkline arrays.
                Requires the ``advanced_analytics`` entitlement; silently degraded
                to ``None`` for plans without it.

        Returns:
            Dashboard stats including retrieval counts, connector status,
            IDP status, coverage metrics, and recent denied retrievals.
        """
        data = await self._client._request(
            "GET", "/api/dashboard/stats",
            params={"sparklines": "true"} if sparklines else None,
        )
        return DashboardStats.model_validate(data)

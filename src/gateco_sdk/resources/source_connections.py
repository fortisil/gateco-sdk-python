"""Source connections resource — document sources with permission import."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class SourceConnectionsResource:
    """Namespace for source connections (Growth plan and above).

    Accessed as ``client.sources``. Sources: gdrive, sharepoint, confluence,
    notion (plus a stub for testing). Secrets are encrypted server-side and
    never returned by any endpoint.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def create(
        self, name: str, source_type: str, config: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._client._request(
            "POST", "/api/source-connections",
            json={"name": name, "source_type": source_type, "config": config},
        )

    async def list(self) -> list[dict[str, Any]]:
        data = await self._client._request("GET", "/api/source-connections")
        return data.get("data", [])

    async def get(self, source_connection_id: str) -> dict[str, Any]:
        return await self._client._request(
            "GET", f"/api/source-connections/{source_connection_id}",
        )

    async def delete(self, source_connection_id: str) -> None:
        await self._client._request(
            "DELETE", f"/api/source-connections/{source_connection_id}",
        )

    async def test(self, source_connection_id: str) -> dict[str, Any]:
        return await self._client._request(
            "POST", f"/api/source-connections/{source_connection_id}/test",
        )

    async def acl_coverage(self, source_connection_id: str) -> dict[str, Any]:
        """Coverage report: matched/unmatched principals in imported ACLs."""
        return await self._client._request(
            "GET", f"/api/source-connections/{source_connection_id}/acl-coverage",
        )

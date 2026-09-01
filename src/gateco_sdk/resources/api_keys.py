"""API keys resource — create, list, delete, rotate."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class ApiKeysResource:
    """Namespace for API key management endpoints.

    Accessed as ``client.api_keys``.

    API keys use the format ``gck_<prefix>_<random>`` and are tied to the
    authenticated organisation.  The plaintext key is returned **only once**
    at creation time; subsequent requests expose only the ``prefix`` for
    identification.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def create(
        self,
        name: str,
        scopes: list[str],
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        """Create a new API key.

        The full plaintext key (``key`` field) is returned exactly once in the
        response and cannot be retrieved again.  Store it securely.

        Args:
            name: Human-readable label for the key (e.g. ``"prod-worker"``).
            scopes: What the key may do. One or more of ``"ingest"``,
                ``"relationships"``, ``"retrieve"``, ``"principals"``. Required:
                a key is created with exactly the scopes it needs. A RAG service
                needs ``["retrieve"]``; an ingestion pipeline ``["ingest"]``.
            expires_at: Optional ISO 8601 expiry datetime string.  When omitted
                the key does not expire.

        Returns:
            Dict containing ``id``, ``name``, ``prefix``, and ``key``
            (plaintext, shown once).
        """
        body: dict[str, Any] = {"name": name, "scopes": list(scopes)}
        if expires_at is not None:
            body["expires_at"] = expires_at
        data = await self._client._request("POST", "/api/api-keys", json=body)
        return data or {}

    async def list(self) -> dict[str, Any]:
        """List all API keys for the current organisation.

        Returns key metadata only — the plaintext key is never included in
        list responses.

        Returns:
            Dict with a ``data`` list of key records (``id``, ``name``,
            ``prefix``, ``created_at``, ``expires_at``, ``last_used_at``).
        """
        data = await self._client._request("GET", "/api/api-keys")
        return data or {}

    async def delete(self, key_id: str) -> dict[str, Any]:
        """Revoke and permanently delete an API key.

        Args:
            key_id: The UUID of the API key to delete.

        Returns:
            Confirmation payload from the server.
        """
        data = await self._client._request("DELETE", f"/api/api-keys/{key_id}")
        return data or {}

    async def rotate(self, key_id: str) -> dict[str, Any]:
        """Rotate an existing API key, invalidating the old value.

        The new plaintext key is returned in the ``key`` field and is shown
        only once.  The key ``id`` and ``name`` remain the same.

        Args:
            key_id: The UUID of the API key to rotate.

        Returns:
            Dict containing ``id``, ``name``, ``prefix``, and ``key``
            (new plaintext, shown once).
        """
        data = await self._client._request("POST", f"/api/api-keys/{key_id}/rotate")
        return data or {}

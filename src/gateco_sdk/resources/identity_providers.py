"""Identity providers resource — CRUD + sync."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk._pagination import AsyncPaginator, Page
from gateco_sdk.types.identity_providers import IdentityProvider

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class IdentityProvidersResource:
    """Namespace for identity provider endpoints.

    Accessed as ``client.identity_providers``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list(self, page: int = 1, per_page: int = 20) -> Page[IdentityProvider]:
        """Fetch a single page of identity providers."""
        raw = await self._client._request(
            "GET",
            "/api/identity-providers",
            params={"page": page, "per_page": per_page},
        )
        items_raw = raw.get("data", []) if raw else []
        meta = (raw or {}).get("meta", {}).get("pagination", {})
        items = [IdentityProvider.model_validate(i) for i in items_raw]
        return Page[IdentityProvider](
            items=items,
            page=meta.get("page", page),
            per_page=meta.get("per_page", per_page),
            total=meta.get("total", len(items)),
            total_pages=meta.get("total_pages", 1),
        )

    def list_all(self, per_page: int = 100) -> AsyncPaginator[IdentityProvider]:
        """Return an async iterator that lazily paginates through all identity providers."""

        async def _fetch(page: int, pp: int) -> dict[str, Any]:
            return await self._client._request(
                "GET", "/api/identity-providers", params={"page": page, "per_page": pp}
            ) or {}

        return AsyncPaginator[IdentityProvider](
            _fetch, IdentityProvider, per_page=per_page
        )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def get(self, idp_id: str) -> IdentityProvider:
        """Get a single identity provider by ID."""
        data = await self._client._request(
            "GET", f"/api/identity-providers/{idp_id}"
        )
        return IdentityProvider.model_validate(data)

    async def create(
        self,
        name: str,
        type: str,
        *,
        config: dict[str, Any] | None = None,
        sync_config: dict[str, Any] | None = None,
    ) -> IdentityProvider:
        """Create a new identity provider."""
        body: dict[str, Any] = {"name": name, "type": type}
        if config is not None:
            body["config"] = config
        if sync_config is not None:
            body["sync_config"] = sync_config
        data = await self._client._request(
            "POST", "/api/identity-providers", json=body
        )
        return IdentityProvider.model_validate(data)

    async def update(
        self,
        idp_id: str,
        *,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        sync_config: dict[str, Any] | None = None,
    ) -> IdentityProvider:
        """Update an existing identity provider."""
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if config is not None:
            body["config"] = config
        if sync_config is not None:
            body["sync_config"] = sync_config
        data = await self._client._request(
            "PATCH", f"/api/identity-providers/{idp_id}", json=body
        )
        return IdentityProvider.model_validate(data)

    async def delete(self, idp_id: str) -> None:
        """Delete an identity provider."""
        await self._client._request("DELETE", f"/api/identity-providers/{idp_id}")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def sync(self, idp_id: str) -> dict[str, Any]:
        """Trigger a sync for an identity provider."""
        data = await self._client._request(
            "POST", f"/api/identity-providers/{idp_id}/sync"
        )
        return data or {}

    # ------------------------------------------------------------------
    # SCIM token management
    # ------------------------------------------------------------------

    async def generate_scim_token(self, idp_id: str) -> dict[str, Any]:
        """Generate a SCIM bearer token for an IDP (Enterprise only).

        The plaintext token is returned exactly once and is never retrievable
        again. Generating a new token automatically revokes any existing token
        for this IDP.
        """
        data = await self._client._request(
            "POST", f"/api/identity-providers/{idp_id}/scim-token"
        )
        return data or {}

    async def revoke_scim_token(self, idp_id: str) -> None:
        """Revoke the current SCIM token for an identity provider."""
        await self._client._request(
            "DELETE", f"/api/identity-providers/{idp_id}/scim-token"
        )

    # ------------------------------------------------------------------
    # Policy suggestions
    # ------------------------------------------------------------------

    async def suggest_policies(self, idp_id: str) -> list[dict[str, Any]]:
        """Generate conservative policy suggestions from synced IDP principal data (Pro+ only).

        Analyzes groups and departments to suggest RBAC/ABAC starting policies
        with confidence scores and explanations.
        """
        raw = await self._client._request(
            "POST", f"/api/identity-providers/{idp_id}/suggest-policies"
        )
        items = (raw or {}).get("suggestions", [])
        return items if isinstance(items, list) else []

    async def apply_policy_suggestions(
        self,
        idp_id: str,
        suggestion_ids: list[str],
    ) -> dict[str, Any]:
        """Apply accepted policy suggestions as draft policies (Pro+ only).

        Args:
            idp_id: The identity provider ID.
            suggestion_ids: List of suggestion IDs to apply. Only accepted
                suggestions create policies; rejected IDs are ignored.
        """
        data = await self._client._request(
            "POST",
            f"/api/identity-providers/{idp_id}/apply-policy-suggestions",
            json={"suggestion_ids": suggestion_ids},
        )
        return data or {}

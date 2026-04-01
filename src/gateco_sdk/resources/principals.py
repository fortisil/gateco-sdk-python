"""Principals resource — list + detail."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk._pagination import AsyncPaginator, Page
from gateco_sdk.types.principals import Principal

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class PrincipalsResource:
    """Namespace for principal endpoints.

    Accessed as ``client.principals``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list(self, page: int = 1, per_page: int = 20) -> Page[Principal]:
        """Fetch a single page of principals."""
        raw = await self._client._request(
            "GET",
            "/api/principals",
            params={"page": page, "per_page": per_page},
        )
        items_raw = raw.get("data", []) if raw else []
        meta = (raw or {}).get("meta", {}).get("pagination", {})
        items = [Principal.model_validate(p) for p in items_raw]
        return Page[Principal](
            items=items,
            page=meta.get("page", page),
            per_page=meta.get("per_page", per_page),
            total=meta.get("total", len(items)),
            total_pages=meta.get("total_pages", 1),
        )

    def list_all(self, per_page: int = 100) -> AsyncPaginator[Principal]:
        """Return an async iterator that lazily paginates through all principals."""

        async def _fetch(page: int, pp: int) -> dict[str, Any]:
            return await self._client._request(
                "GET", "/api/principals", params={"page": page, "per_page": pp}
            ) or {}

        return AsyncPaginator[Principal](_fetch, Principal, per_page=per_page)

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------

    async def get(self, principal_id: str) -> Principal:
        """Get a single principal by ID."""
        data = await self._client._request(
            "GET", f"/api/principals/{principal_id}"
        )
        return Principal.model_validate(data)

    # ------------------------------------------------------------------
    # Resolve
    # ------------------------------------------------------------------

    async def resolve(
        self,
        *,
        email: str | None = None,
        provider_subject: str | None = None,
        identity_provider_id: str | None = None,
    ) -> Principal:
        """Resolve a principal by email or provider subject ID.

        At least one of ``email`` or ``provider_subject`` must be provided.
        When both are given, the server uses them conjunctively for a more
        precise match.  ``identity_provider_id`` optionally scopes the lookup
        to a single identity provider.

        Args:
            email: Email address of the principal to resolve.
            provider_subject: Provider-native subject identifier (e.g. the
                Okta user ID, Google sub claim, or AWS external ID).
            identity_provider_id: UUID of the identity provider to scope the
                lookup to.  When omitted the server searches across all
                providers in the organisation.

        Returns:
            The resolved :class:`~gateco_sdk.types.principals.Principal`.

        Raises:
            ValueError: If neither ``email`` nor ``provider_subject`` is given.
            gateco_sdk.errors.NotFoundError: If no matching principal is found.
        """
        if not email and not provider_subject:
            raise ValueError(
                "At least one of 'email' or 'provider_subject' must be provided."
            )

        body: dict[str, str] = {}
        if email:
            body["email"] = email
        if provider_subject:
            body["provider_subject"] = provider_subject
        if identity_provider_id:
            body["identity_provider_id"] = identity_provider_id

        data = await self._client._request(
            "POST", "/api/principals/resolve", json=body
        )
        return Principal.model_validate(data)

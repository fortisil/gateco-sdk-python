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

    async def list(
        self,
        page: int = 1,
        per_page: int = 20,
        *,
        status: str | None = None,
        search: str | None = None,
        group: str | None = None,
    ) -> Page[Principal]:
        """Fetch a single page of principals.

        Args:
            page: 1-based page number.
            per_page: Page size (server caps at 100).
            status: Optional status filter — ``"active"``, ``"inactive"``,
                ``"suspended"``, or ``"all"``. Omitted = active only (the
                legacy default).
            search: Optional case-insensitive substring filter on display
                name or email.
            group: Optional exact group name the principal is a member of.
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if status is not None:
            params["status"] = status
        if search is not None:
            params["search"] = search
        if group is not None:
            params["group"] = group
        raw = await self._client._request("GET", "/api/principals", params=params)
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

    def list_all(
        self,
        per_page: int = 100,
        *,
        status: str | None = None,
        search: str | None = None,
        group: str | None = None,
    ) -> AsyncPaginator[Principal]:
        """Return an async iterator that lazily paginates through all principals.

        Accepts the same optional ``status``/``search``/``group`` filters as
        :meth:`list`.
        """

        async def _fetch(page: int, pp: int) -> dict[str, Any]:
            params: dict[str, Any] = {"page": page, "per_page": pp}
            if status is not None:
                params["status"] = status
            if search is not None:
                params["search"] = search
            if group is not None:
                params["group"] = group
            return await self._client._request(
                "GET", "/api/principals", params=params
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
    # Local directory (create / update / delete)
    # ------------------------------------------------------------------

    async def create(
        self,
        email: str,
        *,
        display_name: str | None = None,
        groups: list[str] | None = None,
        roles: list[str] | None = None,
        attributes: dict[str, Any] | None = None,
        provider_subject: str | None = None,
    ) -> Principal:
        """Create a principal in the organisation's built-in local directory.

        Available on every plan, bounded by the plan's ``principals`` limit
        (Free 10 / Team 100 / Growth+ unlimited). The local directory is
        provisioned automatically on first use and never syncs. Principals
        from a synced identity provider or SCIM are not created here.

        Raises:
            gateco_sdk.errors.ConflictError: An active principal with this
                email already exists in the local directory.
            gateco_sdk.errors.EntitlementError: The plan's principal limit is
                reached (``is_limit`` is True).
        """
        body: dict[str, Any] = {"email": email}
        if display_name is not None:
            body["display_name"] = display_name
        if groups is not None:
            body["groups"] = groups
        if roles is not None:
            body["roles"] = roles
        if attributes is not None:
            body["attributes"] = attributes
        if provider_subject is not None:
            body["provider_subject"] = provider_subject
        data = await self._client._request("POST", "/api/principals", json=body)
        return Principal.model_validate(data)

    async def update(
        self,
        principal_id: str,
        *,
        display_name: str | None = None,
        groups: list[str] | None = None,
        roles: list[str] | None = None,
        attributes: dict[str, Any] | None = None,
        status: str | None = None,
    ) -> Principal:
        """Update a local principal. Synced principals are rejected (422).

        ``status`` may be ``"active"``, ``"inactive"`` or ``"suspended"``;
        reactivating consumes a principal slot again.
        """
        body: dict[str, Any] = {}
        if display_name is not None:
            body["display_name"] = display_name
        if groups is not None:
            body["groups"] = groups
        if roles is not None:
            body["roles"] = roles
        if attributes is not None:
            body["attributes"] = attributes
        if status is not None:
            body["status"] = status
        data = await self._client._request(
            "PATCH", f"/api/principals/{principal_id}", json=body
        )
        return Principal.model_validate(data)

    async def delete(self, principal_id: str) -> None:
        """Deactivate a local principal (status -> inactive).

        Never a hard delete: the audit trail is preserved and retrieval
        refuses the principal, exactly like a SCIM offboarding.
        """
        await self._client._request("DELETE", f"/api/principals/{principal_id}")

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

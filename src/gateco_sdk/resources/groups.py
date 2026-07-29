"""Groups resource — read-only directory of IdP-synced groups."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk._pagination import AsyncPaginator, Page
from gateco_sdk.types.groups import PrincipalGroup

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class GroupsResource:
    """Namespace for group endpoints.

    Accessed as ``client.groups``.
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
        search: str | None = None,
    ) -> Page[PrincipalGroup]:
        """Fetch a single page of groups.

        Args:
            page: 1-based page number.
            per_page: Page size (server caps at 100).
            search: Optional case-insensitive substring filter on group name.
        """
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if search is not None:
            params["search"] = search
        raw = await self._client._request("GET", "/api/groups", params=params)
        items_raw = raw.get("data", []) if raw else []
        meta = (raw or {}).get("meta", {}).get("pagination", {})
        items = [PrincipalGroup.model_validate(g) for g in items_raw]
        return Page[PrincipalGroup](
            items=items,
            page=meta.get("page", page),
            per_page=meta.get("per_page", per_page),
            total=meta.get("total", len(items)),
            total_pages=meta.get("total_pages", 1),
        )

    def list_all(
        self, per_page: int = 100, *, search: str | None = None
    ) -> AsyncPaginator[PrincipalGroup]:
        """Return an async iterator that lazily paginates through all groups."""

        async def _fetch(page: int, pp: int) -> dict[str, Any]:
            params: dict[str, Any] = {"page": page, "per_page": pp}
            if search is not None:
                params["search"] = search
            return await self._client._request(
                "GET", "/api/groups", params=params
            ) or {}

        return AsyncPaginator[PrincipalGroup](_fetch, PrincipalGroup, per_page=per_page)

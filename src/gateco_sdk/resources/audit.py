"""Audit resource — list + export."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk._pagination import AsyncPaginator, Page
from gateco_sdk.types.audit import AuditEvent

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class AuditResource:
    """Namespace for audit log endpoints.

    Accessed as ``client.audit``.
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
        event_types: str | None = None,
        actor: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> Page[AuditEvent]:
        """Fetch a single page of audit events."""
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if event_types is not None:
            params["event_types"] = event_types
        if actor is not None:
            params["actor"] = actor
        if date_from is not None:
            params["date_from"] = date_from
        if date_to is not None:
            params["date_to"] = date_to

        raw = await self._client._request(
            "GET", "/api/audit-log", params=params
        )
        items_raw = raw.get("data", []) if raw else []
        meta = (raw or {}).get("meta", {}).get("pagination", {})
        items = [AuditEvent.model_validate(e) for e in items_raw]
        return Page[AuditEvent](
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
        event_types: str | None = None,
        actor: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> AsyncPaginator[AuditEvent]:
        """Return an async iterator that lazily paginates through all audit events."""

        async def _fetch(page: int, pp: int) -> dict[str, Any]:
            params: dict[str, Any] = {"page": page, "per_page": pp}
            if event_types is not None:
                params["event_types"] = event_types
            if actor is not None:
                params["actor"] = actor
            if date_from is not None:
                params["date_from"] = date_from
            if date_to is not None:
                params["date_to"] = date_to
            return await self._client._request(
                "GET", "/api/audit-log", params=params
            ) or {}

        return AsyncPaginator[AuditEvent](_fetch, AuditEvent, per_page=per_page)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def export_csv(
        self,
        *,
        event_types: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        format: str = "csv",
    ) -> dict[str, Any]:
        """Export audit log as JSON or CSV.

        Note: The backend returns a streaming file response. This method sends
        the request; for binary download handling the caller should use the
        transport layer directly. This convenience method returns the raw
        response dict (which may be empty for streaming responses).
        """
        params: dict[str, Any] = {"format": format}
        if event_types is not None:
            params["event_types"] = event_types
        if date_from is not None:
            params["date_from"] = date_from
        if date_to is not None:
            params["date_to"] = date_to
        data = await self._client._request(
            "POST", "/api/audit-log/export", params=params
        )
        return data or {}

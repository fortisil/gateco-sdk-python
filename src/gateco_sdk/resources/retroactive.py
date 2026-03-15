"""Retroactive registration resource — register unmanaged vectors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk.types.retroactive import (
    RetroactiveRegisterRequest,
    RetroactiveRegisterResponse,
)

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class RetroactiveResource:
    """Namespace for retroactive registration endpoints.

    Accessed as ``client.retroactive``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def register(
        self,
        connector_id: str,
        *,
        scan_limit: int = 1000,
        default_classification: str | None = None,
        default_sensitivity: str | None = None,
        default_domain: str | None = None,
        default_labels: list[str] | None = None,
        grouping_strategy: str = "individual",
        grouping_pattern: str | None = None,
        dry_run: bool = False,
    ) -> RetroactiveRegisterResponse:
        """Scan a connector's vector DB and register unmanaged vectors as gated resources.

        Requires a Tier 1 connector (pgvector, supabase, neon, pinecone, qdrant).

        Args:
            connector_id: The connector to scan (must be Tier 1).
            scan_limit: Maximum vectors to scan (1-10000).
            default_classification: Default classification for new resources.
            default_sensitivity: Default sensitivity for new resources.
            default_domain: Default domain for new resources.
            default_labels: Default labels for new resources.
            grouping_strategy: How to group vectors into resources
                (``individual``, ``regex``, or ``prefix``).
            grouping_pattern: Pattern for regex/prefix grouping.
            dry_run: If ``True``, simulate without creating resources.

        Returns:
            Registration result with counts and any errors.
        """
        body = RetroactiveRegisterRequest(
            connector_id=connector_id,
            scan_limit=scan_limit,
            default_classification=default_classification,
            default_sensitivity=default_sensitivity,
            default_domain=default_domain,
            default_labels=default_labels,
            grouping_strategy=grouping_strategy,
            grouping_pattern=grouping_pattern,
            dry_run=dry_run,
        )
        data = await self._client._request(
            "POST",
            "/api/v1/retroactive-register",
            json=body.model_dump(exclude_none=True),
        )
        return RetroactiveRegisterResponse.model_validate(data)

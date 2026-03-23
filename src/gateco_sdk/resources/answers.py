"""Answers resource — grounded answer synthesis."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk.types.answers import Answer

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class AnswersResource:
    """Namespace for answer synthesis endpoints.

    Accessed as ``client.answers``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def execute(
        self,
        query: str,
        *,
        principal_id: str,
        connector_id: str,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> Answer:
        """Execute a grounded answer synthesis.

        Args:
            query: Natural language question.
            principal_id: Identity of the requesting principal.
            connector_id: Connector to search against.
            top_k: Maximum chunks for context (default: 5).
            filters: Optional filter dict for scoping results.
        """
        body: dict[str, Any] = {
            "query": query,
            "principal_id": principal_id,
            "connector_id": connector_id,
        }
        if top_k is not None:
            body["top_k"] = top_k
        if filters is not None:
            body["filters"] = filters

        data = await self._client._request(
            "POST", "/api/answers/execute", json=body
        )
        return Answer.model_validate(data)

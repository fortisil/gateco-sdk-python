"""Relationships resource — create, list, delete principal-resource relations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class RelationshipResource:
    """Namespace for relationship management endpoints.

    Accessed as ``client.relationships``.

    Relationships express named access relations between a principal and a
    gated resource (e.g. ``"owner"``, ``"editor"``, ``"viewer"``).  They are
    used by the policy engine to evaluate access at retrieval time.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def create(
        self,
        subject_principal_id: str,
        relation_name: str,
        object_resource_id: str,
    ) -> dict[str, Any]:
        """Create a new relationship between a principal and a resource.

        Args:
            subject_principal_id: UUID of the principal that holds the relation.
            relation_name: Name of the relation (e.g. ``"owner"``, ``"viewer"``).
            object_resource_id: UUID of the gated resource that is the object.

        Returns:
            Dict representing the created relationship record (includes ``id``,
            ``subject_principal_id``, ``relation_name``, ``object_resource_id``,
            ``created_at``).
        """
        body: dict[str, Any] = {
            "subject_principal_id": subject_principal_id,
            "relation_name": relation_name,
            "object_resource_id": object_resource_id,
        }
        data = await self._client._request("POST", "/api/relationships", json=body)
        return data or {}

    async def list(
        self,
        *,
        subject_id: str | None = None,
        relation: str | None = None,
        object_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List relationships, optionally filtered by subject, relation, or object.

        All filter parameters are optional and combinable.

        Args:
            subject_id: Filter to relationships where this principal is the subject.
            relation: Filter to relationships with this relation name.
            object_id: Filter to relationships where this resource is the object.

        Returns:
            List of relationship dicts.
        """
        params: dict[str, str] = {}
        if subject_id is not None:
            params["subject_id"] = subject_id
        if relation is not None:
            params["relation"] = relation
        if object_id is not None:
            params["object_id"] = object_id

        data = await self._client._request(
            "GET", "/api/relationships", params=params or None
        )
        if data is None:
            return []
        # Backend may return a paginated envelope {"data": [...]} or a bare list.
        if isinstance(data, list):
            return data
        return data.get("data", [])

    async def delete(self, relationship_id: str) -> None:
        """Delete a relationship by its ID.

        The backend returns 204 No Content on success.

        Args:
            relationship_id: UUID of the relationship to delete.
        """
        await self._client._request("DELETE", f"/api/relationships/{relationship_id}")

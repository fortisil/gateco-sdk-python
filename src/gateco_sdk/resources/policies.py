"""Policies resource — CRUD + lifecycle (activate, archive)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk._pagination import AsyncPaginator, Page
from gateco_sdk.types.policies import Policy

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class PoliciesResource:
    """Namespace for policy endpoints.

    Accessed as ``client.policies``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list(self, page: int = 1, per_page: int = 20) -> Page[Policy]:
        """Fetch a single page of policies."""
        raw = await self._client._request(
            "GET",
            "/api/policies",
            params={"page": page, "per_page": per_page},
        )
        items_raw = raw.get("data", []) if raw else []
        meta = (raw or {}).get("meta", {}).get("pagination", {})
        items = [Policy.model_validate(p) for p in items_raw]
        return Page[Policy](
            items=items,
            page=meta.get("page", page),
            per_page=meta.get("per_page", per_page),
            total=meta.get("total", len(items)),
            total_pages=meta.get("total_pages", 1),
        )

    def list_all(self, per_page: int = 100) -> AsyncPaginator[Policy]:
        """Return an async iterator that lazily paginates through all policies."""

        async def _fetch(page: int, pp: int) -> dict[str, Any]:
            return await self._client._request(
                "GET", "/api/policies", params={"page": page, "per_page": pp}
            ) or {}

        return AsyncPaginator[Policy](_fetch, Policy, per_page=per_page)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def get(self, policy_id: str) -> Policy:
        """Get a single policy by ID."""
        data = await self._client._request("GET", f"/api/policies/{policy_id}")
        return Policy.model_validate(data)

    async def create(
        self,
        name: str,
        type: str,
        effect: str,
        *,
        description: str | None = None,
        resource_selectors: list[dict[str, Any]] | None = None,
        rules: list[dict[str, Any]] | None = None,
    ) -> Policy:
        """Create a new policy.

        Each rule's ``conditions`` list contains dicts with ``field``, ``operator``,
        and ``value`` keys. Fields **must** be prefixed:

        - ``resource.classification``, ``resource.sensitivity``, etc. for resource checks
        - ``principal.roles``, ``principal.groups``, etc. for principal checks

        Bare field names silently resolve against the principal.

        **Operators:** ``eq``, ``ne``, ``in``, ``contains``, ``lte``, ``gte``.

        **Deny policy note:** When a deny policy's selectors match but no rules match,
        the policy-level ``effect=deny`` fires. Add a catch-all allow rule to deny only
        specific conditions.
        """
        body: dict[str, Any] = {"name": name, "type": type, "effect": effect}
        if description is not None:
            body["description"] = description
        if resource_selectors is not None:
            body["resource_selectors"] = resource_selectors
        if rules is not None:
            body["rules"] = rules
        data = await self._client._request("POST", "/api/policies", json=body)
        return Policy.model_validate(data)

    async def update(
        self,
        policy_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        effect: str | None = None,
        resource_selectors: list[dict[str, Any]] | None = None,
        rules: list[dict[str, Any]] | None = None,
    ) -> Policy:
        """Update an existing policy."""
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if effect is not None:
            body["effect"] = effect
        if resource_selectors is not None:
            body["resource_selectors"] = resource_selectors
        if rules is not None:
            body["rules"] = rules
        data = await self._client._request(
            "PATCH", f"/api/policies/{policy_id}", json=body
        )
        return Policy.model_validate(data)

    async def delete(self, policy_id: str) -> None:
        """Delete a policy."""
        await self._client._request("DELETE", f"/api/policies/{policy_id}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def activate(self, policy_id: str) -> Policy:
        """Activate a draft or archived policy."""
        data = await self._client._request(
            "POST", f"/api/policies/{policy_id}/activate"
        )
        return Policy.model_validate(data)

    async def archive(self, policy_id: str) -> Policy:
        """Archive an active policy."""
        data = await self._client._request(
            "POST", f"/api/policies/{policy_id}/archive"
        )
        return Policy.model_validate(data)

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    async def list_templates(self) -> list[dict[str, Any]]:
        """List the static catalog of policy templates (all plans).

        Returns a list of template dicts with ``id``, ``name``, ``description``,
        ``category``, and ``placeholder_keys`` fields.
        """
        raw = await self._client._request("GET", "/api/policies/templates")
        items = (raw or {}).get("data", [])
        return items if isinstance(items, list) else []

    async def create_from_template(
        self,
        template_id: str,
        placeholder_values: dict[str, str],
        *,
        name: str | None = None,
    ) -> Policy:
        """Create a draft policy from a template (Team+ only).

        Args:
            template_id: One of ``group_rbac``, ``department_access``,
                ``classification_ceiling``, ``deny_sensitive``, ``label_access``,
                ``connector_scoped_allow``, ``global_internal_read``.
            placeholder_values: Map of ``{placeholder_key: value}`` substitutions.
            name: Optional override for the policy name.
        """
        body: dict[str, Any] = {
            "template_id": template_id,
            "placeholder_values": placeholder_values,
        }
        if name is not None:
            body["name"] = name
        data = await self._client._request(
            "POST", "/api/policies/from-template", json=body
        )
        return Policy.model_validate(data)

    # ------------------------------------------------------------------
    # Versioning
    # ------------------------------------------------------------------

    async def list_versions(self, policy_id: str) -> list[dict[str, Any]]:
        """List all saved versions of a policy (Team+ only)."""
        raw = await self._client._request(
            "GET", f"/api/policies/{policy_id}/versions"
        )
        items = (raw or {}).get("data", [])
        return items if isinstance(items, list) else []

    async def restore_version(self, policy_id: str, version: int) -> Policy:
        """Restore a policy to a saved version (Team+ only)."""
        data = await self._client._request(
            "POST", f"/api/policies/{policy_id}/versions/{version}/restore"
        )
        return Policy.model_validate(data)

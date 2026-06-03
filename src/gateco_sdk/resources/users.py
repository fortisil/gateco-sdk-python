"""Users resource — current user profile (GET /me, PATCH /me) and organization settings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk.types.auth import User

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class UsersResource:
    """Namespace for user profile endpoints.

    Accessed as ``client.users``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def get_me(self) -> User:
        """Get the current authenticated user with organization plan.

        Returns the full user profile including organization plan tier,
        which controls entitlement gating.
        """
        data = await self._client._request("GET", "/api/users/me")
        return User.model_validate(data)

    async def update_me(self, name: str) -> User:
        """Update the current user's display name.

        Args:
            name: New display name (stripped server-side).

        Returns:
            Updated :class:`~gateco_sdk.types.auth.User`.
        """
        data = await self._client._request(
            "PATCH", "/api/users/me", json={"name": name}
        )
        return User.model_validate(data)

    # ------------------------------------------------------------------
    # Organization settings
    # ------------------------------------------------------------------

    async def get_org_settings(self) -> dict[str, Any]:
        """Get organization-level settings.

        Returns configuration status for features that require per-org
        setup (e.g. whether an LLM API key is configured for answer
        synthesis).

        Returns:
            Dict with keys: ``id``, ``name``, ``slug``, ``plan``,
            ``failure_mode``, ``llm_provider``,
            ``llm_api_key_configured``.
        """
        data = await self._client._request("GET", "/api/organization/settings")
        return dict(data) if data else {}

    async def update_org_settings(
        self,
        *,
        name: str | None = None,
        failure_mode: str | None = None,
        llm_api_key: str | None = None,
        llm_provider: str | None = None,
        clear_llm_api_key: bool = False,
        llm_key_query_cap: int | None = None,
    ) -> dict[str, Any]:
        """Update organization settings.

        All parameters are optional; only supplied values are changed.

        Args:
            name: New organization display name.
            failure_mode: ``"closed"`` or ``"open_with_audit"`` (Enterprise).
            llm_api_key: Plaintext OpenAI API key — encrypted before storage.
                Setting this also resets ``llm_key_uses`` to 0.
            llm_provider: LLM provider identifier (``"openai"`` in v1).
            clear_llm_api_key: When ``True``, removes the configured LLM API key.
            llm_key_query_cap: Soft cap on queries against the org's own key.
                ``None`` removes the cap. Pass ``-1`` as a sentinel to unset.

        Returns:
            Updated organization settings dict.
        """
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if failure_mode is not None:
            body["failure_mode"] = failure_mode
        if llm_api_key is not None:
            body["llm_api_key"] = llm_api_key
        if llm_provider is not None:
            body["llm_provider"] = llm_provider
        if clear_llm_api_key:
            body["clear_llm_api_key"] = True
        if llm_key_query_cap is not None:
            body["llm_key_query_cap"] = llm_key_query_cap
        data = await self._client._request(
            "PATCH", "/api/organization/settings", json=body
        )
        return dict(data) if data else {}

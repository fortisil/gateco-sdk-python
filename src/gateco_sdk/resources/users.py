"""Users resource — current user profile (GET /me, PATCH /me)."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

"""Auth resource — login, signup, refresh, logout."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gateco_sdk.types.auth import TokenResponse

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class AuthResource:
    """Namespace for authentication endpoints.

    Accessed as ``client.auth``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def login(self, email: str, password: str) -> TokenResponse:
        """Authenticate with email and password.

        Stores the returned tokens in the client for subsequent requests.
        """
        data = await self._client._request(
            "POST",
            "/api/auth/login",
            json={"email": email, "password": password},
            authenticate=False,
        )
        token_resp = TokenResponse.model_validate(data)
        self._client._token_manager.set_tokens(
            token_resp.access_token,
            token_resp.refresh_token,
        )
        return token_resp

    async def signup(
        self,
        name: str,
        email: str,
        password: str,
        organization_name: str,
    ) -> TokenResponse:
        """Create a new account and organisation.

        Stores the returned tokens in the client for subsequent requests.
        """
        data = await self._client._request(
            "POST",
            "/api/auth/signup",
            json={
                "name": name,
                "email": email,
                "password": password,
                "organization_name": organization_name,
            },
            authenticate=False,
        )
        token_resp = TokenResponse.model_validate(data)
        self._client._token_manager.set_tokens(
            token_resp.access_token,
            token_resp.refresh_token,
        )
        return token_resp

    async def refresh(self) -> TokenResponse:
        """Refresh the current access token using the stored refresh token.

        Updates stored tokens with the new pair.
        """
        refresh_token = self._client._token_manager.refresh_token
        if refresh_token is None:
            from gateco_sdk.errors import AuthenticationError
            raise AuthenticationError("No refresh token available")

        data = await self._client._request(
            "POST",
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
            authenticate=False,
        )
        token_resp = TokenResponse.model_validate(data)
        self._client._token_manager.set_tokens(
            token_resp.access_token,
            token_resp.refresh_token,
        )
        return token_resp

    async def logout(self) -> None:
        """Invalidate the current session."""
        await self._client._request("POST", "/api/auth/logout")
        self._client._token_manager.set_tokens("", None)

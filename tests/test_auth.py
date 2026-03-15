"""Tests for authentication and token management."""

from __future__ import annotations

import time

import pytest
import respx
from httpx import Response

from gateco_sdk._auth import TokenManager
from gateco_sdk.errors import AuthenticationError
from tests.conftest import BASE_URL, make_expired_jwt, make_fresh_jwt, make_jwt


# ------------------------------------------------------------------
# TokenManager unit tests
# ------------------------------------------------------------------


class TestTokenManager:
    def test_api_key_mode_headers(self):
        tm = TokenManager(api_key="sk-test-123")
        assert tm.get_auth_headers() == {"X-API-Key": "sk-test-123"}
        assert tm.has_credentials is True
        assert tm.needs_refresh() is False

    def test_jwt_mode_headers(self):
        tm = TokenManager()
        token = make_fresh_jwt()
        tm.set_tokens(token, "refresh-abc")
        headers = tm.get_auth_headers()
        assert headers == {"Authorization": f"Bearer {token}"}
        assert tm.has_credentials is True

    def test_no_credentials(self):
        tm = TokenManager()
        assert tm.get_auth_headers() == {}
        assert tm.has_credentials is False

    def test_is_expired_with_fresh_token(self):
        tm = TokenManager()
        tm.set_tokens(make_fresh_jwt())
        assert tm.is_expired() is False

    def test_is_expired_with_expired_token(self):
        tm = TokenManager()
        tm.set_tokens(make_expired_jwt())
        assert tm.is_expired() is True

    def test_is_expired_with_no_token(self):
        tm = TokenManager()
        assert tm.is_expired() is True

    def test_needs_refresh_true_when_expired_and_refresh_available(self):
        tm = TokenManager()
        tm.set_tokens(make_expired_jwt(), "refresh-token")
        assert tm.needs_refresh() is True

    def test_needs_refresh_false_when_no_refresh_token(self):
        tm = TokenManager()
        tm.set_tokens(make_expired_jwt())
        assert tm.needs_refresh() is False

    def test_needs_refresh_false_in_api_key_mode(self):
        tm = TokenManager(api_key="key")
        assert tm.needs_refresh() is False

    def test_token_without_exp_is_not_expired(self):
        token = make_jwt(exp=None)
        tm = TokenManager()
        tm.set_tokens(token)
        assert tm.is_expired() is False

    def test_set_tokens_updates_both(self):
        tm = TokenManager()
        tm.set_tokens("access-1", "refresh-1")
        assert tm.access_token == "access-1"
        assert tm.refresh_token == "refresh-1"
        # Update only access token
        tm.set_tokens("access-2")
        assert tm.access_token == "access-2"
        assert tm.refresh_token == "refresh-1"  # unchanged


# ------------------------------------------------------------------
# Client auth flow integration tests
# ------------------------------------------------------------------


class TestClientAuth:
    @pytest.mark.asyncio
    async def test_login_stores_tokens(self, client, mock_api):
        access = make_fresh_jwt()
        mock_api.post("/api/auth/login").respond(
            200,
            json={
                "user": {"id": "u1", "name": "Alice", "email": "a@b.com"},
                "access_token": access,
                "refresh_token": "rt-1",
                "token_type": "bearer",
            },
        )
        resp = await client.login("a@b.com", "pass")
        assert resp.access_token == access
        assert client._token_manager.access_token == access
        assert client._token_manager.refresh_token == "rt-1"

    @pytest.mark.asyncio
    async def test_signup_stores_tokens(self, client, mock_api):
        access = make_fresh_jwt()
        mock_api.post("/api/auth/signup").respond(
            200,
            json={
                "user": {"id": "u2", "name": "Bob", "email": "b@c.com"},
                "access_token": access,
                "refresh_token": "rt-2",
                "token_type": "bearer",
            },
        )
        resp = await client.signup("Bob", "b@c.com", "pass", "Acme")
        assert resp.user.name == "Bob"
        assert client._token_manager.has_credentials is True

    @pytest.mark.asyncio
    async def test_logout_clears_tokens(self, authed_client, mock_api):
        mock_api.post("/api/auth/logout").respond(204)
        await authed_client.auth.logout()
        assert authed_client._token_manager.access_token == ""

    @pytest.mark.asyncio
    async def test_refresh_no_token_raises(self, client):
        with pytest.raises(AuthenticationError, match="No refresh token"):
            await client.auth.refresh()

    @pytest.mark.asyncio
    async def test_auto_refresh_on_expired_token(self, client, mock_api):
        """When the access token is expired, the client should refresh before the request."""
        new_access = make_fresh_jwt()
        client._token_manager.set_tokens(make_expired_jwt(), "rt-old")

        mock_api.post("/api/auth/refresh").respond(
            200,
            json={
                "access_token": new_access,
                "refresh_token": "rt-new",
                "token_type": "bearer",
            },
        )
        mock_api.get("/api/connectors").respond(
            200,
            json={
                "data": [],
                "meta": {"pagination": {"page": 1, "per_page": 20, "total": 0, "total_pages": 0}},
            },
        )

        page = await client.connectors.list()
        assert page.items == []
        # Verify tokens were updated
        assert client._token_manager.access_token == new_access

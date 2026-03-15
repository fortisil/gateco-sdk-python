"""Tests for error hierarchy and error-from-response mapping."""

from __future__ import annotations

import httpx
import pytest
import respx

from gateco_sdk.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    EntitlementError,
    GatecoError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    error_from_response,
)
from tests.conftest import BASE_URL, make_fresh_jwt


# ------------------------------------------------------------------
# Unit: error_from_response
# ------------------------------------------------------------------


class TestErrorFromResponse:
    def test_401_maps_to_authentication_error(self):
        err = error_from_response(
            401, {"error": {"code": "AUTH_INVALID_CREDENTIALS", "message": "bad creds"}}
        )
        assert isinstance(err, AuthenticationError)
        assert err.status_code == 401
        assert err.code == "AUTH_INVALID_CREDENTIALS"

    def test_403_permission_denied(self):
        err = error_from_response(
            403, {"error": {"code": "AUTH_PERMISSION_DENIED", "message": "forbidden"}}
        )
        assert isinstance(err, AuthorizationError)

    def test_403_entitlement_required_with_upgrade_to(self):
        err = error_from_response(
            403,
            {
                "error": {
                    "code": "ENTITLEMENT_REQUIRED",
                    "message": "upgrade needed",
                    "upgrade_to": "pro",
                }
            },
        )
        assert isinstance(err, EntitlementError)
        assert err.upgrade_to == "pro"

    def test_404_maps_to_not_found(self):
        err = error_from_response(
            404, {"error": {"code": "RESOURCE_NOT_FOUND", "message": "gone"}}
        )
        assert isinstance(err, NotFoundError)

    def test_409_maps_to_conflict(self):
        err = error_from_response(409, {"error": {"code": "CONFLICT", "message": "dup"}})
        assert isinstance(err, ConflictError)

    def test_422_maps_to_validation_error(self):
        err = error_from_response(
            422, {"error": {"code": "VALIDATION_ERROR", "message": "invalid"}}
        )
        assert isinstance(err, ValidationError)

    def test_429_maps_to_rate_limit_with_retry_after(self):
        err = error_from_response(
            429,
            {"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "slow down"}},
            retry_after=5.0,
        )
        assert isinstance(err, RateLimitError)
        assert err.retry_after == 5.0

    def test_500_maps_to_base_error(self):
        err = error_from_response(
            500, {"error": {"code": "INTERNAL_ERROR", "message": "oops"}}
        )
        assert isinstance(err, GatecoError)
        assert err.status_code == 500

    def test_unknown_status_with_no_body(self):
        err = error_from_response(502, None)
        assert isinstance(err, GatecoError)
        assert err.status_code == 502

    def test_unknown_code_falls_back_to_status(self):
        err = error_from_response(
            404, {"error": {"code": "SOMETHING_ELSE", "message": "x"}}
        )
        # Status-based fallback
        assert isinstance(err, NotFoundError)


# ------------------------------------------------------------------
# Integration: transport raises correct exception classes
# ------------------------------------------------------------------


class TestTransportErrorMapping:
    @pytest.mark.asyncio
    async def test_401_raises_authentication_error(self, authed_client, mock_api):
        mock_api.get("/api/connectors/abc").respond(
            401,
            json={"error": {"code": "AUTH_INVALID_CREDENTIALS", "message": "expired"}},
        )
        # Also mock the refresh to fail so the fallback refresh raises too
        mock_api.post("/api/auth/refresh").respond(
            401,
            json={"error": {"code": "AUTH_INVALID_CREDENTIALS", "message": "bad refresh"}},
        )
        with pytest.raises(AuthenticationError):
            await authed_client.connectors.get("abc")

    @pytest.mark.asyncio
    async def test_404_raises_not_found(self, authed_client, mock_api):
        mock_api.get("/api/connectors/missing").respond(
            404,
            json={"error": {"code": "RESOURCE_NOT_FOUND", "message": "not found"}},
        )
        with pytest.raises(NotFoundError):
            await authed_client.connectors.get("missing")

    @pytest.mark.asyncio
    async def test_422_raises_validation_error(self, authed_client, mock_api):
        mock_api.post("/api/connectors").respond(
            422,
            json={"error": {"code": "VALIDATION_ERROR", "message": "bad input"}},
        )
        with pytest.raises(ValidationError):
            await authed_client.connectors.create("x", "y")

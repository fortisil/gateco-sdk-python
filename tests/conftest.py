"""Shared fixtures for Gateco SDK tests."""

from __future__ import annotations

import base64
import json
import time

import pytest
import respx

from gateco_sdk.client import AsyncGatecoClient


BASE_URL = "http://test.gateco.local"


def make_jwt(exp: float | None = None, extra: dict | None = None) -> str:
    """Build a minimal unsigned JWT for testing token expiry logic.

    The token is NOT cryptographically valid — it only needs to be decodable
    by the SDK's ``TokenManager._decode_exp`` helper.
    """
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()

    payload_data: dict = {}
    if exp is not None:
        payload_data["exp"] = exp
    if extra:
        payload_data.update(extra)

    payload = base64.urlsafe_b64encode(
        json.dumps(payload_data).encode()
    ).rstrip(b"=").decode()

    return f"{header}.{payload}.sig"


def make_fresh_jwt() -> str:
    """Return a JWT that expires 1 hour from now."""
    return make_jwt(exp=time.time() + 3600)


def make_expired_jwt() -> str:
    """Return a JWT that expired 1 minute ago."""
    return make_jwt(exp=time.time() - 60)


@pytest.fixture()
def mock_api():
    """Activate a ``respx`` mock router scoped to ``BASE_URL``."""
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        yield router


@pytest.fixture()
async def client(mock_api):
    """Provide an ``AsyncGatecoClient`` pointed at the mock base URL."""
    async with AsyncGatecoClient(BASE_URL) as c:
        yield c


@pytest.fixture()
async def authed_client(mock_api):
    """Provide an ``AsyncGatecoClient`` with a pre-set valid token."""
    async with AsyncGatecoClient(BASE_URL) as c:
        c._token_manager.set_tokens(make_fresh_jwt(), "refresh-token-value")
        yield c

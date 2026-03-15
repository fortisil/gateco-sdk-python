"""Token management for the Gateco SDK.

Supports both JWT-based auth (login/signup flow with refresh) and static
API-key auth.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import Any


_EXPIRY_BUFFER_SECONDS = 30


class TokenManager:
    """Manages access and refresh tokens for authenticated API requests.

    In *api_key* mode the manager produces a static ``X-API-Key`` header and
    never attempts token refresh.  In *jwt* mode (populated via
    :pymethod:`set_tokens`) it decodes the JWT ``exp`` claim to decide when a
    refresh is needed.

    Args:
        api_key: Optional static API key.  When provided the manager operates
            in api-key mode and ignores JWT tokens.
    """

    def __init__(self, *, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Token storage
    # ------------------------------------------------------------------

    def set_tokens(self, access_token: str, refresh_token: str | None = None) -> None:
        """Store a fresh pair of JWT tokens."""
        self._access_token = access_token
        if refresh_token is not None:
            self._refresh_token = refresh_token

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    @property
    def has_credentials(self) -> bool:
        """Return ``True`` if any form of credential is available."""
        return self._api_key is not None or self._access_token is not None

    # ------------------------------------------------------------------
    # Expiry helpers
    # ------------------------------------------------------------------

    def is_expired(self) -> bool:
        """Return ``True`` if the current access token is expired (with buffer)."""
        if self._access_token is None:
            return True
        exp = self._decode_exp(self._access_token)
        if exp is None:
            return False  # cannot determine; assume valid
        return time.time() >= (exp - _EXPIRY_BUFFER_SECONDS)

    def needs_refresh(self) -> bool:
        """Return ``True`` if the access token should be refreshed.

        This is ``True`` when we are in JWT mode, the token is expired (or
        about to expire), and a refresh token is available.
        """
        if self._api_key is not None:
            return False
        if self._refresh_token is None:
            return False
        return self.is_expired()

    # ------------------------------------------------------------------
    # Header generation
    # ------------------------------------------------------------------

    def get_auth_headers(self) -> dict[str, str]:
        """Build the authentication headers for the next request.

        Returns:
            A dict with either an ``Authorization`` bearer header or an
            ``X-API-Key`` header, or an empty dict if no credentials are set.
        """
        if self._api_key is not None:
            return {"X-API-Key": self._api_key}
        if self._access_token is not None:
            return {"Authorization": f"Bearer {self._access_token}"}
        return {}

    # ------------------------------------------------------------------
    # Concurrency guard
    # ------------------------------------------------------------------

    @property
    def lock(self) -> asyncio.Lock:
        """Lock used to prevent concurrent refresh calls."""
        return self._lock

    # ------------------------------------------------------------------
    # JWT decoding (minimal, no verification)
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_exp(token: str) -> float | None:
        """Extract the ``exp`` claim from a JWT **without** verifying the signature."""
        try:
            parts = token.split(".")
            if len(parts) < 2:
                return None
            # Add padding
            payload_b64 = parts[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload: dict[str, Any] = json.loads(payload_bytes)
            exp = payload.get("exp")
            return float(exp) if exp is not None else None
        except Exception:
            return None

"""Low-level HTTP transport layer built on httpx.

Handles JSON serialisation, error mapping, retries (429 + 5xx), and
``Retry-After`` back-off.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from gateco_sdk.errors import GatecoError, RateLimitError, error_from_response


_DEFAULT_TIMEOUT = 30.0
_DEFAULT_MAX_RETRIES = 2
_DEFAULT_BACKOFF_FACTOR = 0.5


class Transport:
    """Async HTTP transport that wraps :class:`httpx.AsyncClient`.

    Args:
        base_url: Root URL of the Gateco API (e.g. ``https://api.gateco.dev``).
        timeout: Request timeout in seconds.
        max_retries: Maximum number of automatic retries for 429 / 5xx responses.
        retry_backoff_factor: Multiplier for exponential back-off between retries.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        retry_backoff_factor: float = _DEFAULT_BACKOFF_FACTOR,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Core request method
    # ------------------------------------------------------------------

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Send an HTTP request and return the parsed JSON body.

        Automatically retries on ``429`` (respecting ``Retry-After``) and ``5xx``
        responses up to *max_retries* times with exponential back-off.

        Args:
            method: HTTP method (``GET``, ``POST``, etc.).
            path: URL path (will be joined to *base_url*).
            json: JSON-serialisable request body.
            params: Query parameters.
            headers: Extra headers merged with defaults.

        Returns:
            Parsed JSON response body, or ``None`` for ``204 No Content``.

        Raises:
            GatecoError: (or a subclass) when the API returns an error response.
        """
        client = await self._get_client()
        last_exc: GatecoError | None = None

        for attempt in range(1 + self.max_retries):
            try:
                response = await client.request(
                    method,
                    path,
                    json=json,
                    params=self._clean_params(params),
                    headers=headers or {},
                )
            except httpx.HTTPError as exc:
                raise GatecoError(
                    f"HTTP transport error: {exc}",
                    code="TRANSPORT_ERROR",
                    status_code=0,
                ) from exc

            # Success --------------------------------------------------
            if response.status_code == 204:
                return None
            if 200 <= response.status_code < 300:
                return response.json()  # type: ignore[no-any-return]

            # Parse error body -----------------------------------------
            retry_after = self._parse_retry_after(response)
            try:
                body = response.json()
            except Exception:
                body = None

            last_exc = error_from_response(
                response.status_code, body, retry_after=retry_after
            )

            # Retryable? -----------------------------------------------
            is_last = attempt >= self.max_retries
            if isinstance(last_exc, RateLimitError) and not is_last:
                wait = retry_after if retry_after is not None else self._backoff(attempt)
                await asyncio.sleep(wait)
                continue
            if 500 <= response.status_code < 600 and not is_last:
                await asyncio.sleep(self._backoff(attempt))
                continue

            # Not retryable or retries exhausted
            raise last_exc

        # Should be unreachable, but satisfy the type checker.
        assert last_exc is not None
        raise last_exc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _backoff(self, attempt: int) -> float:
        """Exponential back-off: factor * 2^attempt."""
        return self.retry_backoff_factor * (2 ** attempt)

    @staticmethod
    def _parse_retry_after(response: httpx.Response) -> float | None:
        raw = response.headers.get("Retry-After") or response.headers.get("retry-after")
        if raw is None:
            return None
        try:
            return float(raw)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _clean_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
        """Strip ``None`` values so they are not sent as query params."""
        if params is None:
            return None
        return {k: v for k, v in params.items() if v is not None}

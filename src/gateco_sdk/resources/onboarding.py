"""Onboarding resource — status and dismissal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class OnboardingResource:
    """Namespace for onboarding endpoints.

    Accessed as ``client.onboarding``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    async def status(self) -> dict[str, Any]:
        """Fetch the computed onboarding status for the current organisation.

        Returns a dict with 6 onboarding steps, each carrying ``status``
        (``not_started`` / ``in_progress`` / ``completed``), ``evidence_count``,
        ``blocking_reason``, and ``cta_target``.

        Returns:
            Onboarding status payload including step details and overall progress.
        """
        data = await self._client._request("GET", "/api/onboarding/status")
        return data or {}

    async def dismiss(self) -> dict[str, Any]:
        """Dismiss the onboarding checklist for the current organisation.

        Sets ``onboarding_dismissed_at`` on the organisation record. The
        checklist will no longer appear on the dashboard after this call.

        Returns:
            Confirmation payload from the server.
        """
        data = await self._client._request("POST", "/api/onboarding/dismiss", json={})
        return data or {}

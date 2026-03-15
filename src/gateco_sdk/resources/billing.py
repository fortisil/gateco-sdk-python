"""Billing resource — plans, usage, invoices, subscriptions, checkout, portal."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk._pagination import AsyncPaginator, Page
from gateco_sdk.types.billing import (
    CheckoutResponse,
    Invoice,
    Plan,
    Subscription,
    Usage,
)

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class BillingResource:
    """Namespace for billing endpoints.

    Accessed as ``client.billing``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Plans (public)
    # ------------------------------------------------------------------

    async def get_plans(self) -> list[Plan]:
        """List all available plans (public, no auth required)."""
        raw = await self._client._request(
            "GET", "/api/plans", authenticate=False
        )
        plans_raw = raw.get("plans", []) if raw else []
        return [Plan.model_validate(p) for p in plans_raw]

    # ------------------------------------------------------------------
    # Usage
    # ------------------------------------------------------------------

    async def get_usage(self) -> Usage:
        """Get current billing period usage for the authenticated organization."""
        data = await self._client._request("GET", "/api/billing/usage")
        return Usage.model_validate(data)

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------

    async def get_invoices(
        self, page: int = 1, per_page: int = 20
    ) -> Page[Invoice]:
        """Fetch a page of invoices."""
        raw = await self._client._request(
            "GET",
            "/api/billing/invoices",
            params={"page": page, "per_page": per_page},
        )
        items_raw = raw.get("data", []) if raw else []
        meta = (raw or {}).get("meta", {}).get("pagination", {})
        items = [Invoice.model_validate(i) for i in items_raw]
        return Page[Invoice](
            items=items,
            page=meta.get("page", page),
            per_page=meta.get("per_page", per_page),
            total=meta.get("total", len(items)),
            total_pages=meta.get("total_pages", 1),
        )

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------

    async def get_subscription(self) -> Subscription | None:
        """Get the current subscription for the authenticated organization."""
        data = await self._client._request("GET", "/api/billing/subscription")
        if data is None:
            return None
        return Subscription.model_validate(data)

    # ------------------------------------------------------------------
    # Checkout
    # ------------------------------------------------------------------

    async def start_checkout(
        self,
        plan_id: str,
        billing_period: str = "monthly",
    ) -> CheckoutResponse:
        """Create a Stripe Checkout Session for plan upgrade."""
        data = await self._client._request(
            "POST",
            "/api/checkout/start",
            json={"plan_id": plan_id, "billing_period": billing_period},
        )
        return CheckoutResponse.model_validate(data)

    # ------------------------------------------------------------------
    # Billing Portal
    # ------------------------------------------------------------------

    async def create_portal(
        self, return_url: str | None = None
    ) -> dict[str, Any]:
        """Create a Stripe Billing Portal session."""
        body: dict[str, Any] = {}
        if return_url is not None:
            body["return_url"] = return_url
        data = await self._client._request(
            "POST", "/api/billing/portal", json=body
        )
        return data or {}

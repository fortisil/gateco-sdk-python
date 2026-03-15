"""Types for billing endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PlanLimits(BaseModel):
    """Numeric limits for a plan tier."""

    secured_retrievals: int | None = None
    connectors: int | None = None
    policies: int | None = None
    identity_providers: int | None = None


class PlanFeatures(BaseModel):
    """Feature flags for a plan tier."""

    policy_studio: bool = False
    audit_export: bool = False
    access_simulator: bool = False
    custom_roles: bool = False
    sso: bool = False


class Plan(BaseModel):
    """A billing plan."""

    id: str
    name: str
    description: str | None = None
    price_monthly_cents: int = 0
    price_yearly_cents: int = 0
    limits: PlanLimits | None = None
    features: PlanFeatures | None = None
    stripe_price_id_monthly: str | None = None
    stripe_price_id_yearly: str | None = None


class UsageMetric(BaseModel):
    """A single usage metric with used/limit."""

    used: int = 0
    limit: int | None = None
    overage: int | None = None


class Usage(BaseModel):
    """Current billing period usage."""

    period_start: str | None = None
    period_end: str | None = None
    secured_retrievals: UsageMetric | None = None
    connectors: UsageMetric | None = None
    policies: UsageMetric | None = None
    estimated_overage_cents: int = 0


class Invoice(BaseModel):
    """A billing invoice."""

    id: str
    stripe_invoice_id: str | None = None
    amount_cents: int = 0
    currency: str = "usd"
    status: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    pdf_url: str | None = None
    created_at: str | None = None


class Subscription(BaseModel):
    """An active subscription."""

    id: str
    plan_id: str
    status: str
    current_period_start: str | None = None
    current_period_end: str | None = None
    cancel_at_period_end: bool = False


class CheckoutRequest(BaseModel):
    """Request body for ``POST /api/checkout/start``."""

    plan_id: str
    billing_period: str = "monthly"


class CheckoutResponse(BaseModel):
    """Response from ``POST /api/checkout/start``."""

    checkout_url: str
    session_id: str

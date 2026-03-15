"""Types for dashboard endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """Aggregated dashboard statistics."""

    retrievals_today: int = 0
    retrievals_allowed: int = 0
    retrievals_denied: int = 0
    connectors_connected: int = 0
    connectors_error: int = 0
    idps_connected: int = 0
    idps_principal_count: int = 0
    last_idp_sync: str | None = None
    recent_denied: list[dict[str, Any]] = []
    total_bound_vectors: int = 0
    total_vectors: int = 0
    overall_coverage_pct: float | None = None
    connectors_policy_ready: int = 0

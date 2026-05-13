"""Types for dashboard endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class DashboardSparklines(BaseModel):
    """Time-series data for dashboard KPI sparklines.

    All arrays are zero-filled server-side to exact lengths.

    - retrievals_24h: 24 hourly buckets ending at the current hour (UTC).
    - denied_24h: 24 hourly buckets aligned to retrievals_24h; denied outcomes only.
    - principals_7d: 7 daily buckets ending today; active principals by last_seen.
    - coverage_7d: v1 flat line of current coverage value (no snapshot table yet).
    """

    retrievals_24h: list[int]
    denied_24h: list[int]
    principals_7d: list[int]
    coverage_7d: list[float]


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
    sparklines: DashboardSparklines | None = None

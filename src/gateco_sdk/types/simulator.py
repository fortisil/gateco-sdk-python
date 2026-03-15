"""Types for access simulator endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SimulationRequest(BaseModel):
    """Request body for ``POST /api/simulator/run``."""

    principal_id: str
    query: str | None = None
    connector_id: str | None = None
    resource_ids: list[str] | None = None


class SimulationResult(BaseModel):
    """Response from ``POST /api/simulator/run``."""

    outcome: str
    matched_resources: int = 0
    allowed: int = 0
    denied: int = 0
    policy_trace: list[dict[str, Any]] = []
    denial_reasons: list[str] = []

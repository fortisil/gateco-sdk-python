"""Types for retrieval endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DenialReason(BaseModel):
    """Reason a retrieval result was denied."""

    code: str
    message: str | None = None
    policy_id: str | None = None


class PolicyTrace(BaseModel):
    """Trace of a policy evaluation during retrieval."""

    policy_id: str
    policy_name: str | None = None
    decision: str
    reason: str | None = None
    duration_ms: float | None = None


class RetrievalOutcome(BaseModel):
    """A single result item within a retrieval response."""

    resource_id: str
    external_resource_id: str | None = None
    score: float | None = None
    granted: bool = False
    denial_reason: DenialReason | None = None
    policy_traces: list[PolicyTrace] = []
    metadata: dict[str, Any] = {}
    text: str | None = None


class ExecuteRetrievalRequest(BaseModel):
    """Request body for ``POST /api/retrievals/execute``."""

    query_vector: list[float] | None = None
    query: str | None = None
    principal_id: str
    connector_id: str
    top_k: int | None = None
    filters: dict[str, Any] | None = None
    include_unresolved: bool | None = None


class SecuredRetrieval(BaseModel):
    """Full retrieval record returned by list / get / execute endpoints."""

    model_config = {"extra": "allow"}

    id: str | None = None
    retrieval_id: str | None = None
    query: str | None = None
    outcome: str | None = None
    principal_id: str | None = None
    connector_id: str | None = None
    organization_id: str | None = None
    status: str | None = None
    matched_chunks: int = 0
    allowed_chunks: int = 0
    denied_chunks: int = 0
    unresolved_chunks: int = 0
    total_results: int = 0
    granted_count: int = 0
    denied_count: int = 0
    outcomes: list[RetrievalOutcome] = []
    results: list[dict[str, Any]] = []
    denial_reasons: list[str] = []
    policy_trace: list[dict[str, Any]] = []
    warnings: list[str] = []
    created_at: datetime | None = None
    duration_ms: float | None = None
    latency_ms: float | None = None
    connector_latency_ms: float | None = None
    metadata: dict[str, Any] = {}

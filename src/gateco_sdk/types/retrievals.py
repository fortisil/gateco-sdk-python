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


class FilterResult(BaseModel):
    """A single result item within a retrieval response.

    For filter endpoint results, ``resource_mode`` and ``policy_decision``
    are populated.  For execute endpoint results, ``metadata`` and
    ``external_resource_id`` are populated instead.  Extra fields from
    either endpoint are preserved.
    """

    model_config = {"extra": "allow"}

    vector_id: str = ""
    score: float | None = None
    text: str | None = None
    resource_id: str | None = None
    resource_mode: str | None = None  # "registered" | "synthetic" | "unresolved"
    granted: bool = False
    policy_decision: str | None = None  # "allowed" | "denied"
    denial_reason: str | None = None
    metadata: dict[str, Any] | None = None
    external_resource_id: str | None = None

    # Dict-like access for backwards compatibility with code that treats
    # results as plain dicts (e.g., r.get("granted"), r["metadata"]).
    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        # Check extra fields stored by pydantic
        extra = self.__pydantic_extra__ or {}
        if key in extra:
            return extra[key]
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        if hasattr(self, key):
            return True
        extra = self.__pydantic_extra__ or {}
        return key in extra


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
    results: list[FilterResult] = []
    denial_reasons: list[str] = []
    policy_trace: list[dict[str, Any]] = []
    warnings: list[str] = []
    created_at: datetime | None = None
    duration_ms: float | None = None
    latency_ms: float | None = None
    connector_latency_ms: float | None = None
    metadata: dict[str, Any] = {}

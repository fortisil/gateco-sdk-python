"""Types for answer synthesis endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class Citation(BaseModel):
    """A single citation linking answer text to a source chunk."""

    index: int
    resource_id: str | None = None
    vector_id: str = ""
    text_excerpt: str = ""
    score: float | None = None


class RetrievalDiagnostics(BaseModel):
    """Diagnostics explaining a retrieval outcome."""

    model_config = {"extra": "allow"}

    candidates_fetched: int = 0
    candidates_allowed: int = 0
    candidates_denied: int = 0
    refill_rounds: int = 0
    policies_evaluated: int = 0
    active_denial_reasons: list[str] = []
    metadata_resolution_mode: str | None = None
    readiness_level: int | None = None
    outcome_detail: str = ""


class Answer(BaseModel):
    """Response from the answer synthesis endpoint."""

    model_config = {"extra": "allow"}

    answer: str | None = None
    outcome: str = ""  # "answered" | "no_access" | "insufficient_context"
    is_partial: bool = False
    citations: list[Citation] = []
    retrieval_id: str | None = None
    allowed_chunks: int = 0
    denied_chunks: int = 0
    model: str | None = None
    retrieval_latency_ms: int | None = None
    synthesis_latency_ms: int | None = None
    total_latency_ms: int | None = None
    chunks_available: int = 0
    chunks_used_initial: int = 0
    chunks_used_final: int = 0
    retry_used: bool = False
    cap_reached: bool = False
    diagnostics: RetrievalDiagnostics | None = None

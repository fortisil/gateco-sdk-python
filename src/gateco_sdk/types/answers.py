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

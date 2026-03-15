"""Types for pipeline endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EnvelopeConfig(BaseModel):
    """Envelope configuration for a pipeline."""

    format: str | None = None
    fields: dict[str, Any] = {}


class Pipeline(BaseModel):
    """A pipeline resource."""

    id: str
    name: str
    source_connector_id: str
    envelope_config: dict[str, Any] | None = None
    status: str | None = None
    schedule: str = "manual"
    last_run: str | None = None
    records_processed: int = 0
    error_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class PipelineRun(BaseModel):
    """A single pipeline run record."""

    id: str
    pipeline_id: str
    status: str
    records_processed: int = 0
    errors: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None


class CreatePipelineRequest(BaseModel):
    """Request body for ``POST /api/pipelines``."""

    name: str
    source_connector_id: str
    envelope_config: dict[str, Any] | None = None
    schedule: str = "manual"

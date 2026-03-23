"""Types for ingestion endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PreEmbeddedChunk(BaseModel):
    """A pre-embedded chunk for direct vector storage."""

    text: str
    vector: list[float]
    metadata: dict[str, Any] | None = None


class IngestDocumentRequest(BaseModel):
    """Request body for ``POST /api/v1/ingest``."""

    connector_id: str
    external_resource_id: str
    text: str
    classification: str | None = None
    sensitivity: str | None = None
    domain: str | None = None
    labels: list[str] | None = None
    metadata: dict[str, Any] | None = None
    owner_principal_id: str | None = None
    idempotency_key: str | None = None


class IngestDocumentResponse(BaseModel):
    """Response from ``POST /api/v1/ingest``."""

    status: str
    resource_id: str
    external_resource_id: str
    chunk_count: int = 0
    vector_ids: list[str] = []


class BatchIngestRequest(BaseModel):
    """Request body for ``POST /api/v1/ingest/batch``."""

    connector_id: str
    records: list[dict[str, Any]]
    idempotency_key: str | None = None


class BatchIngestResponse(BaseModel):
    """Response from ``POST /api/v1/ingest/batch``."""

    status: str
    succeeded: int = 0
    failed: int = 0
    results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []


# ── File ingestion types ──


class IngestFileResponse(BaseModel):
    """Response from ``POST /api/v1/ingest/file``."""

    status: str
    resource_id: str
    external_resource_id: str
    chunk_count: int = 0
    vector_ids: list[str] = []
    source_filename: str = ""
    source_mime_type: str = ""
    extracted_chars: int = 0
    extractor_used: str = ""
    content_hash: str = ""
    warnings: list[str] = []


class BatchFileIngestResultItem(BaseModel):
    """Per-file result in a batch file ingestion."""

    filename: str
    external_resource_id: str
    status: str  # "ingested" | "skipped" | "failed"
    resource_id: str | None = None
    extracted_chars: int = 0
    chunk_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    warnings: list[str] = []


class BatchFileIngestResponse(BaseModel):
    """Response from ``POST /api/v1/ingest/files``."""

    status: str
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[BatchFileIngestResultItem] = []

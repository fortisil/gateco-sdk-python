"""Types for connector endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Any

from pydantic import BaseModel


class PolicyReadinessLevel(IntEnum):
    """Semantic policy readiness levels (L0-L4)."""

    not_ready = 0
    connection_ready = 1
    search_ready = 2
    resource_policy = 3
    chunk_policy = 4


class Connector(BaseModel):
    """A configured connector instance."""

    id: str
    name: str
    type: str
    config: dict[str, Any] = {}
    status: str | None = None
    organization_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata_resolution_mode: str | None = None
    policy_readiness_level: int | None = None
    connection_ready: bool | None = None
    search_ready: bool | None = None
    bound_vector_count: int | None = None
    coverage_pct: float | None = None


class CreateConnectorRequest(BaseModel):
    """Request body for ``POST /api/connectors``."""

    name: str
    type: str
    config: dict[str, Any] = {}
    metadata_resolution_mode: str | None = None


class TestConnectorResponse(BaseModel):
    """Response from ``POST /api/connectors/{id}/test``."""

    model_config = {"extra": "allow"}

    success: bool
    health_status: str | None = None
    authenticated: bool = False
    schema_discovered: bool = False
    vector_ready: bool = False
    server_version: str | None = None
    resources: list[Any] = []
    total_records: int | None = None
    error: str | None = None
    latency_ms: float | None = None
    warnings: list[str] = []


class SearchConfig(BaseModel):
    """Search configuration for a connector."""

    top_k: int | None = None
    similarity_threshold: float | None = None
    filters: dict[str, Any] | None = None
    extra: dict[str, Any] = {}


class IngestionConfig(BaseModel):
    """Ingestion configuration for a connector."""

    chunk_size: int | None = None
    chunk_overlap: int | None = None
    embedding_model: str | None = None
    extra: dict[str, Any] = {}


class BindingEntry(BaseModel):
    """A single binding entry for ``POST /api/connectors/{id}/bind``."""

    vector_id: str
    external_resource_id: str
    metadata: dict[str, Any] | None = None


class BindResult(BaseModel):
    """Response from ``POST /api/connectors/{id}/bind``."""

    status: str
    bound: int = 0
    errors: list[dict[str, Any]] = []


class CoverageDetail(BaseModel):
    """Response from ``GET /api/connectors/{id}/coverage``."""

    total_resources: int = 0
    bound_resources: int = 0
    unbound_resources: int = 0
    coverage_percent: float = 0.0
    details: list[dict[str, Any]] = []


class ClassificationSuggestion(BaseModel):
    """A single classification suggestion for a resource group."""

    resource_key: str
    vector_ids: list[str] = []
    suggested_classification: str | None = None
    suggested_sensitivity: str | None = None
    suggested_domain: str | None = None
    confidence: float = 0.0
    reasoning: str | None = None


class SuggestClassificationsResponse(BaseModel):
    """Response from ``POST /api/connectors/{id}/suggest-classifications``."""

    status: str
    scanned_vectors: int = 0
    suggestions: list[ClassificationSuggestion] = []


class ApplySuggestionsResponse(BaseModel):
    """Response from ``POST /api/connectors/{id}/apply-suggestions``."""

    status: str
    applied: int = 0
    resources_created: int = 0
    errors: list[dict[str, Any]] = []

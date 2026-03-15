"""Types for data catalog endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class DataCatalogFilters(BaseModel):
    """Filters for data catalog list queries."""

    classification: str | None = None
    sensitivity: str | None = None
    domain: str | None = None
    label: str | None = None
    source_connector_id: str | None = None


class ResourceChunk(BaseModel):
    """A chunk belonging to a gated resource."""

    id: str | None = None
    vector_id: str | None = None
    content_preview: str | None = None
    metadata: dict[str, Any] = {}


class GatedResource(BaseModel):
    """A gated resource in the data catalog."""

    id: str
    title: str
    description: str | None = None
    type: str | None = None
    classification: str | None = None
    sensitivity: str | None = None
    domain: str | None = None
    labels: list[str] | None = None
    encryption_mode: str | None = None
    source_connector_id: str | None = None
    view_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class GatedResourceDetail(GatedResource):
    """Extended resource detail including chunks, policies, and access history."""

    chunks: list[dict[str, Any]] = []
    applicable_policies: list[dict[str, Any]] = []
    recent_access: list[dict[str, Any]] = []

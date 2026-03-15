"""Types for retroactive registration endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RetroactiveRegisterRequest(BaseModel):
    """Request body for ``POST /api/v1/retroactive-register``."""

    connector_id: str
    scan_limit: int = 1000
    default_classification: str | None = None
    default_sensitivity: str | None = None
    default_domain: str | None = None
    default_labels: list[str] | None = None
    grouping_strategy: str = "individual"
    grouping_pattern: str | None = None
    dry_run: bool = False


class RetroactiveRegisterResponse(BaseModel):
    """Response from ``POST /api/v1/retroactive-register``."""

    status: str
    scanned_vectors: int = 0
    already_registered: int = 0
    newly_registered: int = 0
    resources_created: int = 0
    errors: list[dict[str, Any]] = []

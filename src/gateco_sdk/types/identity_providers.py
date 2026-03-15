"""Types for identity provider endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SyncConfig(BaseModel):
    """Sync configuration for an identity provider."""

    schedule: str | None = None
    scope: str | None = None
    filters: dict[str, Any] | None = None


class IdentityProvider(BaseModel):
    """An identity provider resource."""

    id: str
    name: str
    type: str
    status: str
    config: dict[str, Any] = {}
    sync_config: dict[str, Any] | None = None
    principal_count: int = 0
    group_count: int = 0
    last_sync: str | None = None
    error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CreateIdentityProviderRequest(BaseModel):
    """Request body for ``POST /api/identity-providers``."""

    name: str
    type: str
    config: dict[str, Any] = {}
    sync_config: dict[str, Any] | None = None

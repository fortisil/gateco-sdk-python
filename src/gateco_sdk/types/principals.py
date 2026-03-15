"""Types for principal endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PrincipalAttributes(BaseModel):
    """Arbitrary attributes attached to a principal."""

    department: str | None = None
    location: str | None = None
    clearance_level: str | None = None
    extra: dict[str, Any] = {}


class Principal(BaseModel):
    """An identity principal resource."""

    id: str
    identity_provider_id: str | None = None
    identity_provider_name: str | None = None
    external_id: str | None = None
    display_name: str | None = None
    email: str | None = None
    groups: list[str] = []
    roles: list[str] = []
    attributes: dict[str, Any] = {}
    status: str | None = None
    last_seen: str | None = None
    created_at: str | None = None

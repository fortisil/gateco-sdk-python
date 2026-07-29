"""Types for principal endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator


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
    provider_subject: str | None = None
    display_name: str | None = None
    email: str | None = None
    groups: list[str] = []
    roles: list[str] = []
    attributes: dict[str, Any] = {}
    status: str | None = None

    @field_validator("attributes", mode="before")
    @classmethod
    def _coerce_attributes(cls, v: Any) -> dict[str, Any]:
        return v if v is not None else {}
    last_seen: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

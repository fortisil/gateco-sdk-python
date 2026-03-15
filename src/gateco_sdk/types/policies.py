"""Types for policy endpoints."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class PolicyType(str, Enum):
    """Access policy types."""

    rbac = "rbac"
    abac = "abac"
    rebac = "rebac"


class PolicyStatus(str, Enum):
    """Policy lifecycle status."""

    draft = "draft"
    active = "active"
    archived = "archived"


class PolicyEffect(str, Enum):
    """Policy evaluation effect."""

    allow = "allow"
    deny = "deny"


class PolicyCondition(BaseModel):
    """A single condition within a policy rule."""

    field: str | None = None
    operator: str | None = None
    value: Any = None


class PolicyRule(BaseModel):
    """A rule within a policy."""

    id: str | None = None
    description: str | None = None
    effect: str
    conditions: list[dict[str, Any]] | None = None
    priority: int = 0


class Policy(BaseModel):
    """A policy resource."""

    id: str
    name: str
    description: str | None = None
    type: str
    status: str
    effect: str
    resource_selectors: list[dict[str, Any]] | None = None
    version: int = 1
    rules: list[PolicyRule] = []
    created_by: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CreatePolicyRequest(BaseModel):
    """Request body for ``POST /api/policies``."""

    name: str
    description: str | None = None
    type: str
    effect: str
    resource_selectors: list[dict[str, Any]] | None = None
    rules: list[dict[str, Any]] = []

"""Types for authentication endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Request body for ``POST /api/auth/login``."""

    email: str
    password: str


class SignupRequest(BaseModel):
    """Request body for ``POST /api/auth/signup``."""

    name: str
    email: str
    password: str
    organization_name: str


class Organization(BaseModel):
    """Organization summary embedded in user responses."""

    id: str
    name: str
    slug: str | None = None


class User(BaseModel):
    """Authenticated user profile."""

    id: str
    name: str
    email: str
    role: str | None = None
    organization_id: str | None = None
    organization: Organization | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TokenResponse(BaseModel):
    """Response from login / signup / refresh endpoints."""

    user: User | None = None
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"

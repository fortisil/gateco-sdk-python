"""Types for group endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class PrincipalGroup(BaseModel):
    """A group synced or pushed from an identity provider.

    ``member_count`` is computed live by the server from active principals'
    group memberships; it is not the denormalized stored counter.
    """

    id: str
    name: str | None = None
    identity_provider_id: str | None = None
    identity_provider_name: str | None = None
    external_id: str | None = None
    member_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None

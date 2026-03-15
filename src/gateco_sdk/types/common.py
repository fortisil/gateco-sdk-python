"""Shared types used across multiple API domains."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata returned by list endpoints."""

    page: int
    per_page: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope for paginated list responses.

    The backend returns ``{ data: [...], meta: { pagination: {...} } }``.
    """

    data: list[Any]
    meta: dict[str, Any] = {}

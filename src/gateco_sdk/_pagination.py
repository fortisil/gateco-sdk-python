"""Pagination helpers for list endpoints."""

from __future__ import annotations

from typing import Any, AsyncIterator, Awaitable, Callable, Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """A single page of results from a paginated API endpoint.

    Attributes:
        items: The list of items on this page.
        page: Current page number (1-based).
        per_page: Maximum items per page.
        total: Total number of items across all pages.
        total_pages: Total number of pages.
    """

    items: list[T]
    page: int
    per_page: int
    total: int
    total_pages: int


# Type alias for the fetch callback used by AsyncPaginator.
FetchFn = Callable[[int, int], Awaitable[dict[str, Any]]]


class AsyncPaginator(Generic[T]):
    """Lazily yields all items across every page of a paginated endpoint.

    Usage::

        async for connector in client.connectors.list_all():
            print(connector.name)

    Args:
        fetch: Async callable ``(page, per_page) -> raw API response dict``.
        model: Pydantic model class used to parse each item.
        per_page: Number of items to request per page.
    """

    def __init__(
        self,
        fetch: FetchFn,
        model: type[T],
        per_page: int = 100,
    ) -> None:
        self._fetch = fetch
        self._model = model
        self._per_page = per_page

    def __aiter__(self) -> AsyncIterator[T]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[T]:  # type: ignore[override]
        page = 1
        while True:
            raw = await self._fetch(page, self._per_page)

            # Extract items from envelope: {data: [...], meta: {pagination: {...}}}
            items_raw: list[dict[str, Any]] = raw.get("data", [])
            for item_data in items_raw:
                yield self._model.model_validate(item_data)  # type: ignore[arg-type]

            # Determine if there are more pages.
            meta = raw.get("meta", {})
            pagination = meta.get("pagination", {})
            total_pages = pagination.get("total_pages", 1)

            if page >= total_pages or not items_raw:
                break
            page += 1

    async def collect(self) -> list[T]:
        """Eagerly fetch all pages and return a flat list of items."""
        results: list[T] = []
        async for item in self:
            results.append(item)
        return results

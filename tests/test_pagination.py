"""Tests for pagination helpers."""

from __future__ import annotations

from typing import Any

import pytest

from gateco_sdk._pagination import AsyncPaginator, Page
from gateco_sdk.types.connectors import Connector
from tests.conftest import BASE_URL, make_fresh_jwt


class TestPage:
    def test_page_model(self):
        page = Page[Connector](
            items=[
                Connector(id="c1", name="A", type="slack"),
                Connector(id="c2", name="B", type="github"),
            ],
            page=1,
            per_page=10,
            total=2,
            total_pages=1,
        )
        assert len(page.items) == 2
        assert page.total_pages == 1


class TestAsyncPaginator:
    @pytest.mark.asyncio
    async def test_single_page(self):
        """Paginator yields all items from a single-page response."""

        async def fetch(page: int, per_page: int) -> dict[str, Any]:
            return {
                "data": [
                    {"id": "c1", "name": "A", "type": "slack"},
                    {"id": "c2", "name": "B", "type": "github"},
                ],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "per_page": per_page,
                        "total": 2,
                        "total_pages": 1,
                    }
                },
            }

        paginator = AsyncPaginator[Connector](fetch, Connector, per_page=10)
        items = await paginator.collect()
        assert len(items) == 2
        assert all(isinstance(c, Connector) for c in items)

    @pytest.mark.asyncio
    async def test_multiple_pages(self):
        """Paginator fetches subsequent pages until exhausted."""

        pages_data: dict[int, list[dict[str, Any]]] = {
            1: [{"id": "c1", "name": "A", "type": "s"}],
            2: [{"id": "c2", "name": "B", "type": "s"}],
            3: [{"id": "c3", "name": "C", "type": "s"}],
        }

        async def fetch(page: int, per_page: int) -> dict[str, Any]:
            return {
                "data": pages_data.get(page, []),
                "meta": {
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": 3,
                        "total_pages": 3,
                    }
                },
            }

        paginator = AsyncPaginator[Connector](fetch, Connector, per_page=1)
        items = await paginator.collect()
        assert len(items) == 3
        assert [c.id for c in items] == ["c1", "c2", "c3"]

    @pytest.mark.asyncio
    async def test_empty_response(self):
        """Paginator handles zero results gracefully."""

        async def fetch(page: int, per_page: int) -> dict[str, Any]:
            return {
                "data": [],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "per_page": per_page,
                        "total": 0,
                        "total_pages": 0,
                    }
                },
            }

        paginator = AsyncPaginator[Connector](fetch, Connector)
        items = await paginator.collect()
        assert items == []

    @pytest.mark.asyncio
    async def test_async_for_iteration(self):
        """Paginator works with ``async for`` syntax."""

        async def fetch(page: int, per_page: int) -> dict[str, Any]:
            return {
                "data": [{"id": f"c{page}", "name": f"N{page}", "type": "x"}],
                "meta": {
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": 2,
                        "total_pages": 2,
                    }
                },
            }

        ids: list[str] = []
        async for connector in AsyncPaginator[Connector](fetch, Connector, per_page=1):
            ids.append(connector.id)

        assert ids == ["c1", "c2"]


class TestConnectorsListAll:
    @pytest.mark.asyncio
    async def test_list_all_via_client(self, authed_client, mock_api):
        """Integration test: ``connectors.list_all()`` paginates correctly."""
        mock_api.get("/api/connectors").respond(
            200,
            json={
                "data": [{"id": "c1", "name": "Only", "type": "s"}],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "per_page": 100,
                        "total": 1,
                        "total_pages": 1,
                    }
                },
            },
        )
        items = await authed_client.connectors.list_all().collect()
        assert len(items) == 1
        assert items[0].id == "c1"

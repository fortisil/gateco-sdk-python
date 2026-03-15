"""Tests for ConnectorsResource — CRUD, test, bind, config, coverage."""

from __future__ import annotations

import pytest
import respx

from gateco_sdk.types.connectors import (
    BindResult,
    Connector,
    CoverageDetail,
    TestConnectorResponse,
)
from tests.conftest import BASE_URL, make_fresh_jwt


class TestConnectorsCRUD:
    @pytest.mark.asyncio
    async def test_list_returns_page(self, authed_client, mock_api):
        mock_api.get("/api/connectors").respond(
            200,
            json={
                "data": [
                    {"id": "c1", "name": "PGVector", "type": "pgvector", "config": {}},
                    {"id": "c2", "name": "Pinecone", "type": "pinecone", "config": {}},
                ],
                "meta": {
                    "pagination": {"page": 1, "per_page": 20, "total": 2, "total_pages": 1}
                },
            },
        )
        page = await authed_client.connectors.list()
        assert len(page.items) == 2
        assert page.total == 2
        assert page.total_pages == 1
        assert page.items[0].type == "pgvector"

    @pytest.mark.asyncio
    async def test_list_with_pagination_params(self, authed_client, mock_api):
        route = mock_api.get("/api/connectors").respond(
            200,
            json={
                "data": [],
                "meta": {
                    "pagination": {"page": 3, "per_page": 5, "total": 12, "total_pages": 3}
                },
            },
        )
        page = await authed_client.connectors.list(page=3, per_page=5)
        assert page.page == 3
        assert page.per_page == 5

    @pytest.mark.asyncio
    async def test_get_single(self, authed_client, mock_api):
        mock_api.get("/api/connectors/c1").respond(
            200,
            json={"id": "c1", "name": "My DB", "type": "pgvector", "config": {"host": "db"}},
        )
        conn = await authed_client.connectors.get("c1")
        assert isinstance(conn, Connector)
        assert conn.id == "c1"
        assert conn.config == {"host": "db"}

    @pytest.mark.asyncio
    async def test_create(self, authed_client, mock_api):
        mock_api.post("/api/connectors").respond(
            200,
            json={"id": "c-new", "name": "New", "type": "qdrant", "config": {"url": "http://q"}},
        )
        conn = await authed_client.connectors.create("New", "qdrant", {"url": "http://q"})
        assert conn.id == "c-new"
        assert conn.type == "qdrant"

    @pytest.mark.asyncio
    async def test_create_minimal(self, authed_client, mock_api):
        mock_api.post("/api/connectors").respond(
            200,
            json={"id": "c-min", "name": "Bare", "type": "pinecone", "config": {}},
        )
        conn = await authed_client.connectors.create("Bare", "pinecone")
        assert conn.name == "Bare"

    @pytest.mark.asyncio
    async def test_update(self, authed_client, mock_api):
        mock_api.patch("/api/connectors/c1").respond(
            200,
            json={"id": "c1", "name": "Renamed", "type": "pgvector", "config": {}},
        )
        conn = await authed_client.connectors.update("c1", name="Renamed")
        assert conn.name == "Renamed"

    @pytest.mark.asyncio
    async def test_delete(self, authed_client, mock_api):
        mock_api.delete("/api/connectors/c1").respond(204)
        result = await authed_client.connectors.delete("c1")
        assert result is None


class TestConnectorsActions:
    @pytest.mark.asyncio
    async def test_test_connector(self, authed_client, mock_api):
        mock_api.post("/api/connectors/c1/test").respond(
            200,
            json={
                "status": "ok",
                "message": "Connection successful",
                "latency_ms": 15.2,
                "details": {"version": "16.1"},
            },
        )
        result = await authed_client.connectors.test("c1")
        assert isinstance(result, TestConnectorResponse)
        assert result.status == "ok"
        assert result.latency_ms == 15.2

    @pytest.mark.asyncio
    async def test_bind(self, authed_client, mock_api):
        mock_api.post("/api/connectors/c1/bind").respond(
            200,
            json={"status": "ok", "bound": 3, "errors": []},
        )
        result = await authed_client.connectors.bind(
            "c1",
            [
                {"vector_id": "v1", "external_resource_id": "doc-1"},
                {"vector_id": "v2", "external_resource_id": "doc-1"},
                {"vector_id": "v3", "external_resource_id": "doc-2"},
            ],
        )
        assert isinstance(result, BindResult)
        assert result.bound == 3


class TestConnectorsConfig:
    @pytest.mark.asyncio
    async def test_get_search_config(self, authed_client, mock_api):
        mock_api.get("/api/connectors/c1/search-config").respond(
            200,
            json={"table_name": "vectors", "column_name": "embedding"},
        )
        config = await authed_client.connectors.get_search_config("c1")
        assert config["table_name"] == "vectors"

    @pytest.mark.asyncio
    async def test_update_search_config(self, authed_client, mock_api):
        mock_api.patch("/api/connectors/c1/search-config").respond(
            200,
            json={"table_name": "vectors", "column_name": "embedding", "top_k": 10},
        )
        config = await authed_client.connectors.update_search_config(
            "c1", {"top_k": 10}
        )
        assert config["top_k"] == 10

    @pytest.mark.asyncio
    async def test_get_ingestion_config(self, authed_client, mock_api):
        mock_api.get("/api/connectors/c1/ingestion-config").respond(
            200,
            json={"target_table": "vectors", "dimension": 1536},
        )
        config = await authed_client.connectors.get_ingestion_config("c1")
        assert config["dimension"] == 1536

    @pytest.mark.asyncio
    async def test_update_ingestion_config(self, authed_client, mock_api):
        mock_api.patch("/api/connectors/c1/ingestion-config").respond(
            200,
            json={"target_table": "vectors", "dimension": 768},
        )
        config = await authed_client.connectors.update_ingestion_config(
            "c1", {"dimension": 768}
        )
        assert config["dimension"] == 768


class TestConnectorsCoverage:
    @pytest.mark.asyncio
    async def test_get_coverage(self, authed_client, mock_api):
        mock_api.get("/api/connectors/c1/coverage").respond(
            200,
            json={
                "total_resources": 100,
                "bound_resources": 85,
                "unbound_resources": 15,
                "coverage_percent": 85.0,
                "details": [],
            },
        )
        cov = await authed_client.connectors.get_coverage("c1")
        assert isinstance(cov, CoverageDetail)
        assert cov.coverage_percent == 85.0
        assert cov.total_resources == 100


class TestConnectorsListAll:
    @pytest.mark.asyncio
    async def test_list_all_multi_page(self, authed_client, mock_api):
        call_count = 0

        def respond(request):
            nonlocal call_count
            call_count += 1
            from httpx import Response

            if call_count == 1:
                return Response(
                    200,
                    json={
                        "data": [{"id": "c1", "name": "A", "type": "pgvector"}],
                        "meta": {"pagination": {"page": 1, "per_page": 1, "total": 2, "total_pages": 2}},
                    },
                )
            return Response(
                200,
                json={
                    "data": [{"id": "c2", "name": "B", "type": "qdrant"}],
                    "meta": {"pagination": {"page": 2, "per_page": 1, "total": 2, "total_pages": 2}},
                },
            )

        mock_api.get("/api/connectors").mock(side_effect=respond)
        items = await authed_client.connectors.list_all(per_page=1).collect()
        assert len(items) == 2
        assert items[0].id == "c1"
        assert items[1].id == "c2"

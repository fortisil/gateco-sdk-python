"""Tests for the main client — CRUD operations, context manager, etc."""

from __future__ import annotations

import pytest
import respx

from gateco_sdk.client import AsyncGatecoClient, GatecoClient
from gateco_sdk.types.connectors import Connector
from gateco_sdk.types.ingestion import IngestDocumentResponse, BatchIngestResponse
from gateco_sdk.types.retrievals import SecuredRetrieval
from tests.conftest import BASE_URL, make_fresh_jwt


# ------------------------------------------------------------------
# Context manager
# ------------------------------------------------------------------


class TestAsyncClientLifecycle:
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_api):
        async with AsyncGatecoClient(BASE_URL) as client:
            assert client is not None
        # After exiting, the transport should be closed.

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self, mock_api):
        client = AsyncGatecoClient(BASE_URL)
        await client.close()
        await client.close()  # should not raise


# ------------------------------------------------------------------
# Connectors
# ------------------------------------------------------------------


class TestConnectors:
    @pytest.mark.asyncio
    async def test_list_connectors(self, authed_client, mock_api):
        mock_api.get("/api/connectors").respond(
            200,
            json={
                "data": [
                    {"id": "c1", "name": "My Connector", "type": "confluence", "config": {}},
                ],
                "meta": {
                    "pagination": {"page": 1, "per_page": 20, "total": 1, "total_pages": 1}
                },
            },
        )
        page = await authed_client.connectors.list()
        assert len(page.items) == 1
        assert isinstance(page.items[0], Connector)
        assert page.items[0].name == "My Connector"
        assert page.total == 1

    @pytest.mark.asyncio
    async def test_get_connector(self, authed_client, mock_api):
        mock_api.get("/api/connectors/c1").respond(
            200,
            json={"id": "c1", "name": "Conn", "type": "slack", "config": {}},
        )
        conn = await authed_client.connectors.get("c1")
        assert conn.id == "c1"
        assert conn.type == "slack"

    @pytest.mark.asyncio
    async def test_create_connector(self, authed_client, mock_api):
        mock_api.post("/api/connectors").respond(
            200,
            json={"id": "c2", "name": "New", "type": "github", "config": {"org": "acme"}},
        )
        conn = await authed_client.connectors.create("New", "github", {"org": "acme"})
        assert conn.id == "c2"

    @pytest.mark.asyncio
    async def test_update_connector(self, authed_client, mock_api):
        mock_api.patch("/api/connectors/c1").respond(
            200,
            json={"id": "c1", "name": "Renamed", "type": "slack", "config": {}},
        )
        conn = await authed_client.connectors.update("c1", name="Renamed")
        assert conn.name == "Renamed"

    @pytest.mark.asyncio
    async def test_delete_connector(self, authed_client, mock_api):
        mock_api.delete("/api/connectors/c1").respond(204)
        result = await authed_client.connectors.delete("c1")
        assert result is None

    @pytest.mark.asyncio
    async def test_test_connector(self, authed_client, mock_api):
        mock_api.post("/api/connectors/c1/test").respond(
            200,
            json={"status": "ok", "message": "reachable", "latency_ms": 42.5},
        )
        result = await authed_client.connectors.test("c1")
        assert result.status == "ok"
        assert result.latency_ms == 42.5


# ------------------------------------------------------------------
# Ingestion
# ------------------------------------------------------------------


class TestIngestion:
    @pytest.mark.asyncio
    async def test_ingest_document(self, authed_client, mock_api):
        mock_api.post("/api/v1/ingest").respond(
            200,
            json={
                "status": "ok",
                "resource_id": "r1",
                "external_resource_id": "ext-1",
                "chunk_count": 3,
                "vector_ids": ["v1", "v2", "v3"],
            },
        )
        resp = await authed_client.ingest.document(
            "c1", "ext-1", "Hello world", labels=["test"]
        )
        assert isinstance(resp, IngestDocumentResponse)
        assert resp.chunk_count == 3
        assert len(resp.vector_ids) == 3

    @pytest.mark.asyncio
    async def test_ingest_batch(self, authed_client, mock_api):
        mock_api.post("/api/v1/ingest/batch").respond(
            200,
            json={
                "status": "ok",
                "succeeded": 2,
                "failed": 0,
                "results": [{"resource_id": "r1"}, {"resource_id": "r2"}],
                "errors": [],
            },
        )
        resp = await authed_client.ingest.batch(
            "c1",
            [
                {"external_resource_id": "a", "text": "doc a"},
                {"external_resource_id": "b", "text": "doc b"},
            ],
        )
        assert isinstance(resp, BatchIngestResponse)
        assert resp.succeeded == 2


# ------------------------------------------------------------------
# Retrievals
# ------------------------------------------------------------------


class TestRetrievals:
    @pytest.mark.asyncio
    async def test_execute_retrieval(self, authed_client, mock_api):
        mock_api.post("/api/retrievals/execute").respond(
            200,
            json={
                "id": "ret-1",
                "principal_id": "p1",
                "connector_id": "c1",
                "status": "completed",
                "total_results": 2,
                "granted_count": 1,
                "denied_count": 1,
                "outcomes": [
                    {
                        "resource_id": "r1",
                        "score": 0.95,
                        "granted": True,
                        "policy_traces": [],
                    },
                    {
                        "resource_id": "r2",
                        "score": 0.8,
                        "granted": False,
                        "denial_reason": {"code": "POLICY_DENY", "message": "denied"},
                        "policy_traces": [],
                    },
                ],
            },
        )
        result = await authed_client.retrievals.execute(
            [0.1, 0.2, 0.3],
            principal_id="p1",
            connector_id="c1",
            top_k=5,
        )
        assert isinstance(result, SecuredRetrieval)
        assert result.granted_count == 1
        assert result.denied_count == 1
        assert len(result.outcomes) == 2

    @pytest.mark.asyncio
    async def test_get_retrieval(self, authed_client, mock_api):
        mock_api.get("/api/retrievals/ret-1").respond(
            200,
            json={
                "id": "ret-1",
                "principal_id": "p1",
                "connector_id": "c1",
                "status": "completed",
                "total_results": 0,
                "granted_count": 0,
                "denied_count": 0,
                "outcomes": [],
            },
        )
        result = await authed_client.retrievals.get("ret-1")
        assert result.id == "ret-1"

    @pytest.mark.asyncio
    async def test_list_retrievals(self, authed_client, mock_api):
        mock_api.get("/api/retrievals").respond(
            200,
            json={
                "data": [
                    {
                        "id": "ret-1",
                        "status": "completed",
                        "total_results": 0,
                        "granted_count": 0,
                        "denied_count": 0,
                        "outcomes": [],
                    }
                ],
                "meta": {
                    "pagination": {"page": 1, "per_page": 20, "total": 1, "total_pages": 1}
                },
            },
        )
        page = await authed_client.retrievals.list()
        assert len(page.items) == 1


# ------------------------------------------------------------------
# Sync client smoke test
# ------------------------------------------------------------------


class TestSyncClient:
    def test_sync_client_context_manager(self):
        with respx.mock(base_url=BASE_URL):
            with GatecoClient(BASE_URL) as client:
                assert client is not None

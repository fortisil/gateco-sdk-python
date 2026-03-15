"""Tests for IngestionResource — document and batch ingestion."""

from __future__ import annotations

import pytest

from gateco_sdk.types.ingestion import BatchIngestResponse, IngestDocumentResponse
from tests.conftest import BASE_URL


class TestIngestDocument:
    @pytest.mark.asyncio
    async def test_basic_ingest(self, authed_client, mock_api):
        mock_api.post("/api/v1/ingest").respond(
            200,
            json={
                "status": "success",
                "resource_id": "r-abc",
                "external_resource_id": "doc-1",
                "chunk_count": 4,
                "vector_ids": ["v1", "v2", "v3", "v4"],
            },
        )
        resp = await authed_client.ingest.document(
            "c1", "doc-1", "This is the document content."
        )
        assert isinstance(resp, IngestDocumentResponse)
        assert resp.status == "success"
        assert resp.resource_id == "r-abc"
        assert resp.chunk_count == 4
        assert len(resp.vector_ids) == 4

    @pytest.mark.asyncio
    async def test_ingest_with_all_metadata(self, authed_client, mock_api):
        mock_api.post("/api/v1/ingest").respond(
            200,
            json={
                "status": "success",
                "resource_id": "r-meta",
                "external_resource_id": "doc-meta",
                "chunk_count": 1,
                "vector_ids": ["v-meta"],
            },
        )
        resp = await authed_client.ingest.document(
            connector_id="c1",
            external_resource_id="doc-meta",
            text="Content with full metadata.",
            classification="internal",
            sensitivity="high",
            domain="engineering",
            labels=["sdk", "test"],
            metadata={"source": "unit_test"},
            owner_principal_id="p-owner",
        )
        assert resp.resource_id == "r-meta"

    @pytest.mark.asyncio
    async def test_ingest_with_idempotency_key(self, authed_client, mock_api):
        mock_api.post("/api/v1/ingest").respond(
            200,
            json={
                "status": "success",
                "resource_id": "r-idem",
                "external_resource_id": "doc-idem",
                "chunk_count": 2,
                "vector_ids": ["v1", "v2"],
            },
        )
        resp = await authed_client.ingest.document(
            "c1", "doc-idem", "Content.",
            idempotency_key="idem-key-123",
        )
        assert resp.resource_id == "r-idem"


class TestIngestBatch:
    @pytest.mark.asyncio
    async def test_batch_success(self, authed_client, mock_api):
        mock_api.post("/api/v1/ingest/batch").respond(
            200,
            json={
                "status": "success",
                "succeeded": 3,
                "failed": 0,
                "results": [
                    {"external_resource_id": "a", "resource_id": "r1", "chunk_count": 2, "vector_ids": ["v1", "v2"]},
                    {"external_resource_id": "b", "resource_id": "r2", "chunk_count": 1, "vector_ids": ["v3"]},
                    {"external_resource_id": "c", "resource_id": "r3", "chunk_count": 1, "vector_ids": ["v4"]},
                ],
                "errors": [],
            },
        )
        resp = await authed_client.ingest.batch(
            "c1",
            [
                {"external_resource_id": "a", "text": "Document A"},
                {"external_resource_id": "b", "text": "Document B"},
                {"external_resource_id": "c", "text": "Document C"},
            ],
        )
        assert isinstance(resp, BatchIngestResponse)
        assert resp.status == "success"
        assert resp.succeeded == 3
        assert resp.failed == 0
        assert len(resp.results) == 3

    @pytest.mark.asyncio
    async def test_batch_partial_success(self, authed_client, mock_api):
        mock_api.post("/api/v1/ingest/batch").respond(
            200,
            json={
                "status": "partial_success",
                "succeeded": 1,
                "failed": 1,
                "results": [
                    {"external_resource_id": "a", "resource_id": "r1", "chunk_count": 1, "vector_ids": ["v1"]},
                ],
                "errors": [
                    {"external_resource_id": "b", "error_category": "ingestion_validation_failed", "detail": "empty text"},
                ],
            },
        )
        resp = await authed_client.ingest.batch(
            "c1",
            [
                {"external_resource_id": "a", "text": "Good doc"},
                {"external_resource_id": "b", "text": ""},
            ],
        )
        assert resp.status == "partial_success"
        assert resp.succeeded == 1
        assert resp.failed == 1
        assert len(resp.errors) == 1

    @pytest.mark.asyncio
    async def test_batch_with_idempotency_key(self, authed_client, mock_api):
        mock_api.post("/api/v1/ingest/batch").respond(
            200,
            json={
                "status": "success",
                "succeeded": 1,
                "failed": 0,
                "results": [
                    {"external_resource_id": "a", "resource_id": "r1", "chunk_count": 1, "vector_ids": ["v1"]},
                ],
                "errors": [],
            },
        )
        resp = await authed_client.ingest.batch(
            "c1",
            [{"external_resource_id": "a", "text": "Doc"}],
            idempotency_key="batch-key-456",
        )
        assert resp.succeeded == 1

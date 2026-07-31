"""Ingestion resource — document, batch, and file ingestion."""

from __future__ import annotations

import mimetypes
import os
from typing import TYPE_CHECKING, Any

from gateco_sdk.types.ingestion import (
    BatchFileIngestResponse,
    BatchIngestResponse,
    IngestDocumentResponse,
    IngestFileResponse,
)

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class IngestionResource:
    """Namespace for ingestion endpoints.

    Accessed as ``client.ingest``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client
        from gateco_sdk.resources.ingestion_jobs import IngestionJobsResource

        #: Async ingestion jobs (Team+): client.ingest.jobs.enqueue(...)
        self.jobs = IngestionJobsResource(client)


    async def document(
        self,
        connector_id: str,
        external_resource_id: str,
        text: str,
        *,
        classification: str | None = None,
        sensitivity: str | None = None,
        domain: str | None = None,
        labels: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        owner_principal_id: str | None = None,
        idempotency_key: str | None = None,
        chunking: dict[str, Any] | None = None,
        embedding: dict[str, Any] | None = None,
    ) -> IngestDocumentResponse:
        """Ingest a single document.

        Requires a Tier 1 connector (pgvector, supabase, neon, pinecone, qdrant).

        Args:
            connector_id: Target connector (must be Tier 1).
            external_resource_id: Caller-defined resource identifier.
            text: Document text to embed and store.
            classification: Optional classification label.
            sensitivity: Optional sensitivity level.
            domain: Optional domain tag.
            labels: Optional list of labels.
            metadata: Optional arbitrary metadata dict.
            owner_principal_id: Optional owner principal for access control.
            idempotency_key: Optional idempotency key for safe retries.
            chunking: Optional per-request chunking override, e.g.
                {"strategy": "markdown", "chunk_size": 512, "chunk_overlap": 76}.
                Strategies: characters, tokens, recursive, markdown. Applies to
                this request only; the connector's pinned config is unchanged.
            embedding: Optional embedding provider override, e.g.
                {"provider": "openai_compatible", "model": "nomic-embed-text",
                "base_url": "http://localhost:11434/v1"}. Providers: openai,
                openai_compatible, cohere, voyage. API keys are never sent in
                requests; they resolve server-side from provider env vars.
        """
        body: dict[str, Any] = {
            "connector_id": connector_id,
            "external_resource_id": external_resource_id,
            "text": text,
        }
        if classification is not None:
            body["classification"] = classification
        if sensitivity is not None:
            body["sensitivity"] = sensitivity
        if domain is not None:
            body["domain"] = domain
        if labels is not None:
            body["labels"] = labels
        if metadata is not None:
            body["metadata"] = metadata
        if owner_principal_id is not None:
            body["owner_principal_id"] = owner_principal_id
        if idempotency_key is not None:
            body["idempotency_key"] = idempotency_key
        if chunking is not None:
            body["chunking"] = chunking
        if embedding is not None:
            body["embedding"] = embedding

        data = await self._client._request("POST", "/api/v1/ingest", json=body)
        return IngestDocumentResponse.model_validate(data)

    async def batch(
        self,
        connector_id: str,
        records: list[dict[str, Any]],
        *,
        idempotency_key: str | None = None,
        chunking: dict[str, Any] | None = None,
        embedding: dict[str, Any] | None = None,
    ) -> BatchIngestResponse:
        """Ingest a batch of documents in a single request.

        Requires a Tier 1 connector (pgvector, supabase, neon, pinecone, qdrant)
        and the ``batch_ingestion`` feature (Team plan and above); free-plan orgs
        receive an EntitlementError with ``reason="feature_not_in_plan"``.

        Args:
            connector_id: Target connector (must be Tier 1).
            records: List of record dicts, each containing at minimum
                ``external_resource_id`` and ``text``.
            idempotency_key: Optional idempotency key for safe retries.
        """
        body: dict[str, Any] = {
            "connector_id": connector_id,
            "records": records,
        }
        if idempotency_key is not None:
            body["idempotency_key"] = idempotency_key
        if chunking is not None:
            body["chunking"] = chunking
        if embedding is not None:
            body["embedding"] = embedding

        data = await self._client._request("POST", "/api/v1/ingest/batch", json=body)
        return BatchIngestResponse.model_validate(data)

    async def document_byoe(
        self,
        connector_id: str,
        external_resource_id: str,
        pre_embedded_chunks: list[dict[str, Any]],
        *,
        classification: str | None = None,
        sensitivity: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> IngestDocumentResponse:
        """Ingest a document with pre-embedded chunks (Bring Your Own Embeddings).

        Args:
            connector_id: Target connector (must be Tier 1).
            external_resource_id: Caller-defined resource identifier.
            pre_embedded_chunks: List of dicts with 'text' and 'vector' keys.
            classification: Optional classification label.
            sensitivity: Optional sensitivity level.
            metadata: Optional arbitrary metadata dict.
            idempotency_key: Optional idempotency key for safe retries.
        """
        body: dict[str, Any] = {
            "connector_id": connector_id,
            "external_resource_id": external_resource_id,
            "pre_embedded_chunks": pre_embedded_chunks,
        }
        if classification is not None:
            body["classification"] = classification
        if sensitivity is not None:
            body["sensitivity"] = sensitivity
        if metadata is not None:
            body["metadata"] = metadata
        if idempotency_key is not None:
            body["idempotency_key"] = idempotency_key

        data = await self._client._request("POST", "/api/v1/ingest", json=body)
        return IngestDocumentResponse.model_validate(data)

    async def file(
        self,
        connector_id: str,
        file_path: str,
        *,
        external_resource_id: str | None = None,
        classification: str | None = None,
        sensitivity: str | None = None,
        domain: str | None = None,
        labels: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> IngestFileResponse:
        """Upload and ingest a file (PDF, DOCX, CSV, XLSX, etc.).

        Args:
            connector_id: Target connector (must be Tier 1).
            file_path: Path to the file on disk.
            external_resource_id: Optional resource identifier. Auto-generated if omitted.
            classification: Optional classification label.
            sensitivity: Optional sensitivity level.
            domain: Optional domain tag.
            labels: Optional list of labels (sent as comma-separated string).
            metadata: Optional metadata dict (sent as JSON string).
            idempotency_key: Optional idempotency key for safe retries.
        """
        import json as json_mod

        filename = os.path.basename(file_path)
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        form_data: dict[str, Any] = {"connector_id": connector_id}
        if external_resource_id is not None:
            form_data["external_resource_id"] = external_resource_id
        if classification is not None:
            form_data["classification"] = classification
        if sensitivity is not None:
            form_data["sensitivity"] = sensitivity
        if domain is not None:
            form_data["domain"] = domain
        if labels is not None:
            form_data["labels"] = ",".join(labels)
        if metadata is not None:
            form_data["metadata_json"] = json_mod.dumps(metadata)
        if idempotency_key is not None:
            form_data["idempotency_key"] = idempotency_key

        with open(file_path, "rb") as f:
            files = {"file": (filename, f, mime_type)}
            data = await self._client._upload(
                "POST", "/api/v1/ingest/file", files=files, data=form_data,
            )
        return IngestFileResponse.model_validate(data)

    async def files(
        self,
        connector_id: str,
        file_paths: list[str],
        *,
        domain: str | None = None,
        classification: str | None = None,
        sensitivity: str | None = None,
        labels: list[str] | None = None,
    ) -> BatchFileIngestResponse:
        """Upload and ingest multiple files in a single batch.

        Args:
            connector_id: Target connector (must be Tier 1).
            file_paths: List of file paths to upload.
            domain: Optional domain tag applied to all files.
            classification: Optional classification applied to all files.
            sensitivity: Optional sensitivity applied to all files.
            labels: Optional labels applied to all files.
        """
        form_data: dict[str, Any] = {"connector_id": connector_id}
        if domain is not None:
            form_data["domain"] = domain
        if classification is not None:
            form_data["classification"] = classification
        if sensitivity is not None:
            form_data["sensitivity"] = sensitivity
        if labels is not None:
            form_data["labels"] = ",".join(labels)

        file_handles = []
        file_tuples: list[tuple[str, Any]] = []
        try:
            for fp in file_paths:
                filename = os.path.basename(fp)
                mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                fh = open(fp, "rb")
                file_handles.append(fh)
                file_tuples.append(("files", (filename, fh, mime_type)))

            data = await self._client._upload(
                "POST", "/api/v1/ingest/files", files=file_tuples, data=form_data,
            )
        finally:
            for fh in file_handles:
                fh.close()

        return BatchFileIngestResponse.model_validate(data)

    async def delete_resource(
        self, connector_id: str, external_resource_id: str,
    ) -> dict:
        """Tombstone an ingested resource: vectors + registry + soft delete."""
        return await self._client._request(
            "DELETE",
            f"/api/v1/ingest/resources/{external_resource_id}",
            params={"connector_id": connector_id},
        )

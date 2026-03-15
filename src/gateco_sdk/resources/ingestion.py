"""Ingestion resource — document and batch ingestion."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gateco_sdk.types.ingestion import (
    BatchIngestResponse,
    IngestDocumentResponse,
)

if TYPE_CHECKING:
    from gateco_sdk.client import AsyncGatecoClient


class IngestionResource:
    """Namespace for ingestion endpoints.

    Accessed as ``client.ingest``.
    """

    def __init__(self, client: AsyncGatecoClient) -> None:
        self._client = client

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

        data = await self._client._request("POST", "/api/v1/ingest", json=body)
        return IngestDocumentResponse.model_validate(data)

    async def batch(
        self,
        connector_id: str,
        records: list[dict[str, Any]],
        *,
        idempotency_key: str | None = None,
    ) -> BatchIngestResponse:
        """Ingest a batch of documents in a single request.

        Requires a Tier 1 connector (pgvector, supabase, neon, pinecone, qdrant).

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

        data = await self._client._request("POST", "/api/v1/ingest/batch", json=body)
        return BatchIngestResponse.model_validate(data)

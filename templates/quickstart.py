"""Gateco quickstart: login, ingest a document, and execute a retrieval."""

import asyncio

from gateco_sdk import AsyncGatecoClient


async def main():
    async with AsyncGatecoClient(base_url="http://localhost:8000") as client:
        # Login
        await client.login("admin@acmecorp.com", "password123")
        print("Logged in successfully")

        # List connectors
        page = await client.connectors.list()
        print(f"Found {page.total} connectors")

        if page.items:
            connector_id = page.items[0].id

            # Ingest a document
            result = await client.ingest.document(
                connector_id=connector_id,
                external_resource_id="quickstart-doc-1",
                text="This is a sample document for testing Gateco's permission-aware retrieval.",
            )
            print(f"Ingested: {result.chunk_count} chunks, vectors: {result.vector_ids}")


asyncio.run(main())

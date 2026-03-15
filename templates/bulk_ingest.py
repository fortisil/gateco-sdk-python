"""Bulk ingest text files from a directory."""

import asyncio
from pathlib import Path

from gateco_sdk import AsyncGatecoClient


async def main():
    connector_id = "YOUR_CONNECTOR_ID"
    directory = Path("./documents")

    async with AsyncGatecoClient(base_url="http://localhost:8000") as client:
        await client.login("admin@acmecorp.com", "password123")

        records = []
        for f in directory.glob("*.txt"):
            records.append(
                {
                    "external_resource_id": f.stem,
                    "text": f.read_text(),
                }
            )

        if records:
            result = await client.ingest.batch(
                connector_id=connector_id,
                records=records,
            )
            print(f"Ingested: {result.succeeded} succeeded, {result.failed} failed")
        else:
            print("No .txt files found in ./documents")


asyncio.run(main())

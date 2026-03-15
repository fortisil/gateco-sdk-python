"""Scan and register existing vectors in a connector."""

import asyncio

from gateco_sdk import AsyncGatecoClient
from gateco_sdk.resources.retroactive import RetroactiveResource


async def main():
    connector_id = "YOUR_CONNECTOR_ID"

    async with AsyncGatecoClient(base_url="http://localhost:8000") as client:
        await client.login("admin@acmecorp.com", "password123")

        retroactive = RetroactiveResource(client)

        # Dry run first
        result = await retroactive.register(
            connector_id=connector_id,
            scan_limit=5000,
            default_classification="internal",
            default_sensitivity="medium",
            dry_run=True,
        )
        print(
            f"Dry run: {result.scanned_vectors} scanned, "
            f"{result.newly_registered} would be registered"
        )

        # If satisfied, run for real
        if input("Proceed? (y/n): ").lower() == "y":
            result = await retroactive.register(
                connector_id=connector_id,
                scan_limit=5000,
                default_classification="internal",
                default_sensitivity="medium",
                dry_run=False,
            )
            print(
                f"Registered: {result.newly_registered} vectors, "
                f"{result.resources_created} resources created"
            )


asyncio.run(main())

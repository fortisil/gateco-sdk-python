"""Set up a connector with a policy and bind metadata."""

import asyncio

from gateco_sdk import AsyncGatecoClient
from gateco_sdk.resources.policies import PoliciesResource


async def main():
    async with AsyncGatecoClient(base_url="http://localhost:8000") as client:
        await client.login("admin@acmecorp.com", "password123")

        # Create a connector
        connector = await client.connectors.create(
            name="My pgvector DB",
            type="pgvector",
            config={"host": "localhost", "port": 5432, "database": "vectors"},
        )
        print(f"Created connector: {connector.id}")

        # Create a policy
        policies = PoliciesResource(client)
        policy = await policies.create(
            name="Engineering Access",
            type="rbac",
            effect="allow",
            description="Allow engineering team to access internal docs",
            rules=[
                {
                    "description": "Engineers can read internal",
                    "effect": "allow",
                    "conditions": [
                        {
                            "field": "principal.department",
                            "operator": "eq",
                            "value": "engineering",
                        }
                    ],
                    "priority": 1,
                }
            ],
            resource_selectors=[{"classification": "internal"}],
        )
        print(f"Created policy: {policy.id}")


asyncio.run(main())

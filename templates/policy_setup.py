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
        # NOTE: condition fields MUST use resource. or principal. prefix.
        # Bare names silently check principal attributes, not resources.
        policies = PoliciesResource(client)
        policy = await policies.create(
            name="Engineering Access",
            type="rbac",
            effect="allow",
            description="Allow engineering team to access internal docs",
            rules=[
                {
                    "description": "Engineers can read internal docs",
                    "effect": "allow",
                    "priority": 1,
                    "conditions": [
                        {
                            # resource. prefix -> checks resource metadata
                            "field": "resource.classification",
                            "operator": "lte",
                            "value": "internal",
                        },
                        {
                            # principal. prefix -> checks requesting identity
                            "field": "principal.roles",
                            "operator": "contains",
                            "value": "engineer",
                        },
                    ],
                }
            ],
            resource_selectors=["connector_abc"],
        )
        print(f"Created policy: {policy.id}")


asyncio.run(main())

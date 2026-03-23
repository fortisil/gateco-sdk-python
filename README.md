# Gateco Python SDK

Official Python client for the [Gateco](https://gateco.ai) API -- permission-aware retrieval for AI systems.

[![GitHub](https://img.shields.io/badge/GitHub-gateco--sdk--python-blue)](https://github.com/fortisil/gateco-sdk-python)

## Installation

```bash
pip install gateco
```

## Quick Start

### Async (recommended)

```python
import asyncio
from gateco_sdk import AsyncGatecoClient

async def main():
    async with AsyncGatecoClient("https://api.gateco.ai") as client:
        # Authenticate
        await client.login("user@example.com", "password")

        # Ingest a document
        result = await client.ingest.document(
            connector_id="conn-abc",
            external_resource_id="doc-123",
            text="Quarterly revenue increased 15% year-over-year.",
            classification="financial",
            labels=["earnings", "q4"],
        )
        print(f"Ingested: {result.resource_id} ({result.chunk_count} chunks)")

        # Execute a permission-gated retrieval
        retrieval = await client.retrievals.execute(
            query="What was the revenue growth?",
            principal_id="user-456",
            connector_id="conn-abc",
            top_k=5,
        )
        for outcome in retrieval.outcomes:
            if outcome.granted:
                print(f"  [GRANTED] {outcome.resource_id} (score={outcome.score})")
            else:
                print(f"  [DENIED]  {outcome.resource_id}")

asyncio.run(main())
```

### Synchronous

```python
from gateco_sdk import GatecoClient

with GatecoClient("https://api.gateco.ai") as client:
    client.login("user@example.com", "password")

    page = client.connectors.list()
    for connector in page.items:
        print(f"{connector.name} ({connector.type})")
```

### API Key Authentication

```python
from gateco_sdk import AsyncGatecoClient

client = AsyncGatecoClient("https://api.gateco.ai", api_key="sk-your-key")
```

## Resources

| Namespace | Description |
|-----------|-------------|
| `client.auth` | Login, signup, token refresh, logout |
| `client.connectors` | Connector CRUD, test, bind, config, coverage, classification suggestions |
| `client.ingest` | Single-document and batch ingestion |
| `client.retrievals` | Permission-gated retrieval execution, filter, and history |
| `client.answers` | Grounded answer synthesis with citations |
| `client.policies` | Policy CRUD, activate, archive |
| `client.identity_providers` | Identity provider CRUD and sync |
| `client.principals` | Principal listing and detail |
| `client.data_catalog` | Gated resource listing and metadata updates |
| `client.pipelines` | Pipeline CRUD and run management |
| `client.billing` | Plans, usage, invoices, subscription, checkout |
| `client.audit` | Audit log listing and CSV export |
| `client.simulator` | Access simulation dry-runs |
| `client.dashboard` | Dashboard statistics |
| `client.retroactive` | Retroactive vector registration |

## Pagination

List endpoints return a `Page` object. Use `list_all()` for automatic async pagination:

```python
async for connector in client.connectors.list_all():
    print(connector.name)
```

## Error Handling

```python
from gateco_sdk.errors import NotFoundError, RateLimitError

try:
    conn = await client.connectors.get("nonexistent")
except NotFoundError:
    print("Connector not found")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
```

## Development

```bash
pip install -e ".[dev]"
pytest -v
```

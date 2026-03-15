# Gateco Python SDK

Official Python client for the [Gateco](https://gateco.dev) API -- permission-aware retrieval for AI systems.

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
    async with AsyncGatecoClient("https://api.gateco.dev") as client:
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

with GatecoClient("https://api.gateco.dev") as client:
    client.login("user@example.com", "password")

    page = client.connectors.list()
    for connector in page.items:
        print(f"{connector.name} ({connector.type})")
```

### API Key Authentication

```python
from gateco_sdk import AsyncGatecoClient

client = AsyncGatecoClient("https://api.gateco.dev", api_key="sk-your-key")
```

## Resources

| Namespace | Description |
|-----------|-------------|
| `client.auth` | Login, signup, token refresh, logout |
| `client.connectors` | Connector CRUD, test, bind, config, coverage |
| `client.ingest` | Single-document and batch ingestion |
| `client.retrievals` | Permission-gated retrieval execution and history |

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

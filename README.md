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

        # Execute a permission-gated retrieval (vector search, default)
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

        # Keyword search (ranked full-text search)
        result = await client.retrievals.execute(
            query="quarterly revenue report",
            principal_id="user-456",
            connector_id="conn-abc",
            search_mode="keyword",
            top_k=10,
        )

        # Hybrid search (vector + keyword fused)
        result = await client.retrievals.execute(
            query="quarterly revenue report",
            principal_id="user-456",
            connector_id="conn-abc",
            search_mode="hybrid",
            alpha=0.5,  # 1.0=all-vector, 0.0=all-keyword
            top_k=10,
        )

        # Grep search (exact pattern matching)
        result = await client.retrievals.execute(
            query="ERR-4021",
            principal_id="user-456",
            connector_id="conn-abc",
            search_mode="grep",
        )
        print(result.match_count, result.sort_order)  # total matches, "natural"

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

## MCP Server (Model Context Protocol)

The SDK includes an optional MCP server that lets AI agents (Claude Desktop, Cursor, etc.) perform permission-aware retrieval directly.

### Installation

```bash
pip install gateco[mcp]
```

### Usage

```bash
# Via CLI subcommand
gateco mcp serve

# Via direct entry point (for MCP host configs)
gateco-mcp
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "gateco": {
      "command": "gateco-mcp",
      "env": {
        "GATECO_API_KEY": "gk_...",
        "GATECO_BASE_URL": "https://api.gateco.ai"
      }
    }
  }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `gateco_retrieve` | Permission-aware retrieval (vector/keyword/hybrid/grep) |
| `gateco_ask` | Grounded answer synthesis with search modes (Pro+) |
| `gateco_check_access` | Dry-run access simulation (Pro+) |
| `gateco_list_connectors` | List connectors with readiness levels |
| `gateco_list_principals` | List identity principals |
| `gateco_resolve_principal` | Resolve a principal by email or provider subject |

All tools return markdown-formatted text. Denied content is never exposed -- only denial reasons and counts are shown. The server reuses the SDK credential resolution chain: `GATECO_API_KEY` env var, `GATECO_BASE_URL` env var, or `~/.gateco/credentials.json` (set by `gateco login`).

### Programmatic Usage

```python
from gateco_sdk.mcp import create_server, run_stdio

# Create a configured server instance
server = create_server()

# Or start directly on stdio
run_stdio()
```

## Resources

| Namespace | Description |
|-----------|-------------|
| `client.auth` | Login, signup, token refresh, logout |
| `client.connectors` | Connector CRUD, test, bind, config, coverage, classification suggestions |
| `client.ingest` | Single-document and batch ingestion |
| `client.retrievals` | Permission-gated retrieval execution, filter, and history |
| `client.answers` | Grounded answer synthesis with citations |
| `client.policies` | Policy CRUD, activate, archive, and templates |
| `client.identity_providers` | Identity provider CRUD and sync |
| `client.principals` | Principal listing, detail, and resolve |
| `client.data_catalog` | Gated resource listing and metadata updates |
| `client.pipelines` | Pipeline CRUD and run management |
| `client.billing` | Plans, usage, invoices, subscription, checkout |
| `client.audit` | Audit log listing and CSV export |
| `client.simulator` | Access simulation dry-runs |
| `client.dashboard` | Dashboard statistics |
| `client.retroactive` | Retroactive vector registration |

## Principal Resolution

Resolve principals by email or provider subject without knowing their ID:

```python
# Resolve by email
principal = await client.principals.resolve(email="alice@company.com")

# Resolve by provider subject (raw IDP-side user ID)
principal = await client.principals.resolve(provider_subject="okta-user-123")

# Scoped to a specific identity provider
principal = await client.principals.resolve(
    email="alice@company.com",
    identity_provider_id="idp-uuid-here",
)
```

Resolution is read-only -- it finds existing active principals but never creates them. Returns 404 if no active principal matches.

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

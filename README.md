# Gateco Python SDK

Official Python client for the [Gateco](https://gateco.ai) API — permission-aware retrieval for AI systems.

[![PyPI version](https://img.shields.io/pypi/v/gateco.svg)](https://pypi.org/project/gateco/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![GitHub](https://img.shields.io/badge/GitHub-gateco--sdk--python-blue)](https://github.com/fortisil/gateco-sdk-python)

---

## The problem it solves

Without Gateco, when an employee asks your AI assistant "What is the CEO's salary?",
the RAG pipeline returns the salary from a leaked HR document.

With Gateco:

```python
from gateco_sdk import GatecoClient

client = GatecoClient(api_key="gck_live_abc123...")

result = client.retrievals.execute(
    query="What is the CEO's salary?",
    principal_id="user_james_wu",
    connector_id="connector_hr_docs",
    search_mode="hybrid",
)

# result.allowed_chunks → [] (denied — James Wu lacks HR classification access)
# result.denied_count   → 1
# result.decision       → "DENIED"
# Your AI model never sees the salary data
```

Gateco sits between your AI agent and your vector store. Every retrieval is evaluated against
your access policies before any content reaches the model.

---

## Installation

```bash
pip install gateco
```

For MCP server support (Claude Desktop, Cursor, etc.):

```bash
pip install gateco[mcp]
```

---

## Authentication

Gateco API keys use the format `gck_<env>_<random>` (e.g. `gck_live_abc123...`).

Generate keys via the dashboard or via `client.api_keys.create(name="my-service")`.

```python
from gateco_sdk import AsyncGatecoClient, GatecoClient

# Async client with API key
client = AsyncGatecoClient("https://api.gateco.ai", api_key="gck_live_abc123...")

# Sync client with API key
client = GatecoClient("https://api.gateco.ai", api_key="gck_live_abc123...")

# Or use email/password login (issues a short-lived JWT)
client = GatecoClient("https://api.gateco.ai")
client.login("user@example.com", "password")
```

The API key is sent as `Authorization: Bearer <key>` on every request. Set it via the
`GATECO_API_KEY` environment variable when using the CLI or MCP server.

---

## Quick Start

### Async (recommended for production services)

```python
import asyncio
from gateco_sdk import AsyncGatecoClient

async def main():
    async with AsyncGatecoClient(
        "https://api.gateco.ai",
        api_key="gck_live_abc123...",
    ) as client:

        # Policy-gated retrieval — the core Gateco primitive
        result = await client.retrievals.execute(
            query="What is the CEO's salary?",
            principal_id="user_james_wu",
            connector_id="connector_hr_docs",
            search_mode="hybrid",
            alpha=0.7,   # 70% vector weight, 30% keyword
            top_k=5,
        )

        # Allowed chunks are safe to pass to your LLM
        for chunk in result.allowed_chunks:
            print(f"[ALLOWED] {chunk.resource_id} score={chunk.score}")

        # Denied chunks are redacted — only metadata is surfaced
        print(f"Denied: {result.denied_count} chunk(s)")

asyncio.run(main())
```

### Synchronous (scripts and notebooks)

```python
from gateco_sdk import GatecoClient

with GatecoClient("https://api.gateco.ai", api_key="gck_live_abc123...") as client:
    result = client.retrievals.execute(
        query="What is the CEO's salary?",
        principal_id="user_james_wu",
        connector_id="connector_hr_docs",
        search_mode="hybrid",
    )
    print(result.decision)  # "DENIED"
```

---

## Available Namespaces

All 17 namespaces are available on both `AsyncGatecoClient` (async) and `GatecoClient` (sync).

| Namespace | Description |
|-----------|-------------|
| `client.answers` | Grounded answer synthesis with policy-filtered citations (Pro+) |
| `client.api_keys` | Create, list, delete, and rotate API keys |
| `client.audit` | Audit log listing and CSV export |
| `client.auth` | Login, signup, token refresh, logout |
| `client.billing` | Plans, usage meters, invoices, Stripe checkout and portal |
| `client.connectors` | Connector CRUD, connection testing, search/ingestion config, coverage, classification suggestions |
| `client.dashboard` | Aggregated dashboard statistics |
| `client.data_catalog` | Gated resource listing and metadata updates |
| `client.identity_providers` | Identity provider CRUD and sync (Okta, Azure, AWS, GCP) |
| `client.ingest` | Single-document, batch, and file ingestion (Tier 1 connectors) |
| `client.onboarding` | Onboarding status (6 computed steps) and checklist dismissal |
| `client.pipelines` | Pipeline CRUD and run management |
| `client.policies` | Policy CRUD, lifecycle (activate/archive), and templates |
| `client.principals` | Principal listing, detail, and resolution by email or provider subject |
| `client.retroactive` | Retroactive vector registration for existing connectors |
| `client.retrievals` | Permission-gated retrieval execution, policy filter, and history |
| `client.simulator` | Dry-run and live-preview access simulation (Pro+) |

---

## Retrieval Search Modes

```python
# Vector search (default) — semantic similarity
result = await client.retrievals.execute(
    query="quarterly earnings", principal_id="...", connector_id="...",
)

# Keyword search — ranked full-text search (BM25)
result = await client.retrievals.execute(
    query="quarterly earnings", principal_id="...", connector_id="...",
    search_mode="keyword",
)

# Hybrid search — vector + keyword fused (RRF)
result = await client.retrievals.execute(
    query="quarterly earnings", principal_id="...", connector_id="...",
    search_mode="hybrid",
    alpha=0.5,   # 1.0 = all-vector, 0.0 = all-keyword
)

# Grep — exact pattern matching
result = await client.retrievals.execute(
    query="ERR-4021", principal_id="...", connector_id="...",
    search_mode="grep",
    pattern_type="regex",
    case_sensitive=False,
)
```

---

## API Key Management

```python
# Create a key — the plaintext is returned exactly once
key_info = await client.api_keys.create(name="prod-worker")
print(key_info["key"])    # gck_live_abc123...  (store this securely)
print(key_info["prefix"]) # gck_live_abc

# List keys (plaintext never returned after creation)
keys = await client.api_keys.list()

# Rotate a key — old key is invalidated immediately
new_key = await client.api_keys.rotate(key_id="key-uuid-here")

# Delete a key
await client.api_keys.delete(key_id="key-uuid-here")
```

---

## Onboarding Status

```python
# Check which onboarding steps are complete
status = await client.onboarding.status()
for step in status["steps"]:
    print(f"{step['name']:30s}  {step['status']}")

# Dismiss the checklist once the org is fully configured
await client.onboarding.dismiss()
```

---

## Principal Resolution

```python
# Resolve a principal by email (read-only — never creates)
principal = await client.principals.resolve(email="alice@company.com")

# Resolve by raw IDP-side user ID
principal = await client.principals.resolve(provider_subject="okta-user-123")

# Scoped to a specific identity provider
principal = await client.principals.resolve(
    email="alice@company.com",
    identity_provider_id="idp-uuid-here",
)
```

---

## Grounded Answer Synthesis (Pro+)

```python
answer = await client.answers.execute(
    query="Summarise the Q4 revenue results.",
    principal_id="user_alice",
    connector_id="connector_finance_docs",
    search_mode="hybrid",
)

print(answer.answer_text)      # LLM-generated answer from allowed chunks only
print(answer.outcome)          # "answered" | "no_access" | "insufficient_context"
for citation in answer.citations:
    print(f"  [{citation.score:.2f}] {citation.resource_id}")
```

---

## Pagination

List endpoints return a `Page` object. Use `list_all()` for automatic async pagination:

```python
async for connector in client.connectors.list_all():
    print(connector.name)
```

---

## Error Handling

```python
from gateco_sdk.errors import NotFoundError, RateLimitError, AuthenticationError

try:
    conn = await client.connectors.get("nonexistent-id")
except NotFoundError:
    print("Connector not found")
except RateLimitError as e:
    print(f"Rate limited — retry after {e.retry_after}s")
except AuthenticationError:
    print("Invalid or expired credentials")
```

---

## MCP Server (Model Context Protocol)

The optional MCP server lets AI agents (Claude Desktop, Cursor, etc.) perform
permission-aware retrieval without any custom code.

```bash
pip install gateco[mcp]

# Start the server
gateco mcp serve

# Or use the direct entry point (for MCP host configs)
gateco-mcp
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "gateco": {
      "command": "gateco-mcp",
      "env": {
        "GATECO_API_KEY": "gck_live_abc123...",
        "GATECO_BASE_URL": "https://api.gateco.ai"
      }
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `gateco_retrieve` | Permission-aware retrieval (vector/keyword/hybrid/grep) |
| `gateco_ask` | Grounded answer synthesis with search modes (Pro+) |
| `gateco_check_access` | Dry-run access simulation (Pro+) |
| `gateco_list_connectors` | List connectors with readiness levels |
| `gateco_list_principals` | List identity principals |
| `gateco_resolve_principal` | Resolve a principal by email or provider subject |

All tools return markdown-formatted text. Denied content is never exposed — only denial
reasons and counts are shown.

---

## Development

```bash
pip install -e ".[dev]"
pytest -v

# Run MCP server tests
pytest tests/test_mcp/ -v

# With coverage
pytest --cov=src/gateco_sdk
```

---

## Links

- [Documentation](https://gateco.ai/docs)
- [Dashboard](https://app.gateco.ai)
- [GitHub](https://github.com/fortisil/gateco-sdk-python)
- [Bug Tracker](https://github.com/fortisil/gateco-sdk-python/issues)
- [Support](mailto:support@gateco.ai)

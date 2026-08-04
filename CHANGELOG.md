# Changelog

## [1.8.1] - 2026-08-04

### Added
- MCP registry listing metadata: `server.json` for the official MCP registry
  (server name `ai.gateco/gateco`) and the PyPI ownership marker in the README.
  No code changes.

## [1.8.0] - 2026-07-31

### Added
- Async ingestion jobs (Team plan and above): enqueue document/batch ingestion as background
  jobs with progress tracking, retries, and dead-lettering. Python: `client.ingest.jobs`
  (`enqueue/get/list/cancel/wait_for`); TypeScript: `client.ingest.jobs`
  (`enqueue/get/list/cancel/waitFor`).
- Resource tombstones: `client.ingest.delete_resource()` / `deleteResource()` removes an
  ingested resource's vectors, registry chunks, and gated resource.
- Source connections (Growth plan and above): `client.sources` — connect Google Drive,
  SharePoint, Confluence, or Notion; sync documents AND their permissions. Includes
  `acl_coverage()` / `aclCoverage()` reporting matched/unmatched principals, and
  `PlanFeatures.async_ingestion` / `PlanFeatures.source_connectors` typed fields.

### Changed
- Server-side: pipelines run for real (`POST /api/pipelines/{id}/run` enqueues a source-sync
  job group; the former 501 is gone); re-syncing unchanged content skips embedding entirely
  (position-keyed pre-embedding dedup); imported source ACLs create REBAC viewer relationships
  and a DRAFT policy that admins review and activate.

## [1.7.0] - 2026-07-31

### Added
- `chunking` override on ingest document/batch: `{strategy, chunk_size, chunk_overlap}` with
  strategies `characters`, `tokens`, `recursive`, `markdown` (heading-aware with heading-path
  context prefixes). Applies per request; each connector pins its default chunking generation
  write-once on first ingest (existing connectors keep v1 characters, fresh connectors get v2
  markdown at 512 tokens / 15% overlap).
- `embedding` override on ingest document/batch: `{provider, model, dimensions, base_url}` with
  providers `openai`, `openai_compatible` (any OpenAI-wire endpoint: Ollama, TEI, vLLM — keeps
  embeddings fully self-hosted), `cohere`, and `voyage`. Requests never carry API keys; keys
  resolve server-side from provider env vars. The connector records the resolved provider profile
  and server-side query embedding follows it automatically.

### Changed
- Server-side: the default file-extraction backend is now self-hosted Docling (PDF/DOCX/PPTX/
  images parse locally with no content egress). LlamaParse cloud extraction is an explicit
  opt-in via EXTRACTION_BACKEND=llama_parse.

## [1.6.0] - 2026-07-31

### Added
- `PlanLimits.ingested_documents` and `PlanFeatures.batch_ingestion` typed fields, matching the new
  backend plan catalog keys (monthly ingested-document limits: free 100 / team 10k / growth 100k /
  enterprise unlimited).
- Docs: `client.ingest.batch()` requires the `batch_ingestion` feature (Team plan and above);
  free-plan orgs receive `EntitlementError` with `reason="feature_not_in_plan"`.

### Changed
- Server-side (no client code change needed): all ingestion endpoints now accept `X-API-Key`
  authentication in addition to JWT, batch ingestion coalesces embedding calls (large batches are
  significantly faster), and re-ingesting a document that produces fewer chunks now prunes the stale
  chunks from both the registry and the vector DB.

## [1.5.1] - 2026-07-28

No functional changes. Released to verify the switch to Trusted Publishing (OIDC) — this version was
published with no stored PyPI API token. Identical in behaviour to 1.5.0.

## [1.5.0] - 2026-07-28

### Added
- `EntitlementError.reason` — distinguishes the two conditions that share a 403 `ENTITLEMENT_REQUIRED`:
  `"feature_not_in_plan"` (the plan does not grant the feature) and `"resource_limit_reached"` (the plan
  grants it, but the org's quota is full). Both carry `upgrade_to`, so previously they were
  indistinguishable without parsing the message string.
- `EntitlementError.is_limit` / `EntitlementError.is_feature_gate` convenience properties. When `reason`
  is absent (older backend), both report a feature gate, preserving pre-1.5.0 behaviour.

### Fixed
- MCP tools no longer advise "Requires <plan> plan." when a plan *quota* is exhausted. A user who hit the
  connector limit was told to upgrade when deleting a connector would have resolved it; the tool now says
  "Delete an unused resource to free a slot." and mentions upgrading only as the secondary option.
- `error_from_response()` no longer raises `UnboundLocalError` when the response body is
  `{"detail": "<string>"}` rather than an object.

### Requires
- Backend with `error.reason` on entitlement responses (2026-07-28 or later). Against older backends the
  SDK degrades gracefully: `reason` is `None` and `is_feature_gate` is `True`.

## [1.4.0] - 2026-06-05

### Added
- `client.users.update_org_settings()` now accepts `clear_llm_api_key=True` and `llm_key_query_cap` to manage the per-org LLM API key and soft rotation cap
- `LlmCreditExhaustedError` — raised when the org's 100 paid-tier fallback synthesis credits are exhausted
- `LlmKeyNotConfiguredError` — raised when answer synthesis is attempted on the free tier without a configured API key
- `Answer.cap_reached` field — `True` when the latest response has hit the admin-configured query cap (synthesis still succeeds; rotate key to reset counter)
- MCP `gateco_ask` tool now appends a key-rotation reminder when `cap_reached` is set

### Fixed
- `error_from_response()` now correctly parses FastAPI's `{"detail": {"code": "...", "message": "..."}}` error envelope; previously all backend error codes were lost and errors fell back to generic messages

## [1.2.0] - 2026-05-25

### Added
- `client.users` namespace: `get_me()`, `update_me(name)` — read and update the authenticated user profile
- `client.principals.resolve()` — find an active principal by email or provider_subject (was missing from the principals resource)
- `client.billing.get_subscription()` — fetch current subscription with `billing_period` and renewal date
- `client.billing.create_portal()` — create a Stripe billing portal session with redirect URL
- `client.dashboard.get_stats(sparklines=True)` — optional sparklines parameter for time-series KPI arrays
- `client.simulator.run_batch_preview()` — evaluate one search against up to 5 principals in parallel (Growth+)
- `scripts/check_contract.py` — CI contract checker: walks OpenAPI spec and asserts SDK coverage

### Fixed
- `client.auth.login()` now correctly unwraps the `{user, tokens}` response envelope (previously stored no token)
- `client.connectors.update_search_config()` and `update_ingestion_config()` now wrap request body in `{search_config:...}` / `{ingestion_config:...}` (previously sent bare body, causing 422)

## [1.1.0] - 2026-04-29

### Added
- `client.relationships` namespace: `create()`, `list()`, `delete()`

## [1.0.0] - 2026-04-29

### Added
- API key authentication support (`client.api_keys.*`) — create, list, delete, rotate
- Onboarding status and dismissal (`client.onboarding.*`) — 6 computed steps, checklist dismissal
- Production-ready release with full namespace coverage (17 namespaces)
- `ApiKeysResource` and `OnboardingResource` exported from top-level `gateco_sdk` package
- PyPI classifiers: `Development Status :: 5 - Production/Stable`, `Intended Audience :: Developers`, Python 3.10/3.11/3.12 markers

### Changed
- Initial stable release — v0.1.0 was pre-release
- Version bumped from `0.1.0` to `1.0.0` in `pyproject.toml` and `_version.py`

## [0.1.0] - Initial pre-release

- 15 resource namespaces: answers, audit, auth, billing, connectors, dashboard,
  data_catalog, identity_providers, ingest, pipelines, policies, principals,
  retroactive, retrievals, simulator
- Async client (`AsyncGatecoClient`) with httpx transport and token refresh
- Synchronous wrapper (`GatecoClient`) with per-call `asyncio.run()`
- MCP server (`gateco[mcp]`) with 6 tools on stdio transport
- CLI (`gateco`) with login, connectors, principals, suggest-classifications, and mcp subcommands

# Changelog

## [1.2.0] - 2026-05-25

### Added
- `client.users` namespace: `get_me()`, `update_me(name)` — read and update the authenticated user profile
- `client.principals.resolve()` — find an active principal by email or provider_subject (was missing from the principals resource)
- `client.billing.get_subscription()` — fetch current subscription with `billing_period` and renewal date
- `client.billing.create_portal()` — create a Stripe billing portal session with redirect URL
- `client.dashboard.get_stats(sparklines=True)` — optional sparklines parameter for time-series KPI arrays
- `client.simulator.run_batch_preview()` — evaluate one search against up to 5 principals in parallel (Pro+)
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

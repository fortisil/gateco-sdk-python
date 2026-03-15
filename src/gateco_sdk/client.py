"""Gateco SDK clients — async and synchronous."""

from __future__ import annotations

import asyncio
import functools
from typing import Any

from gateco_sdk._auth import TokenManager
from gateco_sdk._transport import Transport
from gateco_sdk.errors import AuthenticationError
from gateco_sdk.resources.audit import AuditResource
from gateco_sdk.resources.auth import AuthResource
from gateco_sdk.resources.billing import BillingResource
from gateco_sdk.resources.connectors import ConnectorsResource
from gateco_sdk.resources.dashboard import DashboardResource
from gateco_sdk.resources.data_catalog import DataCatalogResource
from gateco_sdk.resources.identity_providers import IdentityProvidersResource
from gateco_sdk.resources.ingestion import IngestionResource
from gateco_sdk.resources.pipelines import PipelinesResource
from gateco_sdk.resources.policies import PoliciesResource
from gateco_sdk.resources.principals import PrincipalsResource
from gateco_sdk.resources.retroactive import RetroactiveResource
from gateco_sdk.resources.retrievals import RetrievalsResource
from gateco_sdk.resources.simulator import SimulatorResource
from gateco_sdk.types.auth import TokenResponse


class AsyncGatecoClient:
    """Async client for the Gateco API.

    Args:
        base_url: Root URL of the Gateco API.
        api_key: Optional static API key (mutually exclusive with login flow).
        timeout: HTTP request timeout in seconds.
        max_retries: Maximum automatic retries for 429 / 5xx responses.
        retry_backoff_factor: Multiplier for exponential back-off.

    Usage::

        async with AsyncGatecoClient("https://api.gateco.dev") as client:
            await client.login("user@example.com", "secret")
            connectors = await client.connectors.list()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_backoff_factor: float = 0.5,
    ) -> None:
        self._transport = Transport(
            base_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff_factor=retry_backoff_factor,
        )
        self._token_manager = TokenManager(api_key=api_key)

        # Lazy resource namespaces
        self._auth: AuthResource | None = None
        self._connectors: ConnectorsResource | None = None
        self._ingest: IngestionResource | None = None
        self._retrievals: RetrievalsResource | None = None
        self._policies: PoliciesResource | None = None
        self._identity_providers: IdentityProvidersResource | None = None
        self._principals: PrincipalsResource | None = None
        self._data_catalog: DataCatalogResource | None = None
        self._pipelines: PipelinesResource | None = None
        self._billing: BillingResource | None = None
        self._audit: AuditResource | None = None
        self._simulator: SimulatorResource | None = None
        self._dashboard: DashboardResource | None = None
        self._retroactive: RetroactiveResource | None = None

    # ------------------------------------------------------------------
    # Resource namespaces (lazy)
    # ------------------------------------------------------------------

    @property
    def auth(self) -> AuthResource:
        """Authentication operations."""
        if self._auth is None:
            self._auth = AuthResource(self)
        return self._auth

    @property
    def connectors(self) -> ConnectorsResource:
        """Connector CRUD and management."""
        if self._connectors is None:
            self._connectors = ConnectorsResource(self)
        return self._connectors

    @property
    def ingest(self) -> IngestionResource:
        """Document ingestion operations."""
        if self._ingest is None:
            self._ingest = IngestionResource(self)
        return self._ingest

    @property
    def retrievals(self) -> RetrievalsResource:
        """Permission-gated retrieval operations."""
        if self._retrievals is None:
            self._retrievals = RetrievalsResource(self)
        return self._retrievals

    @property
    def policies(self) -> PoliciesResource:
        """Policy CRUD and lifecycle management."""
        if self._policies is None:
            self._policies = PoliciesResource(self)
        return self._policies

    @property
    def identity_providers(self) -> IdentityProvidersResource:
        """Identity provider CRUD and sync."""
        if self._identity_providers is None:
            self._identity_providers = IdentityProvidersResource(self)
        return self._identity_providers

    @property
    def principals(self) -> PrincipalsResource:
        """Principal listing and detail."""
        if self._principals is None:
            self._principals = PrincipalsResource(self)
        return self._principals

    @property
    def data_catalog(self) -> DataCatalogResource:
        """Data catalog browsing and resource metadata updates."""
        if self._data_catalog is None:
            self._data_catalog = DataCatalogResource(self)
        return self._data_catalog

    @property
    def pipelines(self) -> PipelinesResource:
        """Pipeline CRUD and run management."""
        if self._pipelines is None:
            self._pipelines = PipelinesResource(self)
        return self._pipelines

    @property
    def billing(self) -> BillingResource:
        """Billing, plans, usage, invoices, and subscriptions."""
        if self._billing is None:
            self._billing = BillingResource(self)
        return self._billing

    @property
    def audit(self) -> AuditResource:
        """Audit log listing and export."""
        if self._audit is None:
            self._audit = AuditResource(self)
        return self._audit

    @property
    def simulator(self) -> SimulatorResource:
        """Access simulation (dry-run policy evaluation)."""
        if self._simulator is None:
            self._simulator = SimulatorResource(self)
        return self._simulator

    @property
    def dashboard(self) -> DashboardResource:
        """Dashboard aggregated statistics."""
        if self._dashboard is None:
            self._dashboard = DashboardResource(self)
        return self._dashboard

    @property
    def retroactive(self) -> RetroactiveResource:
        """Retroactive vector registration."""
        if self._retroactive is None:
            self._retroactive = RetroactiveResource(self)
        return self._retroactive

    # ------------------------------------------------------------------
    # Convenience auth methods on the client itself
    # ------------------------------------------------------------------

    async def login(self, email: str, password: str) -> TokenResponse:
        """Shortcut for ``client.auth.login(...)``."""
        return await self.auth.login(email, password)

    async def signup(
        self, name: str, email: str, password: str, organization_name: str
    ) -> TokenResponse:
        """Shortcut for ``client.auth.signup(...)``."""
        return await self.auth.signup(name, email, password, organization_name)

    # ------------------------------------------------------------------
    # Internal request with auto-refresh
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        authenticate: bool = True,
    ) -> dict[str, Any] | None:
        """Send an authenticated request, refreshing the token if needed.

        Args:
            method: HTTP method.
            path: URL path.
            json: Request body.
            params: Query parameters.
            authenticate: Whether to attach auth headers. Set ``False`` for
                login/signup/refresh which supply their own credentials.
        """
        headers: dict[str, str] = {}

        if authenticate:
            # Primary refresh check: proactively refresh if token is near expiry.
            if self._token_manager.needs_refresh():
                await self._do_refresh()
            headers = self._token_manager.get_auth_headers()

        try:
            return await self._transport.request(
                method, path, json=json, params=params, headers=headers
            )
        except AuthenticationError:
            if not authenticate or not self._token_manager.refresh_token:
                raise
            # Fallback refresh on 401: token may have been revoked server-side.
            await self._do_refresh()
            headers = self._token_manager.get_auth_headers()
            return await self._transport.request(
                method, path, json=json, params=params, headers=headers
            )

    async def _do_refresh(self) -> None:
        """Perform a token refresh under a lock to prevent concurrent refreshes."""
        async with self._token_manager.lock:
            # Double-check after acquiring the lock — another coroutine may have
            # already refreshed.
            if not self._token_manager.needs_refresh():
                return
            refresh_token = self._token_manager.refresh_token
            if refresh_token is None:
                return
            data = await self._transport.request(
                "POST",
                "/api/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            if data:
                token_resp = TokenResponse.model_validate(data)
                self._token_manager.set_tokens(
                    token_resp.access_token,
                    token_resp.refresh_token,
                )

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> AsyncGatecoClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP transport."""
        await self._transport.close()


# ======================================================================
# Synchronous wrapper
# ======================================================================


class GatecoClient:
    """Synchronous wrapper around :class:`AsyncGatecoClient`.

    Provides the same API surface but blocks on each call using an internal
    event loop.  Suitable for scripts and notebooks where ``async/await`` is
    not convenient.

    Args:
        base_url: Root URL of the Gateco API.
        api_key: Optional static API key.
        timeout: HTTP request timeout in seconds.
        max_retries: Maximum automatic retries for 429 / 5xx.
        retry_backoff_factor: Multiplier for exponential back-off.

    Usage::

        with GatecoClient("https://api.gateco.dev") as client:
            client.login("user@example.com", "secret")
            page = client.connectors.list()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_backoff_factor: float = 0.5,
    ) -> None:
        self._async_client = AsyncGatecoClient(
            base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff_factor=retry_backoff_factor,
        )
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop

    def _run(self, coro: Any) -> Any:
        return self._get_loop().run_until_complete(coro)

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> TokenResponse:
        """Authenticate with email and password."""
        return self._run(self._async_client.login(email, password))

    def signup(
        self, name: str, email: str, password: str, organization_name: str
    ) -> TokenResponse:
        """Create a new account and organisation."""
        return self._run(
            self._async_client.signup(name, email, password, organization_name)
        )

    # ------------------------------------------------------------------
    # Resource namespaces (sync wrappers)
    # ------------------------------------------------------------------

    @property
    def auth(self) -> _SyncAuthProxy:
        return _SyncAuthProxy(self._async_client.auth, self._run)

    @property
    def connectors(self) -> _SyncConnectorsProxy:
        return _SyncConnectorsProxy(self._async_client.connectors, self._run)

    @property
    def ingest(self) -> _SyncIngestionProxy:
        return _SyncIngestionProxy(self._async_client.ingest, self._run)

    @property
    def retrievals(self) -> _SyncRetrievalsProxy:
        return _SyncRetrievalsProxy(self._async_client.retrievals, self._run)

    @property
    def policies(self) -> _SyncPoliciesProxy:
        return _SyncPoliciesProxy(self._async_client.policies, self._run)

    @property
    def identity_providers(self) -> _SyncIdentityProvidersProxy:
        return _SyncIdentityProvidersProxy(
            self._async_client.identity_providers, self._run
        )

    @property
    def principals(self) -> _SyncPrincipalsProxy:
        return _SyncPrincipalsProxy(self._async_client.principals, self._run)

    @property
    def data_catalog(self) -> _SyncDataCatalogProxy:
        return _SyncDataCatalogProxy(self._async_client.data_catalog, self._run)

    @property
    def pipelines(self) -> _SyncPipelinesProxy:
        return _SyncPipelinesProxy(self._async_client.pipelines, self._run)

    @property
    def billing(self) -> _SyncBillingProxy:
        return _SyncBillingProxy(self._async_client.billing, self._run)

    @property
    def audit(self) -> _SyncAuditProxy:
        return _SyncAuditProxy(self._async_client.audit, self._run)

    @property
    def simulator(self) -> _SyncSimulatorProxy:
        return _SyncSimulatorProxy(self._async_client.simulator, self._run)

    @property
    def dashboard(self) -> _SyncDashboardProxy:
        return _SyncDashboardProxy(self._async_client.dashboard, self._run)

    @property
    def retroactive(self) -> _SyncRetroactiveProxy:
        return _SyncRetroactiveProxy(self._async_client.retroactive, self._run)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> GatecoClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP transport and event loop."""
        self._run(self._async_client.close())
        if self._loop is not None and not self._loop.is_closed():
            self._loop.close()
            self._loop = None


# ======================================================================
# Sync proxy classes
# ======================================================================


class _SyncProxy:
    """Base class for synchronous resource proxies."""

    def __init__(self, async_resource: Any, runner: Any) -> None:
        self._async = async_resource
        self._run = runner


class _SyncAuthProxy(_SyncProxy):
    def login(self, email: str, password: str) -> TokenResponse:
        return self._run(self._async.login(email, password))

    def signup(
        self, name: str, email: str, password: str, organization_name: str
    ) -> TokenResponse:
        return self._run(self._async.signup(name, email, password, organization_name))

    def refresh(self) -> TokenResponse:
        return self._run(self._async.refresh())

    def logout(self) -> None:
        return self._run(self._async.logout())


class _SyncConnectorsProxy(_SyncProxy):
    def list(self, page: int = 1, per_page: int = 20) -> Any:
        return self._run(self._async.list(page, per_page))

    def get(self, connector_id: str) -> Any:
        return self._run(self._async.get(connector_id))

    def create(self, name: str, type: str, config: dict | None = None, **kwargs: Any) -> Any:
        return self._run(self._async.create(name, type, config, **kwargs))

    def update(self, connector_id: str, **kwargs: Any) -> Any:
        return self._run(self._async.update(connector_id, **kwargs))

    def delete(self, connector_id: str) -> None:
        return self._run(self._async.delete(connector_id))

    def test(self, connector_id: str) -> Any:
        return self._run(self._async.test(connector_id))

    def bind(self, connector_id: str, bindings: list) -> Any:
        return self._run(self._async.bind(connector_id, bindings))

    def get_search_config(self, connector_id: str) -> dict:
        return self._run(self._async.get_search_config(connector_id))

    def update_search_config(self, connector_id: str, search_config: dict) -> dict:
        return self._run(self._async.update_search_config(connector_id, search_config))

    def get_ingestion_config(self, connector_id: str) -> dict:
        return self._run(self._async.get_ingestion_config(connector_id))

    def update_ingestion_config(self, connector_id: str, ingestion_config: dict) -> dict:
        return self._run(self._async.update_ingestion_config(connector_id, ingestion_config))

    def get_coverage(self, connector_id: str) -> Any:
        return self._run(self._async.get_coverage(connector_id))

    def suggest_classifications(self, connector_id: str, **kwargs: Any) -> Any:
        return self._run(self._async.suggest_classifications(connector_id, **kwargs))

    def apply_suggestions(self, connector_id: str, suggestions: list) -> Any:
        return self._run(self._async.apply_suggestions(connector_id, suggestions))


class _SyncIngestionProxy(_SyncProxy):
    def document(
        self,
        connector_id: str,
        external_resource_id: str,
        text: str,
        **kwargs: Any,
    ) -> Any:
        return self._run(
            self._async.document(connector_id, external_resource_id, text, **kwargs)
        )

    def batch(
        self,
        connector_id: str,
        records: list[dict[str, Any]],
        **kwargs: Any,
    ) -> Any:
        return self._run(self._async.batch(connector_id, records, **kwargs))


class _SyncRetrievalsProxy(_SyncProxy):
    def execute(self, query_vector: list[float] | None = None, **kwargs: Any) -> Any:
        return self._run(self._async.execute(query_vector, **kwargs))

    def list(self, page: int = 1, per_page: int = 20, **filters: Any) -> Any:
        return self._run(self._async.list(page, per_page, **filters))

    def get(self, retrieval_id: str) -> Any:
        return self._run(self._async.get(retrieval_id))


class _SyncPoliciesProxy(_SyncProxy):
    def list(self, page: int = 1, per_page: int = 20) -> Any:
        return self._run(self._async.list(page, per_page))

    def get(self, policy_id: str) -> Any:
        return self._run(self._async.get(policy_id))

    def create(
        self,
        name: str,
        type: str,
        effect: str,
        **kwargs: Any,
    ) -> Any:
        return self._run(self._async.create(name, type, effect, **kwargs))

    def update(self, policy_id: str, **kwargs: Any) -> Any:
        return self._run(self._async.update(policy_id, **kwargs))

    def delete(self, policy_id: str) -> None:
        return self._run(self._async.delete(policy_id))

    def activate(self, policy_id: str) -> Any:
        return self._run(self._async.activate(policy_id))

    def archive(self, policy_id: str) -> Any:
        return self._run(self._async.archive(policy_id))


class _SyncIdentityProvidersProxy(_SyncProxy):
    def list(self, page: int = 1, per_page: int = 20) -> Any:
        return self._run(self._async.list(page, per_page))

    def get(self, idp_id: str) -> Any:
        return self._run(self._async.get(idp_id))

    def create(self, name: str, type: str, **kwargs: Any) -> Any:
        return self._run(self._async.create(name, type, **kwargs))

    def update(self, idp_id: str, **kwargs: Any) -> Any:
        return self._run(self._async.update(idp_id, **kwargs))

    def delete(self, idp_id: str) -> None:
        return self._run(self._async.delete(idp_id))

    def sync(self, idp_id: str) -> Any:
        return self._run(self._async.sync(idp_id))


class _SyncPrincipalsProxy(_SyncProxy):
    def list(self, page: int = 1, per_page: int = 20) -> Any:
        return self._run(self._async.list(page, per_page))

    def get(self, principal_id: str) -> Any:
        return self._run(self._async.get(principal_id))


class _SyncDataCatalogProxy(_SyncProxy):
    def list(self, page: int = 1, per_page: int = 20, **kwargs: Any) -> Any:
        return self._run(self._async.list(page, per_page, **kwargs))

    def get(self, resource_id: str) -> Any:
        return self._run(self._async.get(resource_id))

    def update(self, resource_id: str, **kwargs: Any) -> Any:
        return self._run(self._async.update(resource_id, **kwargs))


class _SyncPipelinesProxy(_SyncProxy):
    def list(self, page: int = 1, per_page: int = 20) -> Any:
        return self._run(self._async.list(page, per_page))

    def get(self, pipeline_id: str) -> Any:
        return self._run(self._async.get(pipeline_id))

    def create(self, name: str, source_connector_id: str, **kwargs: Any) -> Any:
        return self._run(self._async.create(name, source_connector_id, **kwargs))

    def update(self, pipeline_id: str, **kwargs: Any) -> Any:
        return self._run(self._async.update(pipeline_id, **kwargs))

    def get_runs(self, pipeline_id: str) -> Any:
        return self._run(self._async.get_runs(pipeline_id))

    def run(self, pipeline_id: str) -> Any:
        return self._run(self._async.run(pipeline_id))


class _SyncBillingProxy(_SyncProxy):
    def get_plans(self) -> Any:
        return self._run(self._async.get_plans())

    def get_usage(self) -> Any:
        return self._run(self._async.get_usage())

    def get_invoices(self, page: int = 1, per_page: int = 20) -> Any:
        return self._run(self._async.get_invoices(page, per_page))

    def get_subscription(self) -> Any:
        return self._run(self._async.get_subscription())

    def start_checkout(self, plan_id: str, billing_period: str = "monthly") -> Any:
        return self._run(self._async.start_checkout(plan_id, billing_period))

    def create_portal(self, return_url: str | None = None) -> Any:
        return self._run(self._async.create_portal(return_url))


class _SyncAuditProxy(_SyncProxy):
    def list(self, page: int = 1, per_page: int = 20, **kwargs: Any) -> Any:
        return self._run(self._async.list(page, per_page, **kwargs))

    def export_csv(self, **kwargs: Any) -> Any:
        return self._run(self._async.export_csv(**kwargs))


class _SyncSimulatorProxy(_SyncProxy):
    def run(self, principal_id: str, **kwargs: Any) -> Any:
        return self._run(self._async.run(principal_id, **kwargs))


class _SyncDashboardProxy(_SyncProxy):
    def get_stats(self) -> Any:
        return self._run(self._async.get_stats())


class _SyncRetroactiveProxy(_SyncProxy):
    def register(self, connector_id: str, **kwargs: Any) -> Any:
        return self._run(self._async.register(connector_id, **kwargs))

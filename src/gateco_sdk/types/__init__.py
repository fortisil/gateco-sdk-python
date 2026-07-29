"""Pydantic models for Gateco API request/response types."""

from gateco_sdk.types.answers import Answer, Citation
from gateco_sdk.types.audit import (
    AuditEvent,
    AuditEventType,
    AuditExportRequest,
)
from gateco_sdk.types.auth import (
    LoginRequest,
    Organization,
    SignupRequest,
    TokenResponse,
    User,
)
from gateco_sdk.types.billing import (
    CheckoutRequest,
    CheckoutResponse,
    Invoice,
    Plan,
    PlanFeatures,
    PlanLimits,
    Subscription,
    Usage,
    UsageMetric,
)
from gateco_sdk.types.common import PaginatedResponse, PaginationMeta
from gateco_sdk.types.connectors import (
    BindingEntry,
    BindResult,
    Connector,
    CoverageDetail,
    CreateConnectorRequest,
    IngestionConfig,
    SearchConfig,
    TestConnectorResponse,
)
from gateco_sdk.types.dashboard import DashboardSparklines, DashboardStats
from gateco_sdk.types.data_catalog import (
    DataCatalogFilters,
    GatedResource,
    GatedResourceDetail,
    ResourceChunk,
)
from gateco_sdk.types.identity_providers import (
    CreateIdentityProviderRequest,
    IdentityProvider,
    SyncConfig,
)
from gateco_sdk.types.ingestion import (
    BatchIngestRequest,
    BatchIngestResponse,
    IngestDocumentRequest,
    IngestDocumentResponse,
    PreEmbeddedChunk,
)
from gateco_sdk.types.pipelines import (
    CreatePipelineRequest,
    EnvelopeConfig,
    Pipeline,
    PipelineRun,
)
from gateco_sdk.types.policies import (
    CreatePolicyRequest,
    Policy,
    PolicyCondition,
    PolicyEffect,
    PolicyRule,
    PolicyStatus,
    PolicyType,
)
from gateco_sdk.types.groups import PrincipalGroup
from gateco_sdk.types.principals import Principal, PrincipalAttributes
from gateco_sdk.types.retroactive import (
    RetroactiveRegisterRequest,
    RetroactiveRegisterResponse,
)
from gateco_sdk.types.retrievals import (
    DenialReason,
    ExecuteRetrievalRequest,
    FilterResult,
    PolicyTrace,
    RetrievalOutcome,
    SecuredRetrieval,
)
from gateco_sdk.types.simulator import SimulationRequest, SimulationResult

__all__ = [
    # answers
    "Answer",
    "Citation",
    # common
    "PaginationMeta",
    "PaginatedResponse",
    # auth
    "LoginRequest",
    "SignupRequest",
    "TokenResponse",
    "User",
    "Organization",
    # connectors
    "Connector",
    "CreateConnectorRequest",
    "TestConnectorResponse",
    "SearchConfig",
    "IngestionConfig",
    "BindingEntry",
    "BindResult",
    "CoverageDetail",
    # ingestion
    "IngestDocumentRequest",
    "IngestDocumentResponse",
    "BatchIngestRequest",
    "BatchIngestResponse",
    "PreEmbeddedChunk",
    # retrievals
    "ExecuteRetrievalRequest",
    "SecuredRetrieval",
    "RetrievalOutcome",
    "FilterResult",
    "DenialReason",
    "PolicyTrace",
    # policies
    "Policy",
    "PolicyRule",
    "PolicyCondition",
    "CreatePolicyRequest",
    "PolicyType",
    "PolicyStatus",
    "PolicyEffect",
    # identity providers
    "IdentityProvider",
    "CreateIdentityProviderRequest",
    "SyncConfig",
    # principals
    "Principal",
    "PrincipalAttributes",
    # groups
    "PrincipalGroup",
    # data catalog
    "GatedResource",
    "GatedResourceDetail",
    "ResourceChunk",
    "DataCatalogFilters",
    # pipelines
    "Pipeline",
    "PipelineRun",
    "CreatePipelineRequest",
    "EnvelopeConfig",
    # billing
    "Plan",
    "PlanFeatures",
    "PlanLimits",
    "Usage",
    "UsageMetric",
    "Invoice",
    "Subscription",
    "CheckoutRequest",
    "CheckoutResponse",
    # audit
    "AuditEvent",
    "AuditEventType",
    "AuditExportRequest",
    # simulator
    "SimulationRequest",
    "SimulationResult",
    # dashboard
    "DashboardSparklines",
    "DashboardStats",
    # retroactive
    "RetroactiveRegisterRequest",
    "RetroactiveRegisterResponse",
]

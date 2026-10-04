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
from gateco_sdk.types.labels import (
    CLASSIFICATIONS,
    SENSITIVITIES,
    Classification,
    Sensitivity,
)
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
    "CLASSIFICATIONS",
    "SENSITIVITIES",
    # answers
    "Answer",
    # audit
    "AuditEvent",
    "AuditEventType",
    "AuditExportRequest",
    "BatchIngestRequest",
    "BatchIngestResponse",
    "BindResult",
    "BindingEntry",
    "CheckoutRequest",
    "CheckoutResponse",
    "Citation",
    "Classification",
    # connectors
    "Connector",
    "CoverageDetail",
    "CreateConnectorRequest",
    "CreateIdentityProviderRequest",
    "CreatePipelineRequest",
    "CreatePolicyRequest",
    # dashboard
    "DashboardSparklines",
    "DashboardStats",
    "DataCatalogFilters",
    "DenialReason",
    "EnvelopeConfig",
    # retrievals
    "ExecuteRetrievalRequest",
    "FilterResult",
    # data catalog
    "GatedResource",
    "GatedResourceDetail",
    # identity providers
    "IdentityProvider",
    # ingestion
    "IngestDocumentRequest",
    "IngestDocumentResponse",
    "IngestionConfig",
    "Invoice",
    # auth
    "LoginRequest",
    "Organization",
    "PaginatedResponse",
    # common
    "PaginationMeta",
    # pipelines
    "Pipeline",
    "PipelineRun",
    # billing
    "Plan",
    "PlanFeatures",
    "PlanLimits",
    # policies
    "Policy",
    "PolicyCondition",
    "PolicyEffect",
    "PolicyRule",
    "PolicyStatus",
    "PolicyTrace",
    "PolicyType",
    "PreEmbeddedChunk",
    # principals
    "Principal",
    "PrincipalAttributes",
    # groups
    "PrincipalGroup",
    "ResourceChunk",
    "RetrievalOutcome",
    # retroactive
    "RetroactiveRegisterRequest",
    "RetroactiveRegisterResponse",
    "SearchConfig",
    "SecuredRetrieval",
    "Sensitivity",
    "SignupRequest",
    # simulator
    "SimulationRequest",
    "SimulationResult",
    "Subscription",
    "SyncConfig",
    "TestConnectorResponse",
    "TokenResponse",
    "Usage",
    "UsageMetric",
    "User",
]

"""API resource namespaces."""

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

__all__ = [
    "AuthResource",
    "ConnectorsResource",
    "IngestionResource",
    "RetrievalsResource",
    "PoliciesResource",
    "IdentityProvidersResource",
    "PrincipalsResource",
    "DataCatalogResource",
    "PipelinesResource",
    "BillingResource",
    "AuditResource",
    "SimulatorResource",
    "DashboardResource",
    "RetroactiveResource",
]

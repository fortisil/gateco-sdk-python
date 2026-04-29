"""Gateco SDK — Official Python client for the Gateco API."""

from gateco_sdk._version import __version__
from gateco_sdk.client import AsyncGatecoClient, GatecoClient
from gateco_sdk.resources.api_keys import ApiKeysResource
from gateco_sdk.resources.onboarding import OnboardingResource

__all__ = [
    "__version__",
    "AsyncGatecoClient",
    "GatecoClient",
    "ApiKeysResource",
    "OnboardingResource",
]

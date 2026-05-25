#!/usr/bin/env python3
"""Contract checker: verify Python SDK exposes methods for all OpenAPI operationIds.

Loads packages/contracts/openapi.json, extracts every operationId, derives the
expected SDK resource + method name, and asserts the SDK class has that method.

Run: python scripts/check_contract.py
Exit: 0 if all covered, 1 if any gaps found.
"""

from __future__ import annotations

import importlib
import inspect
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_OPENAPI_PATH = _REPO_ROOT / "packages" / "contracts" / "openapi.json"
_SDK_SRC = Path(__file__).resolve().parents[2] / "src"

# Map operationId path segment → (SDK resource attribute name, resource class name)
_RESOURCE_MAP: dict[str, tuple[str, str]] = {
    "api_admin": None,          # admin routes not in SDK
    "db_health": None,          # infra health, not in SDK
    "health_db": None,
    "api_auth": ("auth", "AuthResource"),
    "api_plans": ("billing", "BillingResource"),
    "api_checkout": ("billing", "BillingResource"),
    "api_billing": ("billing", "BillingResource"),
    "api_webhooks": None,       # webhook receiver, not in SDK
    "api_connectors": ("connectors", "ConnectorsResource"),
    "api_ingestion": ("ingestion", "IngestionResource"),
    "api_data_catalog": ("data_catalog", "DataCatalogResource"),
    "api_policies": ("policies", "PoliciesResource"),
    "api_retrievals": ("retrievals", "RetrievalsResource"),
    "api_simulator": ("simulator", "SimulatorResource"),
    "api_answers": ("answers", "AnswersResource"),
    "api_audit_log": ("audit", "AuditResource"),
    "api_principals": ("principals", "PrincipalsResource"),
    "api_relationships": ("relationships", "RelationshipsResource"),
    "api_identity_providers": ("identity_providers", "IdentityProvidersResource"),
    "api_api_keys": ("api_keys", "ApiKeysResource"),
    "api_users": ("users", "UsersResource"),
    "api_organization": ("users", "UsersResource"),
    "api_onboarding": ("onboarding", "OnboardingResource"),
    "api_scim": None,           # SCIM is server-side only
    "api_pipelines": ("pipelines", "PipelinesResource"),
}

# operationId prefixes (before the resource segment) to skip
_SKIP_OPERATION_PREFIXES: set[str] = {
    "db_status", "health_db", "test_connection", "apply_setup", "retry_setup",
    "update_org_plan", "google_auth", "github_auth", "google_callback", "github_callback",
    "stripe_webhook",
}

# Methods we explicitly exclude from the check (webhook, OAuth server-side flows, etc.)
_SKIP_OPERATION_IDS: set[str] = {
    "stripe_webhook_api_webhooks_stripe_post",
    "db_status_api_admin_db_status_get",
    "test_connection_api_admin_db_test_post",
    "apply_setup_api_admin_db_apply_post",
    "retry_setup_api_admin_db_retry_post",
    "update_org_plan_api_admin_db_organizations__org_id__plan_patch",
    "health_db_health_db_get",
    "google_auth_api_auth_google_get",
    "github_auth_api_auth_github_get",
    "google_callback_api_auth_google_callback_get",
    "github_callback_api_auth_github_callback_get",
}


def _resolve_resource(path: str) -> tuple[str, str] | None:
    """Map an API path to the (resource_attr, class_name) for the SDK."""
    path = path.lstrip("/").replace("-", "_").replace("/", "_")
    for prefix, mapping in _RESOURCE_MAP.items():
        if path.startswith(prefix.lstrip("/")):
            return mapping
    return None


def _derive_method_name(operation_id: str) -> str:
    """Derive a snake_case SDK method name from an operationId.

    FastAPI operationIds look like: ``list_connectors_api_connectors_get``
    We want the human-readable prefix: ``list_connectors``.
    """
    # Strip the trailing ``_api_..._<method>`` suffix
    cleaned = re.sub(r"_api_.*$", "", operation_id)
    return cleaned


def _get_sdk_resource_methods(resource_attr: str, class_name: str) -> set[str]:
    """Import the SDK resource class and return its public async method names."""
    sys.path.insert(0, str(_SDK_SRC))
    try:
        mod = importlib.import_module(f"gateco_sdk.resources.{resource_attr.rstrip('s').replace('_', '_')}")
    except ModuleNotFoundError:
        try:
            mod = importlib.import_module(f"gateco_sdk.resources.{resource_attr}")
        except ModuleNotFoundError:
            return set()
    finally:
        sys.path.pop(0)

    for name, obj in inspect.getmembers(mod, inspect.isclass):
        if name == class_name or name.endswith("Resource"):
            return {
                m for m, _ in inspect.getmembers(obj, predicate=inspect.isfunction)
                if not m.startswith("_")
            }
    return set()


def main() -> int:
    if not _OPENAPI_PATH.exists():
        print(f"ERROR: OpenAPI spec not found at {_OPENAPI_PATH}")
        print("Run: cd packages/contracts && npm run generate")
        return 1

    with open(_OPENAPI_PATH) as f:
        spec = json.load(f)

    gaps: list[str] = []
    checked = 0
    skipped = 0

    _resource_method_cache: dict[str, set[str]] = {}

    for path, methods in spec.get("paths", {}).items():
        for http_method, op in methods.items():
            if http_method not in ("get", "post", "patch", "put", "delete"):
                continue
            operation_id: str = op.get("operationId", "")
            if not operation_id or operation_id in _SKIP_OPERATION_IDS:
                skipped += 1
                continue

            resource_info = _resolve_resource(path)
            if resource_info is None:
                skipped += 1
                continue

            resource_attr, class_name = resource_info
            method_name = _derive_method_name(operation_id)
            checked += 1

            if resource_attr not in _resource_method_cache:
                _resource_method_cache[resource_attr] = _get_sdk_resource_methods(resource_attr, class_name)

            sdk_methods = _resource_method_cache[resource_attr]
            if not sdk_methods:
                # Resource module missing entirely — report once
                gap = f"MISSING RESOURCE MODULE: {resource_attr} (class={class_name}) — needed for operationId={operation_id}"
                if gap not in gaps:
                    gaps.append(gap)
                continue

            # Allow partial name matching — SDK methods don't have to be named exactly
            # the same as the operationId prefix, but must be present in the class
            # Heuristic: check if any SDK method name contains the core action words
            action_words = {w for w in method_name.split("_") if len(w) > 2}
            found = any(
                all(word in sdk_method for word in action_words)
                for sdk_method in sdk_methods
            ) or method_name in sdk_methods

            if not found:
                gaps.append(
                    f"MISSING: {http_method.upper()} {path} → operationId={operation_id} "
                    f"→ expected ~{method_name} in {class_name} (have: {sorted(sdk_methods)[:5]}...)"
                )

    print(f"Contract check: {checked} operations checked, {skipped} skipped")
    if gaps:
        print(f"\n{len(gaps)} gap(s) found:\n")
        for gap in gaps:
            print(f"  ✗ {gap}")
        return 1

    print(f"✓ All {checked} operations are covered by the Python SDK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

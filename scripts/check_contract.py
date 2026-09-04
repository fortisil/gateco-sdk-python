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

# scripts/ -> sdk-python/ -> packages/ -> gateco/ (the monorepo root that holds packages/)
_MONOREPO_ROOT = Path(__file__).resolve().parents[3]
_OPENAPI_PATH = _MONOREPO_ROOT / "packages" / "contracts" / "openapi.json"
_SDK_SRC = Path(__file__).resolve().parents[2] / "src"

# URL prefix -> (client attribute, resource class, module under gateco_sdk.resources),
# or None when the prefix is deliberately outside the SDK (say why). Longest prefix
# wins. A prefix that appears in the spec and is missing here FAILS the check, so a
# new router cannot slip past unmapped.
_RESOURCE_MAP: dict[str, tuple[str, str, str] | None] = {
    "/": None,                           # root banner
    "/health": None,                     # liveness / readiness probes
    "/api/admin": None,                  # X-Admin-Token setup console, not a customer API
    "/api/platform": None,               # platform-admin console (require_platform_admin)
    "/api/webhooks": None,               # Stripe calls us
    "/api/marketplace": None,            # AWS Marketplace calls us
    "/api/scim": None,                   # the IdP calls us
    "/api/benchmark": None,              # Performance Self-Test: in-app, login-gated by ruling (2026-08-31)
    "/api/capabilities": None,           # public capability matrix consumed by the app
    "/api/auth": ("auth", "AuthResource", "auth"),
    "/api/plans": ("billing", "BillingResource", "billing"),
    "/api/checkout": ("billing", "BillingResource", "billing"),
    "/api/billing": ("billing", "BillingResource", "billing"),
    "/api/connectors": ("connectors", "ConnectorsResource", "connectors"),
    "/api/v1/ingest/jobs": ("ingest.jobs", "IngestionJobsResource", "ingestion_jobs"),
    "/api/v1/ingest": ("ingest", "IngestionResource", "ingestion"),
    "/api/v1/resources": ("data_catalog", "DataCatalogResource", "data_catalog"),
    "/api/v1/retroactive-register": ("retroactive", "RetroactiveResource", "retroactive"),
    "/api/data-catalog": ("data_catalog", "DataCatalogResource", "data_catalog"),
    "/api/policies": ("policies", "PoliciesResource", "policies"),
    "/api/retrievals": ("retrievals", "RetrievalsResource", "retrievals"),
    "/api/simulator": ("simulator", "SimulatorResource", "simulator"),
    "/api/answers": ("answers", "AnswersResource", "answers"),
    "/api/audit-log": ("audit", "AuditResource", "audit"),
    "/api/principals": ("principals", "PrincipalsResource", "principals"),
    "/api/groups": ("groups", "GroupsResource", "groups"),
    "/api/relationships": ("relationships", "RelationshipResource", "relationships"),
    "/api/identity-providers": ("identity_providers", "IdentityProvidersResource", "identity_providers"),
    "/api/api-keys": ("api_keys", "ApiKeysResource", "api_keys"),
    "/api/users": ("users", "UsersResource", "users"),
    "/api/organization": ("users", "UsersResource", "users"),
    "/api/team": ("users", "UsersResource", "users"),
    "/api/onboarding": ("onboarding", "OnboardingResource", "onboarding"),
    "/api/pipelines": ("pipelines", "PipelinesResource", "pipelines"),
    "/api/source-connections": ("sources", "SourceConnectionsResource", "source_connections"),
    "/api/dashboard": ("dashboard", "DashboardResource", "dashboard"),
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


_UNMAPPED = object()


def _resolve_resource(path: str):
    """(mapping, url_prefix) for the longest matching prefix; _UNMAPPED when none matches."""
    for prefix in sorted(_RESOURCE_MAP, key=len, reverse=True):
        if path == prefix or path.startswith(prefix.rstrip("/") + "/"):
            return _RESOURCE_MAP[prefix], prefix
    return _UNMAPPED, ""


def _derive_method_name(operation_id: str) -> str:
    """The FastAPI function name inside an operationId.

    FastAPI operationIds look like ``list_connectors_api_connectors_get``; we
    want ``list_connectors``.
    """
    return re.sub(r"_api_.*$", "", operation_id)


#: Route function name -> SDK method, where the SDK chose a different name on
#: purpose. Keep this list short and explain every entry.
_EXPLICIT_METHOD: dict[str, str] = {
    "deactivate_principal": "delete",      # SDK mirrors the HTTP verb; server soft-deactivates
    "list_runs": "get_runs",               # pipelines.get_runs(pipeline_id)
    "export_audit_log": "export_csv",      # audit.export_csv(...)
    "onboarding_status": "status",         # onboarding.status()
    "dismiss_onboarding": "dismiss",       # onboarding.dismiss()
    "list_plans": "get_plans",             # billing.get_plans()
    "ingest_document": "document",         # ingest.document(...)
    "retroactive_register": "register",    # retroactive.register(...)
}

#: Verbs the SDK spells differently from the route function.
_VERB_SYNONYMS: dict[str, set[str]] = {
    "deactivate": {"delete"},
    "remove": {"delete"},
    "patch": {"update"},
    "fetch": {"get"},
}

#: Operations the SDK deliberately does not expose, with the reason. A gap
#: that is not here fails the check, so new endpoints get an SDK method or an
#: entry with a reason, never silence.
KNOWN_GAPS: dict[str, str] = {
    "stream_audit_log": "server-sent events stream; SDKs expose list/export instead",
    "submit_profile": "onboarding profile form is app-only (plan Phase 6 decides)",
    "update_pipeline": "pipelines are app-managed in v1; SDK exposes create/get/list/run history",
    "run_pipeline": "pipelines are app-managed in v1; scheduled by the worker",
    "get_db_schema": "Search Config dialog helper; SDK method lands in plan Phase 5 (SDK parity)",
    "get_preflight": "connector preflight is app-only until plan Phase 5 (SDK parity)",
    "get_activation_stats": "dashboard activation card; app-only",
    "bulk_classify": "Data Catalog bulk classify; done in the app table (select rows / all), not the SDK",
    "list_team_invites": "team invites are managed in the app (Organization settings)",
    "create_team_invite": "team invites are managed in the app (Organization settings)",
    "revoke_team_invite": "team invites are managed in the app (Organization settings)",
}


def _static_segments(path: str, resource_prefix: str) -> list[str]:
    """Literal path segments after the resource root, e.g. ['resolve'] or ['runs']."""
    rest = path.removeprefix(resource_prefix)
    return [seg.replace("-", "_") for seg in rest.strip("/").split("/") if seg and not seg.startswith("{")]


def _covered(fn: str, path: str, resource_prefix: str, sdk_methods: set[str]) -> bool:
    """Does the SDK resource expose this route?

    1. An explicit mapping wins.
    2. A sub-resource route (``/principals/resolve``, ``/pipelines/{id}/runs``)
       needs a method whose name contains every literal segment.
    3. A root route (list/create/get/update/delete on the resource itself)
       needs a method named after the verb, or a listed synonym.
    """
    if fn in _EXPLICIT_METHOD:
        return _EXPLICIT_METHOD[fn] in sdk_methods
    segments = _static_segments(path, resource_prefix)
    if segments:
        # every token of every literal segment, singular or plural, in one method name
        tokens = [t.rstrip("s") for seg in segments for t in seg.split("_") if t]
        return any(all(t in m for t in tokens) for m in sdk_methods)
    verb = fn.split("_")[0]
    wanted = {verb} | _VERB_SYNONYMS.get(verb, set())
    return bool(wanted & sdk_methods)


def _get_sdk_resource_methods(class_name: str, module: str) -> set[str]:
    """Public method names of the named resource class."""
    sys.path.insert(0, str(_SDK_SRC))
    try:
        mod = importlib.import_module(f"gateco_sdk.resources.{module}")
    finally:
        sys.path.pop(0)
    cls = getattr(mod, class_name)
    return {m for m, _ in inspect.getmembers(cls, predicate=inspect.isfunction) if not m.startswith("_")}


def main() -> int:
    if not _OPENAPI_PATH.exists():
        print(f"ERROR: OpenAPI spec not found at {_OPENAPI_PATH}")
        print("Run: cd packages/contracts && npm run generate")
        return 1

    with open(_OPENAPI_PATH) as f:
        spec = json.load(f)

    gaps: list[str] = []
    known: list[str] = []
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

            mapping, url_prefix = _resolve_resource(path)
            if mapping is _UNMAPPED:
                gap = f"UNMAPPED PREFIX: {path} — add it to _RESOURCE_MAP (with a reason if it is not for the SDK)"
                if gap not in gaps:
                    gaps.append(gap)
                continue
            if mapping is None:
                skipped += 1
                continue
            resource_attr, class_name, module = mapping
            method_name = _derive_method_name(operation_id)
            checked += 1
            if resource_attr not in _resource_method_cache:
                _resource_method_cache[resource_attr] = _get_sdk_resource_methods(class_name, module)
            sdk_methods = _resource_method_cache[resource_attr]
            if not sdk_methods:
                gap = f"MISSING RESOURCE MODULE: {resource_attr} (class={class_name}) — needed for operationId={operation_id}"
                if gap not in gaps:
                    gaps.append(gap)
                continue
            if _covered(method_name, path, url_prefix, sdk_methods):
                continue
            if method_name in KNOWN_GAPS:
                known.append(f"{http_method.upper()} {path}: {KNOWN_GAPS[method_name]}")
                continue
            gaps.append(
                f"MISSING: {http_method.upper()} {path} → operationId={operation_id} "
                f"→ expected ~{method_name} in {class_name} (have: {sorted(sdk_methods)})"
            )
    print(f"Contract check: {checked} operations checked, {skipped} skipped, {len(known)} known gaps")
    for k in known:
        print(f"  · known gap: {k}")
    if gaps:
        print(f"\n{len(gaps)} gap(s) found:\n")
        for gap in gaps:
            print(f"  ✗ {gap}")
        return 1

    print(f"✓ All {checked} operations are covered by the Python SDK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

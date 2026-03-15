"""Gateco CLI — command-line interface for the Gateco SDK.

Uses only argparse (no extra dependencies). All output is JSON for machine
readability; errors are printed to stderr.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

_CRED_DIR = Path.home() / ".gateco"
_CRED_FILE = _CRED_DIR / "credentials.json"

_DEFAULT_BASE_URL = "http://localhost:8000/api"


def _load_credentials() -> dict[str, Any]:
    """Load credentials from env vars or ``~/.gateco/credentials.json``.

    Environment variables take precedence:
      - ``GATECO_API_KEY``  -> api_key
      - ``GATECO_BASE_URL`` -> base_url

    Returns:
        Dict with ``access_token`` and/or ``api_key``, ``refresh_token``,
        and ``base_url``.
    """
    creds: dict[str, Any] = {
        "access_token": None,
        "refresh_token": None,
        "api_key": None,
        "base_url": _DEFAULT_BASE_URL,
    }

    # File-based credentials
    if _CRED_FILE.exists():
        try:
            stored = json.loads(_CRED_FILE.read_text())
            creds["access_token"] = stored.get("access_token")
            creds["refresh_token"] = stored.get("refresh_token")
            creds["base_url"] = stored.get("base_url", _DEFAULT_BASE_URL)
        except (json.JSONDecodeError, OSError):
            pass

    # Env overrides
    env_key = os.environ.get("GATECO_API_KEY")
    if env_key:
        creds["api_key"] = env_key

    env_url = os.environ.get("GATECO_BASE_URL")
    if env_url:
        creds["base_url"] = env_url

    return creds


def _save_credentials(
    access_token: str,
    refresh_token: str | None,
    base_url: str,
) -> None:
    """Persist credentials to ``~/.gateco/credentials.json`` (mode 0600).

    Uses write-to-temp-then-rename for atomicity.
    """
    _CRED_DIR.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "base_url": base_url,
        },
        indent=2,
    )

    fd, tmp_path = tempfile.mkstemp(dir=str(_CRED_DIR), suffix=".tmp")
    try:
        os.write(fd, payload.encode())
        os.close(fd)
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        os.replace(tmp_path, str(_CRED_FILE))
    except Exception:
        os.close(fd) if not os.get_inheritable(fd) else None  # noqa: E501
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


# ---------------------------------------------------------------------------
# Client + async helpers
# ---------------------------------------------------------------------------


def _get_client() -> Any:
    """Build an ``AsyncGatecoClient`` from stored credentials.

    Returns an *unopened* client (caller should use ``async with``).
    """
    from gateco_sdk.client import AsyncGatecoClient

    creds = _load_credentials()

    api_key = creds.get("api_key")
    base_url = creds.get("base_url", _DEFAULT_BASE_URL)

    # Strip trailing /api if present -- the SDK expects the root URL and
    # prepends /api in its request paths.
    raw_base = str(base_url)
    if raw_base.endswith("/api"):
        raw_base = raw_base[: -len("/api")]

    client = AsyncGatecoClient(raw_base, api_key=api_key)

    # If we have JWT tokens, inject them into the token manager.
    access = creds.get("access_token")
    if access and not api_key:
        client._token_manager.set_tokens(
            access, creds.get("refresh_token")
        )

    return client


def _run(coro: Any) -> Any:
    """Run a coroutine via ``asyncio.run``."""
    return asyncio.run(coro)


def _output(data: Any) -> None:
    """Pretty-print *data* as JSON to stdout."""
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    print(json.dumps(data, indent=2, default=str))


def _error(msg: str) -> None:
    """Print an error message to stderr and exit with code 1."""
    print(json.dumps({"error": str(msg)}), file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


async def _cmd_login(args: argparse.Namespace) -> None:
    """Authenticate and store credentials."""
    from gateco_sdk.client import AsyncGatecoClient

    base_url = args.base_url
    raw_base = base_url
    if raw_base.endswith("/api"):
        raw_base = raw_base[: -len("/api")]

    async with AsyncGatecoClient(raw_base) as client:
        token_resp = await client.login(args.email, args.password)

    _save_credentials(
        token_resp.access_token,
        token_resp.refresh_token,
        base_url,
    )
    _output({"status": "ok", "user": token_resp.user.email if token_resp.user else None})


async def _cmd_ingest(args: argparse.Namespace) -> None:
    """Ingest a single file."""
    file_path = Path(args.file)
    if not file_path.exists():
        _error(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()
    if suffix not in (".txt", ".md"):
        _error(f"Unsupported file type '{suffix}'. Only .txt and .md files are supported.")

    text = file_path.read_text(encoding="utf-8")
    external_resource_id = file_path.name

    kwargs: dict[str, Any] = {}
    if args.classification:
        kwargs["classification"] = args.classification
    if args.sensitivity:
        kwargs["sensitivity"] = args.sensitivity
    if args.domain:
        kwargs["domain"] = args.domain

    async with _get_client() as client:
        result = await client.ingest.document(
            connector_id=args.connector_id,
            external_resource_id=external_resource_id,
            text=text,
            **kwargs,
        )
    _output(result)


async def _cmd_ingest_batch(args: argparse.Namespace) -> None:
    """Ingest all matching files from a directory."""
    directory = Path(args.directory)
    if not directory.is_dir():
        _error(f"Directory not found: {directory}")

    glob_pattern = args.glob or "*.txt"
    files = sorted(directory.glob(glob_pattern))

    # Filter to supported types
    supported = (".txt", ".md")
    files = [f for f in files if f.suffix.lower() in supported and f.is_file()]

    if not files:
        _error(f"No supported files matching '{glob_pattern}' in {directory}")

    records = []
    for f in files:
        records.append(
            {
                "external_resource_id": f.name,
                "text": f.read_text(encoding="utf-8"),
            }
        )

    async with _get_client() as client:
        result = await client.ingest.batch(
            connector_id=args.connector_id,
            records=records,
        )
    _output(result)


async def _cmd_retrieve(args: argparse.Namespace) -> None:
    """Execute a permission-gated retrieval."""
    vec_path = Path(args.vector_file)
    if not vec_path.exists():
        _error(f"Vector file not found: {vec_path}")

    try:
        query_vector = json.loads(vec_path.read_text(encoding="utf-8"))
        if not isinstance(query_vector, list):
            _error("Vector file must contain a JSON array of floats.")
    except json.JSONDecodeError as exc:
        _error(f"Invalid JSON in vector file: {exc}")

    kwargs: dict[str, Any] = {}
    if args.top_k is not None:
        kwargs["top_k"] = args.top_k

    async with _get_client() as client:
        result = await client.retrievals.execute(
            query_vector=query_vector,
            principal_id=args.principal_id,
            connector_id=args.connector_id,
            **kwargs,
        )
    _output(result)


# -- connectors subcommands ------------------------------------------------


async def _cmd_connectors_list(args: argparse.Namespace) -> None:
    """List connectors."""
    async with _get_client() as client:
        page = await client.connectors.list()
    _output({"items": [c.model_dump(mode="json") for c in page.items], "total": page.total})


async def _cmd_connectors_test(args: argparse.Namespace) -> None:
    """Test a connector."""
    async with _get_client() as client:
        result = await client.connectors.test(args.connector_id)
    _output(result)


async def _cmd_connectors_create(args: argparse.Namespace) -> None:
    """Create a connector."""
    config = None
    if args.config:
        try:
            config = json.loads(args.config)
        except json.JSONDecodeError as exc:
            _error(f"Invalid JSON for --config: {exc}")

    async with _get_client() as client:
        result = await client.connectors.create(
            name=args.name,
            type=args.type,
            config=config,
        )
    _output(result)


# -- policies subcommands --------------------------------------------------


async def _cmd_policies_list(args: argparse.Namespace) -> None:
    """List policies."""
    from gateco_sdk.resources.policies import PoliciesResource

    async with _get_client() as client:
        resource = PoliciesResource(client)
        page = await resource.list()
    _output({"items": [p.model_dump(mode="json") for p in page.items], "total": page.total})


async def _cmd_policies_create(args: argparse.Namespace) -> None:
    """Create a policy from a JSON file."""
    from gateco_sdk.resources.policies import PoliciesResource

    file_path = Path(args.from_file)
    if not file_path.exists():
        _error(f"Policy file not found: {file_path}")

    try:
        policy_def = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _error(f"Invalid JSON in policy file: {exc}")

    if not isinstance(policy_def, dict):
        _error("Policy file must contain a JSON object.")

    # Extract required fields
    name = policy_def.get("name")
    type_ = policy_def.get("type")
    effect = policy_def.get("effect")
    if not all([name, type_, effect]):
        _error("Policy file must include 'name', 'type', and 'effect' fields.")

    kwargs: dict[str, Any] = {}
    if "description" in policy_def:
        kwargs["description"] = policy_def["description"]
    if "resource_selectors" in policy_def:
        kwargs["resource_selectors"] = policy_def["resource_selectors"]
    if "rules" in policy_def:
        kwargs["rules"] = policy_def["rules"]

    async with _get_client() as client:
        resource = PoliciesResource(client)
        result = await resource.create(
            name=name,
            type=type_,
            effect=effect,
            **kwargs,
        )
    _output(result)


# -- suggest-classifications -----------------------------------------------


async def _cmd_suggest_classifications(args: argparse.Namespace) -> None:
    """Generate classification suggestions for a connector's vectors."""
    kwargs: dict[str, Any] = {}
    if args.scan_limit is not None:
        kwargs["scan_limit"] = args.scan_limit
    if args.grouping_strategy:
        kwargs["grouping_strategy"] = args.grouping_strategy

    async with _get_client() as client:
        result = await client.connectors.suggest_classifications(
            args.connector_id,
            **kwargs,
        )
    _output(result)


# -- retroactive-register --------------------------------------------------


async def _cmd_retroactive_register(args: argparse.Namespace) -> None:
    """Scan and register unmanaged vectors."""
    from gateco_sdk.resources.retroactive import RetroactiveResource

    kwargs: dict[str, Any] = {}
    if args.scan_limit is not None:
        kwargs["scan_limit"] = args.scan_limit
    if args.dry_run:
        kwargs["dry_run"] = True

    async with _get_client() as client:
        resource = RetroactiveResource(client)
        result = await resource.register(
            connector_id=args.connector_id,
            **kwargs,
        )
    _output(result)


# -- audit ------------------------------------------------------------------


async def _cmd_audit_list(args: argparse.Namespace) -> None:
    """List audit events."""
    from gateco_sdk.resources.audit import AuditResource

    page_num = args.page if args.page else 1
    per_page = args.per_page if args.per_page else 20

    async with _get_client() as client:
        resource = AuditResource(client)
        page = await resource.list(page=page_num, per_page=per_page)
    _output({"items": [e.model_dump(mode="json") for e in page.items], "total": page.total})


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="gateco",
        description="Gateco CLI — permission-aware retrieval for AI systems",
    )
    subparsers = parser.add_subparsers(dest="command")

    # -- login --------------------------------------------------------------
    login_parser = subparsers.add_parser("login", help="Authenticate and store credentials")
    login_parser.add_argument("--email", required=True, help="Account email")
    login_parser.add_argument("--password", required=True, help="Account password")
    login_parser.add_argument(
        "--base-url",
        default=_DEFAULT_BASE_URL,
        help=f"API base URL (default: {_DEFAULT_BASE_URL})",
    )

    # -- ingest -------------------------------------------------------------
    ingest_parser = subparsers.add_parser("ingest", help="Ingest a single text file")
    ingest_parser.add_argument("file", help="Path to file (.txt or .md)")
    ingest_parser.add_argument("--connector-id", required=True, help="Target connector ID")
    ingest_parser.add_argument("--classification", default=None, help="Classification label")
    ingest_parser.add_argument("--sensitivity", default=None, help="Sensitivity level")
    ingest_parser.add_argument("--domain", default=None, help="Domain tag")

    # -- ingest-batch -------------------------------------------------------
    batch_parser = subparsers.add_parser("ingest-batch", help="Ingest files from a directory")
    batch_parser.add_argument("directory", help="Directory containing files")
    batch_parser.add_argument("--connector-id", required=True, help="Target connector ID")
    batch_parser.add_argument(
        "--glob", default="*.txt", help="Glob pattern for matching files (default: *.txt)"
    )

    # -- retrieve -----------------------------------------------------------
    retrieve_parser = subparsers.add_parser("retrieve", help="Execute a permission-gated retrieval")
    retrieve_parser.add_argument(
        "--vector-file", required=True, help="JSON file containing query vector"
    )
    retrieve_parser.add_argument("--principal-id", required=True, help="Requesting principal ID")
    retrieve_parser.add_argument("--connector-id", required=True, help="Connector ID to query")
    retrieve_parser.add_argument("--top-k", type=int, default=None, help="Max results (default: 10)")

    # -- connectors ---------------------------------------------------------
    conn_parser = subparsers.add_parser("connectors", help="Connector management")
    conn_sub = conn_parser.add_subparsers(dest="subcommand")

    conn_sub.add_parser("list", help="List all connectors")

    conn_test = conn_sub.add_parser("test", help="Test connector connectivity")
    conn_test.add_argument("connector_id", help="Connector ID to test")

    conn_create = conn_sub.add_parser("create", help="Create a new connector")
    conn_create.add_argument("--name", required=True, help="Connector name")
    conn_create.add_argument("--type", required=True, help="Connector type (e.g. pgvector)")
    conn_create.add_argument("--config", default=None, help="JSON config string")

    # -- policies -----------------------------------------------------------
    pol_parser = subparsers.add_parser("policies", help="Policy management")
    pol_sub = pol_parser.add_subparsers(dest="subcommand")

    pol_sub.add_parser("list", help="List all policies")

    pol_create = pol_sub.add_parser("create", help="Create a policy from a JSON file")
    pol_create.add_argument("--from-file", required=True, help="Path to policy JSON file")

    # -- suggest-classifications --------------------------------------------
    suggest_parser = subparsers.add_parser(
        "suggest-classifications", help="Suggest classifications for connector vectors"
    )
    suggest_parser.add_argument("--connector-id", required=True, help="Connector to analyze")
    suggest_parser.add_argument("--scan-limit", type=int, default=1000, help="Max vectors to scan")
    suggest_parser.add_argument(
        "--grouping-strategy", default="individual",
        help="Grouping strategy (individual, regex, prefix)",
    )

    # -- retroactive-register -----------------------------------------------
    retro_parser = subparsers.add_parser(
        "retroactive-register", help="Scan and register unmanaged vectors"
    )
    retro_parser.add_argument("--connector-id", required=True, help="Connector to scan")
    retro_parser.add_argument("--scan-limit", type=int, default=5000, help="Max vectors to scan")
    retro_parser.add_argument(
        "--dry-run", action="store_true", help="Simulate without creating resources"
    )

    # -- audit --------------------------------------------------------------
    audit_parser = subparsers.add_parser("audit", help="Audit log operations")
    audit_sub = audit_parser.add_subparsers(dest="subcommand")

    audit_list = audit_sub.add_parser("list", help="List audit events")
    audit_list.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    audit_list.add_argument("--per-page", type=int, default=20, help="Items per page (default: 20)")

    return parser


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_DISPATCH: dict[str, Any] = {
    "login": _cmd_login,
    "ingest": _cmd_ingest,
    "ingest-batch": _cmd_ingest_batch,
    "retrieve": _cmd_retrieve,
}

_SUB_DISPATCH: dict[str, dict[str, Any]] = {
    "connectors": {
        "list": _cmd_connectors_list,
        "test": _cmd_connectors_test,
        "create": _cmd_connectors_create,
    },
    "policies": {
        "list": _cmd_policies_list,
        "create": _cmd_policies_create,
    },
    "audit": {
        "list": _cmd_audit_list,
    },
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point (registered as ``gateco`` console script)."""
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Commands with subcommands
    if args.command in _SUB_DISPATCH:
        sub = getattr(args, "subcommand", None)
        if not sub:
            # Print help for the subcommand group
            parser.parse_args([args.command, "--help"])
            sys.exit(1)
        handler = _SUB_DISPATCH[args.command].get(sub)
        if not handler:
            _error(f"Unknown subcommand: {args.command} {sub}")
    elif args.command == "suggest-classifications":
        handler = _cmd_suggest_classifications
    elif args.command == "retroactive-register":
        handler = _cmd_retroactive_register
    else:
        handler = _DISPATCH.get(args.command)
        if not handler:
            _error(f"Unknown command: {args.command}")

    try:
        _run(handler(args))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        _error(str(exc))


if __name__ == "__main__":
    main()

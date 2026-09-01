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

_DEFAULT_BASE_URL = os.environ.get("GATECO_BASE_URL", "https://api.gateco.ai")  # 1.9.0: production, not localhost


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
        os.close(fd) if not os.get_inheritable(fd) else None
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
    raw_base = raw_base.removesuffix("/api")

    # If we have JWT tokens, inject them into the token manager and persist
    # whatever the SDK's auto-refresh replaces them with. Before this the CLI
    # refreshed in memory only, so every invocation re-used the refresh token
    # until it expired at seven days and then failed with a bare JSON error.
    access = creds.get("access_token")
    if access and not api_key:
        client = _persisting_client_class()(raw_base, base_url_for_file=str(base_url))
        client._token_manager.set_tokens(access, creds.get("refresh_token"))
        return client

    return AsyncGatecoClient(raw_base, api_key=api_key)


def _persisting_client_class() -> type:
    """Build (once) an AsyncGatecoClient subclass that writes refreshed tokens back to disk."""
    from gateco_sdk.client import AsyncGatecoClient

    class _PersistingClient(AsyncGatecoClient):
        def __init__(self, base_url: str, *, base_url_for_file: str, **kwargs: Any) -> None:
            super().__init__(base_url, **kwargs)
            self._base_url_for_file = base_url_for_file
            self._loaded_tokens: tuple[str | None, str | None] | None = None

        async def __aenter__(self):  # type: ignore[override]
            self._loaded_tokens = (
                self._token_manager.access_token, self._token_manager.refresh_token
            )
            return await super().__aenter__()

        async def __aexit__(self, *exc_info: object) -> None:  # type: ignore[override]
            try:
                await super().__aexit__(*exc_info)
            finally:
                current = (self._token_manager.access_token, self._token_manager.refresh_token)
                if current[0] and current != self._loaded_tokens:
                    _save_credentials(current[0], current[1], self._base_url_for_file)

    return _PersistingClient


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
    if os.environ.get("GATECO_API_KEY"):
        print(
            "warning: GATECO_API_KEY is set and takes precedence over a stored session. "
            "Unset it if you want this login to be used.",
            file=sys.stderr,
        )
    from gateco_sdk.client import AsyncGatecoClient

    base_url = args.base_url
    raw_base = base_url
    raw_base = raw_base.removesuffix("/api")

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
    search_mode = getattr(args, "search_mode", "vector") or "vector"

    kwargs: dict[str, Any] = {"search_mode": search_mode}
    if args.top_k is not None:
        kwargs["top_k"] = args.top_k

    # Vector file is required only for vector mode (and optional for hybrid)
    if search_mode == "vector" and not args.query:
        vec_path = Path(args.vector_file) if args.vector_file else None
        if not vec_path or not vec_path.exists():
            _error("--vector-file is required for vector search mode (or use --query)")

        try:
            query_vector = json.loads(vec_path.read_text(encoding="utf-8"))
            if not isinstance(query_vector, list):
                _error("Vector file must contain a JSON array of floats.")
        except json.JSONDecodeError as exc:
            _error(f"Invalid JSON in vector file: {exc}")
        kwargs["query_vector"] = query_vector
    elif args.vector_file:
        vec_path = Path(args.vector_file)
        if vec_path.exists():
            try:
                query_vector = json.loads(vec_path.read_text(encoding="utf-8"))
                if isinstance(query_vector, list):
                    kwargs["query_vector"] = query_vector
            except json.JSONDecodeError:
                pass

    if args.query:
        kwargs["query"] = args.query

    if search_mode == "hybrid" and getattr(args, "alpha", None) is not None:
        kwargs["alpha"] = args.alpha

    if search_mode == "grep":
        if getattr(args, "pattern_type", None):
            kwargs["pattern_type"] = args.pattern_type
        if getattr(args, "case_sensitive", False):
            kwargs["case_sensitive"] = True

    async with _get_client() as client:
        result = await client.retrievals.execute(
            principal_id=args.principal_id,
            connector_id=args.connector_id,
            **kwargs,
        )
    _output(result)


# -- principals subcommands ------------------------------------------------


async def _cmd_whoami(args: argparse.Namespace) -> None:
    """Show how the CLI is authenticating: URL, session or key, and the key's scopes."""
    creds = _load_credentials()
    source = "GATECO_API_KEY" if os.environ.get("GATECO_API_KEY") else (
        "~/.gateco/credentials.json (gateco login)" if creds.get("access_token") else "none"
    )
    async with _get_client() as client:
        me = await client.users.get_me()
    auth = getattr(me, "auth", None) or (me.get("auth") if isinstance(me, dict) else None) or {}
    _output({
        "base_url": str(creds.get("base_url", _DEFAULT_BASE_URL)),
        "credential_source": source,
        "auth": auth if isinstance(auth, dict) else getattr(auth, "model_dump", lambda: auth)(),
        "email": getattr(me, "email", None) or (me.get("email") if isinstance(me, dict) else None),
    })


async def _cmd_principals_list(args: argparse.Namespace) -> None:
    """List principals."""
    page_num = args.page if args.page else 1
    per_page = args.per_page if args.per_page else 20
    async with _get_client() as client:
        page = await client.principals.list(page=page_num, per_page=per_page)
    _output({"items": [p.model_dump(mode="json") for p in page.items], "total": page.total})


async def _cmd_principals_resolve(args: argparse.Namespace) -> None:
    """Resolve a principal by email or provider subject ID."""
    email: str | None = args.email
    provider_subject: str | None = args.provider_subject
    identity_provider_id: str | None = args.identity_provider_id

    if not email and not provider_subject:
        _error("At least one of --email or --provider-subject must be provided.")

    async with _get_client() as client:
        principal = await client.principals.resolve(
            email=email,
            provider_subject=provider_subject,
            identity_provider_id=identity_provider_id,
        )
    _output(principal)


async def _cmd_principals_create(args: argparse.Namespace) -> None:
    """Create a principal in the org's local directory (no identity provider needed)."""
    attributes: dict[str, str] = {}
    for item in args.attr or []:
        if "=" not in item:
            _error(f"--attr expects key=value, got {item!r}")
        k, v = item.split("=", 1)
        attributes[k.strip()] = v.strip()
    async with _get_client() as client:
        principal = await client.principals.create(
            args.email,
            display_name=args.name,
            groups=args.group or None,
            roles=args.role or None,
            attributes=attributes or None,
        )
    _output(principal)


async def _cmd_principals_deactivate(args: argparse.Namespace) -> None:
    """Deactivate a local principal (status -> inactive; never a hard delete)."""
    async with _get_client() as client:
        await client.principals.delete(args.principal_id)
    _output({"id": args.principal_id, "status": "inactive"})


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


# -- ask (grounded answer) --------------------------------------------------


async def _cmd_ask(args: argparse.Namespace) -> None:
    """Execute a grounded answer synthesis."""
    kwargs: dict[str, Any] = {}
    if args.top_k is not None:
        kwargs["top_k"] = args.top_k

    async with _get_client() as client:
        result = await client.answers.execute(
            query=args.query,
            principal_id=args.principal_id,
            connector_id=args.connector_id,
            **kwargs,
        )
    _output(result)


# -- filter (policy filter) -------------------------------------------------


async def _cmd_filter(args: argparse.Namespace) -> None:
    """Apply policy filtering to external retrieval candidates."""
    if args.candidates_file:
        file_path = Path(args.candidates_file)
        if not file_path.exists():
            _error(f"Candidates file not found: {file_path}")
        try:
            candidates = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            _error(f"Invalid JSON in candidates file: {exc}")
    elif args.candidates:
        try:
            candidates = json.loads(args.candidates)
        except json.JSONDecodeError as exc:
            _error(f"Invalid JSON for --candidates: {exc}")
    else:
        _error("Either --candidates or --candidates-file is required")

    if not isinstance(candidates, list):
        _error("Candidates must be a JSON array")

    async with _get_client() as client:
        result = await client.retrievals.filter(
            principal_id=args.principal_id,
            connector_id=args.connector_id,
            candidates=candidates,
            include_trace=args.include_trace,
        )
    _output(result)


# -- query (interactive REPL) -----------------------------------------------


async def _cmd_query(args: argparse.Namespace) -> None:
    """Launch the interactive query REPL."""
    from gateco_sdk.query_repl import GatecoQueryREPL

    creds = _load_credentials()
    base_url = args.base_url or creds.get("base_url", _DEFAULT_BASE_URL)

    repl = GatecoQueryREPL(
        base_url=base_url,
        email=args.email,
        password=args.password,
        connector_id=args.connector_id,
        principal_id=args.principal_id,
        debug=args.debug,
        json_mode=args.json,
        top_k=args.top_k,
    )
    await repl.run()


# -- mcp serve --------------------------------------------------------------


async def _cmd_mcp_serve(args: argparse.Namespace) -> None:
    """Start the MCP server on stdio transport."""
    try:
        from gateco_sdk.mcp import run_stdio
    except ImportError:
        _error("MCP extras not installed. Run: pip install gateco[mcp]")
    run_stdio()


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
        "--vector-file", default=None, help="JSON file containing query vector (required for vector mode)"
    )
    retrieve_parser.add_argument("--principal-id", required=True, help="Requesting principal ID")
    retrieve_parser.add_argument("--connector-id", required=True, help="Connector ID to query")
    retrieve_parser.add_argument(
        "--top-k", type=int, default=None, help="Max results (default: 10)",
    )
    retrieve_parser.add_argument(
        "--query", default=None, help="Text query (used for keyword/hybrid/grep or server-side embedding)",
    )
    retrieve_parser.add_argument(
        "--search-mode", default="vector",
        choices=["vector", "keyword", "hybrid", "grep"],
        help="Search mode (default: vector)",
    )
    retrieve_parser.add_argument(
        "--alpha", type=float, default=None,
        help="Hybrid weight: 1.0=all-vector, 0.0=all-keyword (default: 0.5)",
    )
    retrieve_parser.add_argument(
        "--pattern-type", default=None, choices=["substring", "regex"],
        help="Grep pattern type (default: substring)",
    )
    retrieve_parser.add_argument(
        "--case-sensitive", action="store_true",
        help="Case-sensitive grep matching",
    )

    # -- filter -------------------------------------------------------------
    filter_parser = subparsers.add_parser(
        "filter", help="Apply policy filtering to external retrieval candidates"
    )
    filter_parser.add_argument("--connector-id", required=True, help="Connector ID")
    filter_parser.add_argument("--principal-id", required=True, help="Requesting principal ID")
    filter_parser.add_argument(
        "--candidates", default=None,
        help="Inline JSON array of candidate objects",
    )
    filter_parser.add_argument(
        "--candidates-file", default=None,
        help="Path to JSON file with candidate array",
    )
    filter_parser.add_argument(
        "--include-trace", action="store_true",
        help="Include full policy trace in response",
    )

    # -- ask ----------------------------------------------------------------
    ask_parser = subparsers.add_parser("ask", help="Get a grounded answer from allowed chunks")
    ask_parser.add_argument("query", help="Natural language question")
    ask_parser.add_argument("--connector-id", required=True, help="Connector ID to query")
    ask_parser.add_argument("--principal-id", required=True, help="Requesting principal ID")
    ask_parser.add_argument(
        "--top-k", type=int, default=None,
        help="Max context chunks (default: 5)",
    )

    # -- principals ---------------------------------------------------------
    subparsers.add_parser("whoami", help="Show base URL, credential source, and key scopes")

    prin_parser = subparsers.add_parser("principals", help="Principal management")
    prin_sub = prin_parser.add_subparsers(dest="subcommand")

    prin_list = prin_sub.add_parser("list", help="List all principals")
    prin_list.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    prin_list.add_argument("--per-page", type=int, default=20, help="Items per page (default: 20)")

    prin_create = prin_sub.add_parser(
        "create", help="Create a principal in the local directory (no identity provider needed)"
    )
    prin_create.add_argument("--email", required=True, help="Email address (unique per directory)")
    prin_create.add_argument("--name", default=None, help="Display name")
    prin_create.add_argument("--group", action="append", help="Group name (repeatable)")
    prin_create.add_argument("--role", action="append", help="Role name (repeatable)")
    prin_create.add_argument("--attr", action="append", help="Attribute as key=value (repeatable)")

    prin_deactivate = prin_sub.add_parser(
        "deactivate", help="Deactivate a local principal (status -> inactive)"
    )
    prin_deactivate.add_argument("principal_id", help="Principal UUID")

    prin_resolve = prin_sub.add_parser(
        "resolve", help="Resolve a principal by email or provider subject ID"
    )
    prin_resolve.add_argument("--email", default=None, help="Email address of the principal")
    prin_resolve.add_argument(
        "--provider-subject", default=None,
        help="Provider-native subject identifier (e.g. Okta user ID, Google sub claim)",
    )
    prin_resolve.add_argument(
        "--identity-provider-id", default=None,
        help="UUID of the identity provider to scope the lookup to",
    )

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

    # -- mcp ----------------------------------------------------------------
    mcp_parser = subparsers.add_parser("mcp", help="MCP server operations")
    mcp_sub = mcp_parser.add_subparsers(dest="subcommand")
    mcp_sub.add_parser("serve", help="Start the MCP server on stdio transport")

    # -- query (interactive REPL) -------------------------------------------
    query_parser = subparsers.add_parser(
        "query", help="Interactive REPL for testing retrieval queries"
    )
    query_parser.add_argument("--email", default=None, help="Account email (or use stored creds)")
    query_parser.add_argument("--password", default=None, help="Account password")
    query_parser.add_argument(
        "--base-url", default=None,
        help=f"API base URL (default: {_DEFAULT_BASE_URL})",
    )
    query_parser.add_argument("--connector-id", default=None, help="Pre-select connector ID")
    query_parser.add_argument("--principal-id", default=None, help="Pre-select principal ID")
    query_parser.add_argument("--debug", action="store_true", help="Show request/response details")
    query_parser.add_argument("--json", action="store_true", help="Show raw JSON responses")
    query_parser.add_argument("--top-k", type=int, default=20, help="Max results (default: 20)")

    return parser


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_DISPATCH: dict[str, Any] = {
    "login": _cmd_login,
    "whoami": _cmd_whoami,
    "ingest": _cmd_ingest,
    "ingest-batch": _cmd_ingest_batch,
    "retrieve": _cmd_retrieve,
    "filter": _cmd_filter,
    "ask": _cmd_ask,
    "query": _cmd_query,
}

_SUB_DISPATCH: dict[str, dict[str, Any]] = {
    "principals": {
        "list": _cmd_principals_list,
        "resolve": _cmd_principals_resolve,
        "create": _cmd_principals_create,
        "deactivate": _cmd_principals_deactivate,
    },
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
    "mcp": {
        "serve": _cmd_mcp_serve,
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
        from gateco_sdk.errors import AuthenticationError

        if isinstance(exc, AuthenticationError):
            _error(
                f"{exc}. Your session is missing, expired or revoked: run `gateco login` "
                "again, or set GATECO_API_KEY to a key with the scopes this command needs."
            )
        _error(str(exc))


if __name__ == "__main__":
    main()

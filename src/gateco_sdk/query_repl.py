"""Interactive query REPL for testing Gateco retrievals.

Provides a terminal-based REPL for executing natural language queries against
Gateco connectors with different principals, displaying policy decisions with
colored output.

Query text is sent to the Gateco backend which handles embedding server-side.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

from gateco_sdk.client import AsyncGatecoClient
from gateco_sdk.types.principals import Principal
from gateco_sdk.types.retrievals import SecuredRetrieval


# ---------------------------------------------------------------------------
# ANSI color helpers
# ---------------------------------------------------------------------------

_COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}


def _c(text: str, *styles: str) -> str:
    """Wrap *text* in ANSI escape codes."""
    if not sys.stdout.isatty():
        return text
    prefix = "".join(_COLORS.get(s, "") for s in styles)
    return f"{prefix}{text}{_COLORS['reset']}"


def _format_snippet(text: str, limit: int = 200) -> str:
    """Normalize whitespace and truncate for terminal display."""
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "\u2026"


# ---------------------------------------------------------------------------
# REPL class
# ---------------------------------------------------------------------------


class GatecoQueryREPL:
    """Interactive REPL for permission-gated retrieval queries.

    Args:
        base_url: Gateco API base URL.
        email: Login email.
        password: Login password.
        connector_id: Optional pre-selected connector ID.
        principal_id: Optional pre-selected principal ID.
        debug: Show request/response details.
        json_mode: Show raw JSON responses.
        top_k: Max retrieval results.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        email: str | None = None,
        password: str | None = None,
        connector_id: str | None = None,
        principal_id: str | None = None,
        debug: bool = False,
        json_mode: bool = False,
        top_k: int = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        if self.base_url.endswith("/api"):
            self.base_url = self.base_url[: -len("/api")]

        self.email = email
        self.password = password
        self.debug = debug
        self.json_mode = json_mode
        self.top_k = top_k

        self._client: AsyncGatecoClient | None = None
        self._connector_id = connector_id
        self._principal_id = principal_id

        # Cached context
        self._connectors: list[dict[str, Any]] = []
        self._principals: list[Principal] = []
        self._policies: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Authenticate and load context (connectors, principals, policies)."""
        client = AsyncGatecoClient(self.base_url)
        try:
            if self.email and self.password:
                await client.login(self.email, self.password)
                print(_c(f"Logged in as {self.email}", "green"))
            else:
                # Try stored credentials
                from gateco_sdk.cli import _load_credentials

                creds = _load_credentials()
                access = creds.get("access_token")
                if not access:
                    print(_c(
                        "No credentials. Use --email/--password "
                        "or `gateco login` first.", "red",
                    ))
                    await client.close()
                    return False
                client._token_manager.set_tokens(access, creds.get("refresh_token"))
                print(_c("Using stored credentials.", "green"))
        except Exception as exc:
            print(_c(f"Login failed: {exc}", "red"))
            await client.close()
            return False

        self._client = client

        # Load connectors
        try:
            page = await client.connectors.list()
            self._connectors = [c.model_dump(mode="json") for c in page.items]
        except Exception as exc:
            if self.debug:
                print(_c(f"Failed to load connectors: {exc}", "yellow"))

        # Load principals
        try:
            page = await client.principals.list(per_page=100)
            self._principals = list(page.items)
        except Exception as exc:
            if self.debug:
                print(_c(f"Failed to load principals: {exc}", "yellow"))

        # Load policies
        try:
            from gateco_sdk.resources.policies import PoliciesResource

            pol_resource = PoliciesResource(client)
            page = await pol_resource.list(per_page=100)
            self._policies = [p.model_dump(mode="json") for p in page.items]
        except Exception as exc:
            if self.debug:
                print(_c(f"Failed to load policies: {exc}", "yellow"))

        # Auto-select connector if only one or if specified
        if self._connector_id:
            print(_c(f"Connector: {self._connector_id}", "cyan"))
        elif len(self._connectors) == 1:
            self._connector_id = self._connectors[0]["id"]
            cname = self._connectors[0].get('name', self._connector_id)
            print(_c(f"Auto-selected connector: {cname}", "cyan"))
        elif self._connectors:
            print(_c(
                f"  {len(self._connectors)} connectors available. "
                "Use `connectors` to list, `connector <name>` to select.",
                "cyan",
            ))

        # Auto-select principal if specified
        if self._principal_id:
            match = self._find_principal(self._principal_id)
            if match:
                self._principal_id = match.id
                print(_c(f"Principal: {match.display_name or match.email or match.id}", "cyan"))
            else:
                print(_c(f"Principal: {self._principal_id} (not found in list)", "yellow"))
        elif self._principals:
            print(_c(
                f"  {len(self._principals)} principals available. "
                "Use `principals` to list, `switch <name>` to select.",
                "cyan",
            ))

        active_policies = [p for p in self._policies if p.get("status") == "active"]
        print(_c(f"  {len(active_policies)} active policies.", "cyan"))
        print()
        return True

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def cmd_query(self, text: str) -> None:
        """Send a query to the backend for server-side embedding and retrieval."""
        if not self._client:
            print(_c("Not connected.", "red"))
            return
        if not self._connector_id:
            print(_c("No connector selected. Use `connector <name>` first.", "yellow"))
            return
        if not self._principal_id:
            print(_c("No principal selected. Use `switch <name>` first.", "yellow"))
            return

        try:
            t0 = time.monotonic()
            result = await self._client.retrievals.execute(
                query=text,
                principal_id=self._principal_id,
                connector_id=self._connector_id,
                top_k=self.top_k,
            )
            round_trip_ms = (time.monotonic() - t0) * 1000

            if self.json_mode:
                self._display_json(result)
            else:
                self._display_retrieval(result, round_trip_ms)

        except Exception as exc:
            print(_c(f"Query failed: {exc}", "red"))
            if self.debug:
                import traceback

                traceback.print_exc()

    def cmd_principals(self) -> None:
        """List available principals."""
        if not self._principals:
            print(_c("No principals loaded.", "yellow"))
            return

        print(_c("Principals:", "bold"))
        for p in self._principals:
            marker = " *" if p.id == self._principal_id else ""
            name = p.display_name or p.email or p.external_id or p.id
            groups = ", ".join(p.groups) if p.groups else "none"
            dept = (p.attributes or {}).get("department", "")
            dept_str = f" dept={dept}" if dept else ""
            print(
                f"  {_c(name, 'cyan')}{_c(marker, 'green')}"
                f"  groups=[{groups}]{dept_str}  id={p.id[:8]}..."
            )

    def cmd_connectors(self) -> None:
        """List available connectors."""
        if not self._connectors:
            print(_c("No connectors loaded.", "yellow"))
            return

        print(_c("Connectors:", "bold"))
        for c in self._connectors:
            marker = " *" if c["id"] == self._connector_id else ""
            name = c.get("name", c["id"])
            ctype = c.get("type", "unknown")
            status = c.get("status", "unknown")
            readiness = c.get("policy_readiness_level", "?")
            color = "green" if status == "active" else "yellow"
            print(
                f"  {_c(name, 'cyan')}{_c(marker, 'green')}"
                f"  type={ctype}  status={_c(status, color)}"
                f"  L{readiness}  id={c['id'][:8]}..."
            )

    def cmd_policies(self) -> None:
        """List active policies."""
        active = [p for p in self._policies if p.get("status") == "active"]
        if not active:
            print(_c("No active policies.", "yellow"))
            return

        print(_c(f"Active Policies ({len(active)}):", "bold"))
        for p in active:
            name = p.get("name", "unnamed")
            effect = p.get("effect", "?")
            ptype = p.get("type", "?")
            color = "green" if effect == "allow" else "red"
            selectors = p.get("resource_selectors", {})
            sel_str = ""
            if selectors:
                parts = []
                for k, v in selectors.items():
                    if isinstance(v, list):
                        parts.append(f"{k}={','.join(str(x) for x in v)}")
                    else:
                        parts.append(f"{k}={v}")
                sel_str = f"  selectors=[{'; '.join(parts)}]"
            rules_count = len(p.get("rules", []))
            print(
                f"  {_c(name, 'cyan')}  {_c(effect, color)}"
                f"  type={ptype}  rules={rules_count}{sel_str}"
            )

    def cmd_switch(self, identifier: str) -> None:
        """Switch the active principal by name, email, or partial ID."""
        match = self._find_principal(identifier)
        if match:
            self._principal_id = match.id
            name = match.display_name or match.email or match.id
            print(_c(f"Switched to: {name} ({match.id[:8]}...)", "green"))
        else:
            print(_c(f"No principal matching '{identifier}'.", "yellow"))

    def cmd_connector(self, identifier: str) -> None:
        """Switch the active connector by name or partial ID."""
        match = self._find_connector(identifier)
        if match:
            self._connector_id = match["id"]
            name = match.get("name", match["id"])
            print(_c(f"Switched to connector: {name} ({match['id'][:8]}...)", "green"))
        else:
            print(_c(f"No connector matching '{identifier}'.", "yellow"))

    def cmd_session(self) -> None:
        """Show current session state."""
        print(_c("Session:", "bold"))
        # Principal
        if self._principal_id:
            match = self._find_principal(self._principal_id)
            name = (match.display_name or match.email or match.id) if match else self._principal_id
            print(f"  Principal: {_c(name, 'cyan')} ({self._principal_id[:8]}...)")
        else:
            print(f"  Principal: {_c('none', 'yellow')}")
        # Connector
        if self._connector_id:
            match = self._find_connector(self._connector_id)
            name = match.get("name", self._connector_id) if match else self._connector_id
            print(f"  Connector: {_c(name, 'cyan')} ({self._connector_id[:8]}...)")
        else:
            print(f"  Connector: {_c('none', 'yellow')}")
        # Settings
        print(f"  Top-K: {self.top_k}")
        print("  Embedding: server-side")
        print(f"  JSON mode: {self.json_mode}")
        print(f"  Debug: {self.debug}")

    async def cmd_ask(self, text: str) -> None:
        """Send a question for grounded answer synthesis."""
        if not self._client:
            print(_c("Not connected.", "red"))
            return
        if not self._connector_id:
            print(_c("No connector selected. Use `connector <name>` first.", "yellow"))
            return
        if not self._principal_id:
            print(_c("No principal selected. Use `switch <name>` first.", "yellow"))
            return

        try:
            result = await self._client.answers.execute(
                query=text,
                principal_id=self._principal_id,
                connector_id=self._connector_id,
                top_k=self.top_k if self.top_k <= 20 else 5,
            )

            if self.json_mode:
                data = result.model_dump(mode="json")
                print(json.dumps(data, indent=2, default=str))
                return

            print()
            outcome = (result.outcome or "unknown").upper()
            allowed = result.allowed_chunks or 0
            denied = result.denied_chunks or 0

            if result.answer:
                label = "Partial Answer:" if getattr(result, "is_partial", False) else "Answer:"
                print(f"{_c(label, 'bold')}")
                print(f"  {result.answer}")

                if result.citations:
                    print(f"\n{_c('Sources:', 'bold')}")
                    for cit in result.citations:
                        score_str = f"[{cit.score:.2f}] " if cit.score is not None else ""
                        vid = cit.vector_id or cit.resource_id or "?"
                        excerpt = _format_snippet(cit.text_excerpt, 80) if cit.text_excerpt else ""
                        excerpt_str = f' — "{excerpt}"' if excerpt else ""
                        print(
                            f"  [{cit.index}] {_c(score_str, 'dim')}"
                            f"{vid}{_c(excerpt_str, 'dim')}"
                        )
            else:
                outcome_colors = {"NO_ACCESS": "red", "INSUFFICIENT_CONTEXT": "yellow"}
                color = outcome_colors.get(outcome, "white")
                print(f"{_c('No answer:', 'bold')} {_c(outcome, color)}")
                if outcome == "INSUFFICIENT_CONTEXT":
                    avail = getattr(result, "chunks_available", 0)
                    used = getattr(result, "chunks_used_final", 0)
                    retried = getattr(result, "retry_used", False)
                    if avail <= 3:
                        print(_c(
                            f"  Only {avail} allowed chunk(s) with text were available.",
                            "dim",
                        ))
                    elif retried:
                        print(_c(
                            f"  Used {used} of {avail} allowed chunks; "
                            "retried with expanded context.",
                            "dim",
                        ))
                    else:
                        print(_c(
                            f"  Used {used} of {avail} allowed chunks.",
                            "dim",
                        ))

            print(f"\n{_c('Outcome:', 'dim')} {outcome} ({allowed} allowed, {denied} denied)")

            parts = []
            if result.total_latency_ms is not None:
                parts.append(f"total: {result.total_latency_ms}ms")
            if result.retrieval_latency_ms is not None:
                parts.append(f"retrieval: {result.retrieval_latency_ms}ms")
            if result.synthesis_latency_ms is not None:
                parts.append(f"synthesis: {result.synthesis_latency_ms}ms")
            if parts:
                print(f"{_c('Latency:', 'dim')} {', '.join(parts)}")
            print()

        except Exception as exc:
            print(_c(f"Ask failed: {exc}", "red"))
            if self.debug:
                import traceback

                traceback.print_exc()

    async def cmd_filter(self, text: str) -> None:
        """Apply policy filtering to external candidates (JSON or @file)."""
        if not self._client:
            print(_c("Not connected.", "red"))
            return
        if not self._connector_id:
            print(_c("No connector selected. Use `connector <name>` first.", "yellow"))
            return
        if not self._principal_id:
            print(_c("No principal selected. Use `switch <name>` first.", "yellow"))
            return

        # Parse candidates: @file or inline JSON
        text = text.strip()
        if text.startswith("@"):
            from pathlib import Path

            fpath = Path(text[1:])
            if not fpath.exists():
                print(_c(f"File not found: {fpath}", "red"))
                return
            try:
                candidates = json.loads(fpath.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                print(_c(f"Invalid JSON in file: {exc}", "red"))
                return
        else:
            try:
                candidates = json.loads(text)
            except json.JSONDecodeError as exc:
                print(_c(f"Invalid JSON: {exc}", "red"))
                return

        if not isinstance(candidates, list):
            print(_c("Candidates must be a JSON array.", "yellow"))
            return

        try:
            t0 = time.monotonic()
            result = await self._client.retrievals.filter(
                principal_id=self._principal_id,
                connector_id=self._connector_id,
                candidates=candidates,
                include_trace=self.debug,
            )
            round_trip_ms = (time.monotonic() - t0) * 1000

            if self.json_mode:
                self._display_json(result)
            else:
                self._display_filter(result, round_trip_ms)

        except Exception as exc:
            print(_c(f"Filter failed: {exc}", "red"))
            if self.debug:
                import traceback

                traceback.print_exc()

    def _display_filter(self, result: SecuredRetrieval, round_trip_ms: float = 0) -> None:
        """Display formatted filter results."""
        outcome = (result.outcome or "unknown").upper()
        outcome_colors = {"ALLOWED": "green", "DENIED": "red", "PARTIAL": "yellow"}
        color = outcome_colors.get(outcome, "white")

        allowed = result.allowed_chunks or 0
        denied = result.denied_chunks or 0
        matched = result.matched_chunks or (allowed + denied)

        print()
        print(
            f"{_c('Filter Outcome:', 'bold')} {_c(outcome, color, 'bold')}"
            f" (allowed: {allowed}, denied: {denied}, total: {matched})"
        )

        for item in result.results:
            vid = item.get("vector_id", "?")
            granted = item.get("granted", False)
            mode = item.get("resource_mode", "?")
            score_val = item.get("score")
            score = f"[{score_val}] " if score_val is not None else ""

            if granted:
                status = _c("ALLOWED", "green")
                text = item.get("text")
                snippet = f'  "{_format_snippet(text, 100)}"' if text else ""
            else:
                status = _c("DENIED", "red")
                reason = item.get("denial_reason", "")
                snippet = f"  reason: {reason}" if reason else ""

            print(f"  {_c(score, 'dim')}{vid} {status} ({mode}){_c(snippet, 'dim')}")

        # Latency
        latency = result.latency_ms
        parts = []
        if latency is not None:
            parts.append(f"total: {latency:.0f}ms")
        if round_trip_ms:
            parts.append(f"round-trip: {round_trip_ms:.0f}ms")
        if parts:
            print(f"\n  {_c('Latency:', 'dim')} {', '.join(parts)}")
        print()

    def cmd_help(self) -> None:
        """Show available commands."""
        print(_c("Commands:", "bold"))
        print("  <text>           Execute a retrieval query (search)")
        print("  search <text>    Execute a retrieval query (explicit)")
        print("  ask <text>       Get a grounded answer from allowed chunks")
        print("  filter <json>    Policy-filter external candidates (JSON or @file)")
        print("  principals       List available principals")
        print("  connectors       List available connectors")
        print("  policies         List active policies")
        print("  switch <name>    Switch active principal (name, email, or partial ID)")
        print("  connector <name> Switch active connector (name or partial ID)")
        print("  session          Show current principal, connector, settings")
        print("  json             Toggle JSON output mode")
        print("  debug            Toggle debug mode")
        print("  top-k <N>        Set max results")
        print("  help             Show this help")
        print("  exit / quit      Exit the REPL")

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def _display_retrieval(self, result: SecuredRetrieval, round_trip_ms: float = 0) -> None:
        """Display formatted retrieval results."""
        outcome = (result.outcome or result.status or "unknown").upper()
        outcome_colors = {
            "ALLOWED": "green",
            "DENIED": "red",
            "PARTIAL": "yellow",
            "FULL_ACCESS": "green",
            "NO_ACCESS": "red",
        }
        color = outcome_colors.get(outcome, "white")

        allowed = result.allowed_chunks or result.granted_count or 0
        denied = result.denied_chunks or result.denied_count or 0
        matched = result.matched_chunks or result.total_results or (allowed + denied)

        print()
        print(
            f"{_c('Outcome:', 'bold')} {_c(outcome, color, 'bold')}"
            f" (allowed: {allowed}, denied: {denied}, matched: {matched})"
        )

        # Allowed results
        allowed_items = [r for r in result.outcomes if r.granted]
        if not allowed_items:
            # Fall back to results list
            allowed_items_raw = [r for r in result.results if r.get("granted")]
        else:
            allowed_items_raw = None

        if allowed_items:
            print(f"\n  {_c(f'ALLOWED ({len(allowed_items)} chunks):', 'green', 'bold')}")
            for item in allowed_items[:10]:
                ext_id = item.external_resource_id or item.resource_id
                score = f"[{item.score:.2f}]" if item.score is not None else ""
                domain = (item.metadata or {}).get("domain", "")
                domain_str = f" — domain: {domain}" if domain else ""
                print(f"    {_c(score, 'dim')} {ext_id}{domain_str}")
                if item.text:
                    print(f"      {_c(_format_snippet(item.text), 'dim')}")
            if len(allowed_items) > 10:
                print(f"    ... and {len(allowed_items) - 10} more")
        elif allowed_items_raw:
            print(f"\n  {_c(f'ALLOWED ({len(allowed_items_raw)} chunks):', 'green', 'bold')}")
            for item in allowed_items_raw[:10]:
                ext_id = item.get("external_resource_id", item.get("resource_id", "?"))
                score_val = item.get("score")
                score = f"[{score_val:.2f}]" if score_val is not None else ""
                domain = (item.get("metadata") or {}).get("domain", "")
                domain_str = f" — domain: {domain}" if domain else ""
                print(f"    {_c(score, 'dim')} {ext_id}{domain_str}")
                text = item.get("text")
                if text:
                    print(f"      {_c(_format_snippet(text), 'dim')}")

        # Denied results
        denied_items = [r for r in result.outcomes if not r.granted]
        if not denied_items:
            denied_items_raw = [r for r in result.results if not r.get("granted")]
        else:
            denied_items_raw = None

        if denied_items:
            print(f"\n  {_c(f'DENIED ({len(denied_items)} chunks):', 'red', 'bold')}")
            for item in denied_items[:10]:
                ext_id = item.external_resource_id or item.resource_id
                score = f"[{item.score:.2f}]" if item.score is not None else ""
                domain = (item.metadata or {}).get("domain", "")
                domain_str = f" — domain: {domain}" if domain else ""
                reason = ""
                if item.denial_reason:
                    reason = f" — \"{item.denial_reason.message or item.denial_reason.code}\""
                print(f"    {_c(score, 'dim')} {ext_id}{domain_str}{_c(reason, 'red')}")
            if len(denied_items) > 10:
                print(f"    ... and {len(denied_items) - 10} more")
        elif denied_items_raw:
            print(f"\n  {_c(f'DENIED ({len(denied_items_raw)} chunks):', 'red', 'bold')}")
            for item in denied_items_raw[:10]:
                ext_id = item.get("external_resource_id", item.get("resource_id", "?"))
                score_val = item.get("score")
                score = f"[{score_val:.2f}]" if score_val is not None else ""
                domain = (item.get("metadata") or {}).get("domain", "")
                domain_str = f" — domain: {domain}" if domain else ""
                reason_data = item.get("denial_reason") or {}
                if reason_data:
                    msg = reason_data.get('message') or reason_data.get('code', '')
                    reason = f' — "{msg}"'
                else:
                    reason = ""
                print(
                    f"    {_c(score, 'dim')} {ext_id}"
                    f"{domain_str}{_c(reason, 'red')}"
                )

        # Policy trace — deduplicate by (policy_name, effect) for readability
        if result.policy_trace:
            print(f"\n  {_c('Policy Trace:', 'bold')}")
            seen: set[str] = set()
            for trace in result.policy_trace:
                name = trace.get("policy_name", trace.get("policy_id", "unknown"))
                effect = trace.get("effect", trace.get("decision", "?"))
                key = f"{name}:{effect}"
                if key in seen:
                    continue
                seen.add(key)
                color = "green" if effect in ("allow", "allowed") else "red"
                matched = trace.get("rule_matched")
                match_str = "" if matched is None else (
                    " rule-hit" if matched else " default-effect"
                )
                print(f"    {name} ({_c(effect, color)}{match_str})")

        # Latency
        latency = result.latency_ms or result.duration_ms
        conn_latency = result.connector_latency_ms
        parts = []
        if latency is not None:
            parts.append(f"total: {latency:.0f}ms")
        if conn_latency is not None:
            parts.append(f"connector: {conn_latency:.0f}ms")
        if round_trip_ms:
            parts.append(f"round-trip: {round_trip_ms:.0f}ms")
        if parts:
            print(f"\n  {_c('Latency:', 'dim')} {', '.join(parts)}")
        print()

    def _display_json(self, result: SecuredRetrieval) -> None:
        """Display raw JSON response."""
        data = result.model_dump(mode="json")
        print(json.dumps(data, indent=2, default=str))

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def _find_principal(self, identifier: str) -> Principal | None:
        """Find a principal by display_name, email, external_id, or partial ID."""
        identifier_lower = identifier.lower()
        for p in self._principals:
            if p.id == identifier:
                return p
            if p.display_name and p.display_name.lower() == identifier_lower:
                return p
            if p.email and p.email.lower() == identifier_lower:
                return p
            if p.external_id and p.external_id.lower() == identifier_lower:
                return p
        # Partial match
        for p in self._principals:
            if p.id.startswith(identifier):
                return p
            if p.display_name and identifier_lower in p.display_name.lower():
                return p
            if p.email and identifier_lower in p.email.lower():
                return p
            if p.external_id and identifier_lower in p.external_id.lower():
                return p
        return None

    def _find_connector(self, identifier: str) -> dict[str, Any] | None:
        """Find a connector by name or partial ID."""
        identifier_lower = identifier.lower()
        for c in self._connectors:
            if c["id"] == identifier:
                return c
            if c.get("name", "").lower() == identifier_lower:
                return c
        # Partial match
        for c in self._connectors:
            if c["id"].startswith(identifier):
                return c
            if identifier_lower in c.get("name", "").lower():
                return c
        return None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start the interactive REPL."""
        print(_c("Gateco Query REPL", "bold", "cyan"))
        print(_c(
            "Type a query to search, `ask <text>` for answers, "
            "or `help` for commands.", "dim",
        ))
        print()

        if not await self.connect():
            return

        try:
            while True:
                # Build prompt
                parts = []
                if self._principal_id:
                    match = self._find_principal(self._principal_id)
                    name = (match.display_name or match.email or "?") if match else "?"
                    parts.append(name)
                else:
                    parts.append("no-principal")
                if self._connector_id:
                    match = self._find_connector(self._connector_id)
                    name = match.get("name", "?") if match else "?"
                    parts.append(name)
                else:
                    parts.append("no-connector")

                prompt = _c(f"gateco [{'/'.join(parts)}]> ", "bold")

                try:
                    line = input(prompt).strip()
                except EOFError:
                    break

                if not line:
                    continue

                cmd_lower = line.lower()

                if cmd_lower in ("exit", "quit", "q"):
                    break
                elif cmd_lower == "help":
                    self.cmd_help()
                elif cmd_lower == "principals":
                    self.cmd_principals()
                elif cmd_lower == "connectors":
                    self.cmd_connectors()
                elif cmd_lower == "policies":
                    self.cmd_policies()
                elif cmd_lower == "session":
                    self.cmd_session()
                elif cmd_lower == "json":
                    self.json_mode = not self.json_mode
                    print(_c(f"JSON mode: {'on' if self.json_mode else 'off'}", "cyan"))
                elif cmd_lower == "debug":
                    self.debug = not self.debug
                    print(_c(f"Debug mode: {'on' if self.debug else 'off'}", "cyan"))
                elif cmd_lower.startswith("switch "):
                    self.cmd_switch(line[7:].strip())
                elif cmd_lower.startswith("connector "):
                    self.cmd_connector(line[10:].strip())
                elif cmd_lower.startswith("top-k "):
                    try:
                        self.top_k = int(line[6:].strip())
                        print(_c(f"Top-K: {self.top_k}", "cyan"))
                    except ValueError:
                        print(_c("Usage: top-k <number>", "yellow"))
                elif cmd_lower.startswith("ask "):
                    await self.cmd_ask(line[4:].strip())
                elif cmd_lower.startswith("filter "):
                    await self.cmd_filter(line[7:].strip())
                elif cmd_lower.startswith("search "):
                    await self.cmd_query(line[7:].strip())
                else:
                    await self.cmd_query(line)

        except KeyboardInterrupt:
            print()
        finally:
            if self._client:
                await self._client.close()
            print(_c("Goodbye.", "dim"))

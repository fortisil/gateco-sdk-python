"""Response formatters — SDK models to readable markdown strings.

All functions are pure (no I/O, no side effects) and return markdown-formatted
text suitable for MCP tool responses.
"""

from __future__ import annotations

from gateco_sdk._pagination import Page
from gateco_sdk.types.answers import Answer
from gateco_sdk.types.connectors import Connector
from gateco_sdk.types.principals import Principal
from gateco_sdk.types.retrievals import SecuredRetrieval
from gateco_sdk.types.simulator import SimulationResult

_READINESS_LABELS: dict[int, str] = {
    0: "L0 Not Ready",
    1: "L1 Connection Ready",
    2: "L2 Search Ready",
    3: "L3 Resource Policy",
    4: "L4 Chunk Policy",
}

_TEXT_LIMIT = 120


def _truncate(text: str | None, limit: int = _TEXT_LIMIT) -> str:
    """Truncate text to *limit* characters with ellipsis."""
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def format_retrieval(result: SecuredRetrieval) -> str:
    """Format a ``SecuredRetrieval`` as markdown."""
    outcome = result.outcome or result.status or "unknown"
    duration = f"{result.duration_ms:.0f}ms" if result.duration_ms else "n/a"

    lines = [
        "## Retrieval Results",
        "",
        f"**Outcome:** {outcome} | "
        f"**Allowed:** {result.allowed_chunks or result.granted_count} | "
        f"**Denied:** {result.denied_chunks or result.denied_count} | "
        f"**Duration:** {duration}",
    ]

    # Prefer results (FilterResult) over outcomes (RetrievalOutcome)
    allowed_items = []
    denied_count = 0

    if result.results:
        for r in result.results:
            if r.granted:
                allowed_items.append((r.score, r.resource_id or r.vector_id, r.text))
            else:
                denied_count += 1
    elif result.outcomes:
        for o in result.outcomes:
            if o.granted:
                allowed_items.append((o.score, o.resource_id, o.text))
            else:
                denied_count += 1

    if allowed_items:
        lines += [
            "",
            "### Allowed Chunks",
            "",
            "| # | Score | Resource | Text |",
            "|---|-------|----------|------|",
        ]
        for i, (score, resource, text) in enumerate(allowed_items, 1):
            score_str = f"{score:.2f}" if score is not None else "n/a"
            lines.append(
                f"| {i} | {score_str} | {resource or 'n/a'} | {_truncate(text)} |"
            )
    else:
        lines += ["", "No allowed chunks."]

    # Denial summary
    denial_reasons = result.denial_reasons
    if denied_count > 0 or denial_reasons:
        lines += ["", "### Denial Summary"]
        if denial_reasons:
            for reason in denial_reasons:
                lines.append(f"- {reason}")
        elif denied_count > 0:
            lines.append(f"- {denied_count} chunk(s) denied by policy")

    if result.warnings:
        lines += ["", "### Warnings"]
        for w in result.warnings:
            lines.append(f"- {w}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Answer
# ---------------------------------------------------------------------------


def format_answer(result: Answer) -> str:
    """Format an ``Answer`` as markdown."""
    if result.outcome == "no_access":
        return (
            "## Answer\n\n"
            "**Outcome:** no_access\n\n"
            "No answer — principal has no access to relevant chunks."
        )
    if result.outcome == "insufficient_context":
        return (
            "## Answer\n\n"
            "**Outcome:** insufficient_context\n\n"
            "No answer — insufficient context in accessible chunks."
        )

    partial = "Yes" if result.is_partial else "No"
    lines = [
        "## Answer",
        "",
        f"**Outcome:** {result.outcome} | **Partial:** {partial}",
        "",
        result.answer or "(empty answer)",
    ]

    if result.citations:
        lines += [
            "",
            "### Citations",
            "",
            "| # | Resource | Score | Excerpt |",
            "|---|----------|-------|---------|",
        ]
        for c in result.citations:
            score_str = f"{c.score:.2f}" if c.score is not None else "n/a"
            lines.append(
                f"| {c.index} | {c.resource_id or c.vector_id} "
                f"| {score_str} | {_truncate(c.text_excerpt, 80)} |"
            )

    # Diagnostics
    retrieval_ms = f"{result.retrieval_latency_ms}ms" if result.retrieval_latency_ms else "n/a"
    synthesis_ms = f"{result.synthesis_latency_ms}ms" if result.synthesis_latency_ms else "n/a"
    lines += [
        "",
        "### Diagnostics",
        f"Allowed: {result.allowed_chunks} | Denied: {result.denied_chunks} | "
        f"Retrieval: {retrieval_ms} | Synthesis: {synthesis_ms}",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def format_simulation(result: SimulationResult) -> str:
    """Format a ``SimulationResult`` as markdown."""
    lines = [
        "## Access Simulation",
        "",
        f"**Outcome:** {result.outcome} | "
        f"**Matched:** {result.matched_resources} | "
        f"**Allowed:** {result.allowed} | "
        f"**Denied:** {result.denied}",
    ]

    if result.denial_reasons:
        lines += ["", "### Denial Reasons"]
        for reason in result.denial_reasons:
            lines.append(f"- {reason}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Connectors
# ---------------------------------------------------------------------------


def format_connectors(page: Page[Connector]) -> str:
    """Format a ``Page[Connector]`` as markdown."""
    lines = [
        f"## Connectors ({page.total} total)",
        "",
        "| Name | Type | Readiness | Status | ID |",
        "|------|------|-----------|--------|----|",
    ]

    for c in page.items:
        readiness = _READINESS_LABELS.get(
            c.policy_readiness_level or 0, f"L{c.policy_readiness_level}"
        )
        lines.append(
            f"| {c.name} | {c.type} | {readiness} | {c.status or 'n/a'} | {c.id} |"
        )

    if not page.items:
        lines.append("| — | — | — | — | — |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Principals
# ---------------------------------------------------------------------------


def format_principals(page: Page[Principal]) -> str:
    """Format a ``Page[Principal]`` as markdown."""
    lines = [
        f"## Principals ({page.total} total, page {page.page}/{page.total_pages})",
        "",
        "| Name | Email | Groups | Roles | ID |",
        "|------|-------|--------|-------|----|",
    ]

    for p in page.items:
        groups = ", ".join(p.groups) if p.groups else "—"
        roles = ", ".join(p.roles) if p.roles else "—"
        lines.append(
            f"| {p.display_name or '—'} | {p.email or '—'} "
            f"| {groups} | {roles} | {p.id} |"
        )

    if not page.items:
        lines.append("| — | — | — | — | — |")

    return "\n".join(lines)

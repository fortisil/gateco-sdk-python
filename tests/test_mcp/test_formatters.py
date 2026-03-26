"""Tests for MCP response formatters."""

from __future__ import annotations

import pytest

from gateco_sdk._pagination import Page
from gateco_sdk.mcp.formatters import (
    format_answer,
    format_connectors,
    format_principals,
    format_retrieval,
    format_simulation,
)
from gateco_sdk.types.answers import Answer, Citation
from gateco_sdk.types.connectors import Connector
from gateco_sdk.types.principals import Principal
from gateco_sdk.types.retrievals import FilterResult, RetrievalOutcome, SecuredRetrieval
from gateco_sdk.types.simulator import SimulationResult


# ---------------------------------------------------------------------------
# format_retrieval
# ---------------------------------------------------------------------------


class TestFormatRetrieval:
    def test_with_results(self):
        r = SecuredRetrieval(
            outcome="partial",
            allowed_chunks=2,
            denied_chunks=1,
            duration_ms=45.0,
            results=[
                FilterResult(vector_id="v1", score=0.92, text="Allowed text here", granted=True, resource_id="doc-001"),
                FilterResult(vector_id="v2", score=0.85, text="More allowed", granted=True, resource_id="doc-002"),
                FilterResult(vector_id="v3", score=0.80, text="Secret", granted=False, resource_id="doc-003"),
            ],
            denial_reasons=["Confidential Data Policy"],
        )
        out = format_retrieval(r)
        assert "## Retrieval Results" in out
        assert "**Outcome:** partial" in out
        assert "**Allowed:** 2" in out
        assert "**Denied:** 1" in out
        assert "45ms" in out
        assert "doc-001" in out
        assert "0.92" in out
        assert "Allowed text here" in out
        # Denied content should NOT appear in allowed table
        assert "Secret" not in out.split("### Denial Summary")[0] or "Secret" not in out
        assert "Confidential Data Policy" in out

    def test_with_outcomes_fallback(self):
        r = SecuredRetrieval(
            outcome="full",
            granted_count=1,
            denied_count=0,
            duration_ms=20.0,
            outcomes=[
                RetrievalOutcome(resource_id="r1", score=0.95, granted=True, text="Hello world"),
            ],
        )
        out = format_retrieval(r)
        assert "r1" in out
        assert "0.95" in out

    def test_empty_results(self):
        r = SecuredRetrieval(outcome="empty", allowed_chunks=0, denied_chunks=0)
        out = format_retrieval(r)
        assert "No allowed chunks" in out

    def test_long_text_truncated(self):
        long_text = "x" * 200
        r = SecuredRetrieval(
            outcome="full",
            allowed_chunks=1,
            results=[FilterResult(vector_id="v1", score=0.9, text=long_text, granted=True)],
        )
        out = format_retrieval(r)
        assert "..." in out
        # Should be truncated to 120 + "..."
        assert ("x" * 121) not in out

    def test_warnings_shown(self):
        r = SecuredRetrieval(
            outcome="full",
            allowed_chunks=0,
            warnings=["Some warning"],
        )
        out = format_retrieval(r)
        assert "Some warning" in out


# ---------------------------------------------------------------------------
# format_answer
# ---------------------------------------------------------------------------


class TestFormatAnswer:
    def test_answered(self):
        a = Answer(
            answer="The answer is 42.",
            outcome="answered",
            is_partial=False,
            allowed_chunks=5,
            denied_chunks=2,
            retrieval_latency_ms=32,
            synthesis_latency_ms=210,
            citations=[
                Citation(index=1, resource_id="doc-001", score=0.92, text_excerpt="relevant text"),
            ],
        )
        out = format_answer(a)
        assert "The answer is 42." in out
        assert "**Outcome:** answered" in out
        assert "**Partial:** No" in out
        assert "doc-001" in out
        assert "0.92" in out
        assert "Allowed: 5" in out
        assert "Denied: 2" in out
        assert "32ms" in out
        assert "210ms" in out

    def test_no_access(self):
        a = Answer(outcome="no_access")
        out = format_answer(a)
        assert "no_access" in out
        assert "no access to relevant chunks" in out

    def test_insufficient_context(self):
        a = Answer(outcome="insufficient_context")
        out = format_answer(a)
        assert "insufficient_context" in out
        assert "insufficient context" in out

    def test_partial_answer(self):
        a = Answer(answer="Partial answer.", outcome="answered", is_partial=True)
        out = format_answer(a)
        assert "**Partial:** Yes" in out

    def test_no_citations(self):
        a = Answer(answer="Simple answer.", outcome="answered", citations=[])
        out = format_answer(a)
        assert "Citations" not in out


# ---------------------------------------------------------------------------
# format_simulation
# ---------------------------------------------------------------------------


class TestFormatSimulation:
    def test_typical(self):
        s = SimulationResult(
            outcome="partial",
            matched_resources=15,
            allowed=12,
            denied=3,
            denial_reasons=["Classification 'confidential' not permitted"],
        )
        out = format_simulation(s)
        assert "## Access Simulation" in out
        assert "**Outcome:** partial" in out
        assert "**Matched:** 15" in out
        assert "**Allowed:** 12" in out
        assert "**Denied:** 3" in out
        assert "confidential" in out

    def test_no_denials(self):
        s = SimulationResult(outcome="full", matched_resources=5, allowed=5, denied=0)
        out = format_simulation(s)
        assert "Denial Reasons" not in out


# ---------------------------------------------------------------------------
# format_connectors
# ---------------------------------------------------------------------------


class TestFormatConnectors:
    def test_populated(self):
        page = Page[Connector](
            items=[
                Connector(id="abc-123", name="Prod DB", type="pgvector", status="active", policy_readiness_level=3),
                Connector(id="def-456", name="Dev DB", type="qdrant", status="active", policy_readiness_level=1),
            ],
            page=1, per_page=20, total=2, total_pages=1,
        )
        out = format_connectors(page)
        assert "## Connectors (2 total)" in out
        assert "Prod DB" in out
        assert "L3 Resource Policy" in out
        assert "Dev DB" in out
        assert "L1 Connection Ready" in out

    def test_empty(self):
        page = Page[Connector](items=[], page=1, per_page=20, total=0, total_pages=1)
        out = format_connectors(page)
        assert "0 total" in out


# ---------------------------------------------------------------------------
# format_principals
# ---------------------------------------------------------------------------


class TestFormatPrincipals:
    def test_populated(self):
        page = Page[Principal](
            items=[
                Principal(
                    id="p1", display_name="Sarah Chen", email="sarah@acme.com",
                    groups=["engineering", "leads"], roles=["admin"],
                ),
            ],
            page=1, per_page=20, total=24, total_pages=2,
        )
        out = format_principals(page)
        assert "## Principals (24 total, page 1/2)" in out
        assert "Sarah Chen" in out
        assert "sarah@acme.com" in out
        assert "engineering, leads" in out
        assert "admin" in out

    def test_empty(self):
        page = Page[Principal](items=[], page=1, per_page=20, total=0, total_pages=1)
        out = format_principals(page)
        assert "0 total" in out

    def test_missing_optional_fields(self):
        page = Page[Principal](
            items=[Principal(id="p1")],
            page=1, per_page=20, total=1, total_pages=1,
        )
        out = format_principals(page)
        # Should show dashes for missing fields
        assert "—" in out

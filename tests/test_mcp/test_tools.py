"""Tests for MCP tool handler functions with mocked SDK client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateco_sdk._pagination import Page
from gateco_sdk.errors import (
    AuthenticationError,
    AuthorizationError,
    EntitlementError,
    GatecoError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from gateco_sdk.mcp.tools import (
    _ToolError,
    handle_ask,
    handle_check_access,
    handle_list_connectors,
    handle_list_principals,
    handle_retrieve,
)
from gateco_sdk.types.answers import Answer, Citation
from gateco_sdk.types.connectors import Connector
from gateco_sdk.types.principals import Principal
from gateco_sdk.types.retrievals import FilterResult, SecuredRetrieval
from gateco_sdk.types.simulator import SimulationResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_client():
    """Create a mock AsyncGatecoClient that supports ``async with``."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ---------------------------------------------------------------------------
# handle_retrieve
# ---------------------------------------------------------------------------


class TestHandleRetrieve:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        client = _mock_client()
        client.retrievals.execute = AsyncMock(
            return_value=SecuredRetrieval(
                outcome="full",
                allowed_chunks=2,
                denied_chunks=0,
                duration_ms=30.0,
                results=[
                    FilterResult(vector_id="v1", score=0.9, text="Hello", granted=True),
                ],
            )
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            result = await handle_retrieve("conn-1", "test query", "user-1", top_k=5)

        assert "Retrieval Results" in result
        assert "Hello" in result
        client.retrievals.execute.assert_called_once_with(
            query="test query",
            principal_id="user-1",
            connector_id="conn-1",
            top_k=5,
            search_mode="vector",
        )

    @pytest.mark.asyncio
    async def test_auth_error(self):
        client = _mock_client()
        client.retrievals.execute = AsyncMock(side_effect=AuthenticationError())
        with patch("gateco_sdk.cli._get_client", return_value=client):
            with pytest.raises(_ToolError, match="Authentication failed"):
                await handle_retrieve("conn-1", "q", "user-1")

    @pytest.mark.asyncio
    async def test_not_found_error(self):
        client = _mock_client()
        client.retrievals.execute = AsyncMock(
            side_effect=NotFoundError("Connector conn-x not found")
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            with pytest.raises(_ToolError, match="Not found"):
                await handle_retrieve("conn-x", "q", "user-1")

    @pytest.mark.asyncio
    async def test_validation_error(self):
        client = _mock_client()
        client.retrievals.execute = AsyncMock(
            side_effect=ValidationError("top_k must be positive")
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            with pytest.raises(_ToolError, match="Invalid request"):
                await handle_retrieve("conn-1", "q", "user-1", top_k=-1)


# ---------------------------------------------------------------------------
# handle_ask
# ---------------------------------------------------------------------------


class TestHandleAsk:
    @pytest.mark.asyncio
    async def test_answered(self):
        client = _mock_client()
        client.answers.execute = AsyncMock(
            return_value=Answer(
                answer="The answer is 42.",
                outcome="answered",
                citations=[Citation(index=1, resource_id="r1", score=0.9, text_excerpt="42")],
                allowed_chunks=3,
                denied_chunks=1,
            )
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            result = await handle_ask("conn-1", "What is the answer?", "user-1")

        assert "The answer is 42." in result
        assert "answered" in result

    @pytest.mark.asyncio
    async def test_no_access(self):
        client = _mock_client()
        client.answers.execute = AsyncMock(
            return_value=Answer(outcome="no_access")
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            result = await handle_ask("conn-1", "secret?", "user-1")

        assert "no access" in result

    @pytest.mark.asyncio
    async def test_insufficient_context(self):
        client = _mock_client()
        client.answers.execute = AsyncMock(
            return_value=Answer(outcome="insufficient_context")
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            result = await handle_ask("conn-1", "vague?", "user-1")

        assert "insufficient context" in result

    @pytest.mark.asyncio
    async def test_entitlement_error(self):
        client = _mock_client()
        client.answers.execute = AsyncMock(
            side_effect=EntitlementError("Pro plan required", upgrade_to="pro")
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            with pytest.raises(_ToolError, match="pro plan"):
                await handle_ask("conn-1", "q", "user-1")

    @pytest.mark.asyncio
    async def test_default_top_k(self):
        client = _mock_client()
        client.answers.execute = AsyncMock(
            return_value=Answer(answer="ok", outcome="answered")
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            await handle_ask("conn-1", "q", "user-1")

        client.answers.execute.assert_called_once_with(
            "q", principal_id="user-1", connector_id="conn-1", top_k=15,
            search_mode="vector",
        )


# ---------------------------------------------------------------------------
# handle_check_access
# ---------------------------------------------------------------------------


class TestHandleCheckAccess:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        client = _mock_client()
        client.simulator.run = AsyncMock(
            return_value=SimulationResult(
                outcome="partial",
                matched_resources=10,
                allowed=7,
                denied=3,
                denial_reasons=["Classification denied"],
            )
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            result = await handle_check_access("user-1", connector_id="conn-1")

        assert "Access Simulation" in result
        assert "Classification denied" in result

    @pytest.mark.asyncio
    async def test_with_resource_ids(self):
        client = _mock_client()
        client.simulator.run = AsyncMock(
            return_value=SimulationResult(outcome="full", matched_resources=2, allowed=2, denied=0)
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            await handle_check_access("user-1", resource_ids=["r1", "r2"])

        client.simulator.run.assert_called_once_with(
            "user-1", connector_id=None, resource_ids=["r1", "r2"],
        )

    @pytest.mark.asyncio
    async def test_authorization_error(self):
        client = _mock_client()
        client.simulator.run = AsyncMock(
            side_effect=AuthorizationError("Not allowed to simulate")
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            with pytest.raises(_ToolError, match="Permission denied"):
                await handle_check_access("user-1")


# ---------------------------------------------------------------------------
# handle_list_connectors
# ---------------------------------------------------------------------------


class TestHandleListConnectors:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        client = _mock_client()
        client.connectors.list = AsyncMock(
            return_value=Page[Connector](
                items=[
                    Connector(id="c1", name="Prod", type="pgvector", status="active", policy_readiness_level=3),
                ],
                page=1, per_page=20, total=1, total_pages=1,
            )
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            result = await handle_list_connectors()

        assert "Prod" in result
        assert "pgvector" in result

    @pytest.mark.asyncio
    async def test_pagination_params_passed(self):
        client = _mock_client()
        client.connectors.list = AsyncMock(
            return_value=Page[Connector](
                items=[], page=2, per_page=5, total=0, total_pages=1,
            )
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            await handle_list_connectors(page=2, per_page=5)

        client.connectors.list.assert_called_once_with(page=2, per_page=5)

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        client = _mock_client()
        client.connectors.list = AsyncMock(
            side_effect=RateLimitError(retry_after=30.0)
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            with pytest.raises(_ToolError, match="Rate limited"):
                await handle_list_connectors()


# ---------------------------------------------------------------------------
# handle_list_principals
# ---------------------------------------------------------------------------


class TestHandleListPrincipals:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        client = _mock_client()
        client.principals.list = AsyncMock(
            return_value=Page[Principal](
                items=[
                    Principal(id="p1", display_name="Sarah", email="sarah@acme.com", groups=["eng"]),
                ],
                page=1, per_page=20, total=1, total_pages=1,
            )
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            result = await handle_list_principals(page=1, per_page=10)

        assert "Sarah" in result
        assert "sarah@acme.com" in result

    @pytest.mark.asyncio
    async def test_pagination_params_passed(self):
        client = _mock_client()
        client.principals.list = AsyncMock(
            return_value=Page[Principal](
                items=[], page=3, per_page=5, total=0, total_pages=1,
            )
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            await handle_list_principals(page=3, per_page=5)

        client.principals.list.assert_called_once_with(page=3, per_page=5)

    @pytest.mark.asyncio
    async def test_generic_gateco_error(self):
        client = _mock_client()
        client.principals.list = AsyncMock(
            side_effect=GatecoError("Something broke", status_code=500)
        )
        with patch("gateco_sdk.cli._get_client", return_value=client):
            with pytest.raises(_ToolError, match="Gateco error"):
                await handle_list_principals()

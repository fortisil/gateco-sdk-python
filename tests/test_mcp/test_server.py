"""Tests for MCP server creation and tool registration."""

from __future__ import annotations

import pytest


class TestCreateServer:
    def test_creates_server(self):
        from gateco_sdk.mcp.server import create_server

        server = create_server()
        assert server is not None
        assert server.name == "gateco"

    def test_server_has_correct_tool_count(self):
        from gateco_sdk.mcp.server import create_server

        server = create_server()
        # FastMCP stores tools internally; list them
        tools = server._tool_manager._tools
        assert len(tools) == 6

    def test_tool_names(self):
        from gateco_sdk.mcp.server import create_server

        server = create_server()
        tool_names = set(server._tool_manager._tools.keys())
        expected = {
            "gateco_retrieve",
            "gateco_ask",
            "gateco_check_access",
            "gateco_list_connectors",
            "gateco_list_principals",
            "gateco_resolve_principal",
        }
        assert tool_names == expected

    def test_retrieve_tool_has_required_params(self):
        from gateco_sdk.mcp.server import create_server

        server = create_server()
        tool = server._tool_manager._tools["gateco_retrieve"]
        # The tool should have parameters defined
        schema = tool.parameters
        assert "connector_id" in schema.get("properties", {})
        assert "query" in schema.get("properties", {})
        assert "principal_id" in schema.get("properties", {})

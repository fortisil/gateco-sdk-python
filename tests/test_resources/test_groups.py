"""Tests for GroupsResource — list + filters, and principals list filters."""

from __future__ import annotations

import httpx
import pytest

from gateco_sdk.types.groups import PrincipalGroup


class TestGroupsList:
    @pytest.mark.asyncio
    async def test_list_returns_page(self, authed_client, mock_api):
        mock_api.get("/api/groups").respond(
            200,
            json={
                "data": [
                    {
                        "id": "g1",
                        "name": "Engineering",
                        "identity_provider_id": "idp1",
                        "identity_provider_name": "Okta OIN",
                        "external_id": "idp1-eng",
                        "member_count": 4,
                        "created_at": "2026-07-29T00:00:00+00:00",
                        "updated_at": "2026-07-29T00:00:00+00:00",
                    },
                    {
                        "id": "g2",
                        "name": "Marketing",
                        "identity_provider_id": "idp1",
                        "identity_provider_name": "Okta OIN",
                        "external_id": "idp1-mkt",
                        "member_count": 0,
                        "created_at": "2026-07-29T00:00:00+00:00",
                        "updated_at": None,
                    },
                ],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "per_page": 20,
                        "total": 2,
                        "total_pages": 1,
                    }
                },
            },
        )
        page = await authed_client.groups.list()
        assert len(page.items) == 2
        assert page.total == 2
        assert isinstance(page.items[0], PrincipalGroup)
        assert page.items[0].name == "Engineering"
        assert page.items[0].member_count == 4
        assert page.items[1].member_count == 0

    @pytest.mark.asyncio
    async def test_list_passes_search_param(self, authed_client, mock_api):
        route = mock_api.get("/api/groups").respond(
            200,
            json={
                "data": [],
                "meta": {
                    "pagination": {
                        "page": 2,
                        "per_page": 5,
                        "total": 0,
                        "total_pages": 1,
                    }
                },
            },
        )
        await authed_client.groups.list(page=2, per_page=5, search="eng")
        request: httpx.Request = route.calls.last.request
        assert request.url.params["page"] == "2"
        assert request.url.params["per_page"] == "5"
        assert request.url.params["search"] == "eng"

    @pytest.mark.asyncio
    async def test_list_omits_search_when_none(self, authed_client, mock_api):
        route = mock_api.get("/api/groups").respond(
            200,
            json={
                "data": [],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "per_page": 20,
                        "total": 0,
                        "total_pages": 1,
                    }
                },
            },
        )
        await authed_client.groups.list()
        request: httpx.Request = route.calls.last.request
        assert "search" not in request.url.params


class TestPrincipalsListFilters:
    @pytest.mark.asyncio
    async def test_list_passes_status_search_group(self, authed_client, mock_api):
        route = mock_api.get("/api/principals").respond(
            200,
            json={
                "data": [],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "per_page": 20,
                        "total": 0,
                        "total_pages": 1,
                    }
                },
            },
        )
        await authed_client.principals.list(
            status="all", search="ada", group="eng"
        )
        request: httpx.Request = route.calls.last.request
        assert request.url.params["status"] == "all"
        assert request.url.params["search"] == "ada"
        assert request.url.params["group"] == "eng"

    @pytest.mark.asyncio
    async def test_list_default_omits_filter_params(self, authed_client, mock_api):
        """Backward-compat: no filter kwargs -> no filter query params sent."""
        route = mock_api.get("/api/principals").respond(
            200,
            json={
                "data": [],
                "meta": {
                    "pagination": {
                        "page": 1,
                        "per_page": 20,
                        "total": 0,
                        "total_pages": 1,
                    }
                },
            },
        )
        await authed_client.principals.list()
        request: httpx.Request = route.calls.last.request
        assert "status" not in request.url.params
        assert "search" not in request.url.params
        assert "group" not in request.url.params

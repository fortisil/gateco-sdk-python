"""Tests for RetrievalsResource — execute, list, get."""

from __future__ import annotations

import pytest

from gateco_sdk.types.retrievals import SecuredRetrieval
from tests.conftest import BASE_URL


class TestRetrievalExecute:
    @pytest.mark.asyncio
    async def test_execute_with_vector(self, authed_client, mock_api):
        mock_api.post("/api/retrievals/execute").respond(
            200,
            json={
                "id": "ret-1",
                "principal_id": "p1",
                "connector_id": "c1",
                "status": "completed",
                "total_results": 3,
                "granted_count": 2,
                "denied_count": 1,
                "outcomes": [
                    {"resource_id": "r1", "score": 0.95, "granted": True, "policy_traces": []},
                    {"resource_id": "r2", "score": 0.88, "granted": True, "policy_traces": []},
                    {
                        "resource_id": "r3",
                        "score": 0.75,
                        "granted": False,
                        "denial_reason": {"code": "POLICY_DENY", "message": "access denied"},
                        "policy_traces": [{"policy_id": "pol-1", "decision": "deny"}],
                    },
                ],
            },
        )
        result = await authed_client.retrievals.execute(
            [0.1, 0.2, 0.3, 0.4],
            principal_id="p1",
            connector_id="c1",
            top_k=10,
        )
        assert isinstance(result, SecuredRetrieval)
        assert result.id == "ret-1"
        assert result.granted_count == 2
        assert result.denied_count == 1
        assert len(result.outcomes) == 3
        assert result.outcomes[0].granted is True
        assert result.outcomes[2].granted is False

    @pytest.mark.asyncio
    async def test_execute_with_filters(self, authed_client, mock_api):
        mock_api.post("/api/retrievals/execute").respond(
            200,
            json={
                "id": "ret-2",
                "status": "completed",
                "total_results": 0,
                "granted_count": 0,
                "denied_count": 0,
                "outcomes": [],
            },
        )
        result = await authed_client.retrievals.execute(
            [0.1, 0.2],
            principal_id="p1",
            connector_id="c1",
            filters={"domain": "engineering"},
        )
        assert result.total_results == 0

    @pytest.mark.asyncio
    async def test_execute_with_include_unresolved(self, authed_client, mock_api):
        mock_api.post("/api/retrievals/execute").respond(
            200,
            json={
                "id": "ret-3",
                "status": "completed",
                "total_results": 1,
                "granted_count": 0,
                "denied_count": 0,
                "outcomes": [
                    {"resource_id": "unresolved-1", "score": 0.6, "granted": False, "policy_traces": []},
                ],
            },
        )
        result = await authed_client.retrievals.execute(
            [0.1],
            principal_id="p1",
            connector_id="c1",
            include_unresolved=True,
        )
        assert result.total_results == 1


class TestRetrievalList:
    @pytest.mark.asyncio
    async def test_list_retrievals(self, authed_client, mock_api):
        mock_api.get("/api/retrievals").respond(
            200,
            json={
                "data": [
                    {
                        "id": "ret-1",
                        "status": "completed",
                        "total_results": 5,
                        "granted_count": 3,
                        "denied_count": 2,
                        "outcomes": [],
                    },
                    {
                        "id": "ret-2",
                        "status": "completed",
                        "total_results": 1,
                        "granted_count": 1,
                        "denied_count": 0,
                        "outcomes": [],
                    },
                ],
                "meta": {
                    "pagination": {"page": 1, "per_page": 20, "total": 2, "total_pages": 1}
                },
            },
        )
        page = await authed_client.retrievals.list()
        assert len(page.items) == 2
        assert page.total == 2
        assert page.items[0].id == "ret-1"

    @pytest.mark.asyncio
    async def test_list_with_filters(self, authed_client, mock_api):
        mock_api.get("/api/retrievals").respond(
            200,
            json={
                "data": [],
                "meta": {"pagination": {"page": 1, "per_page": 20, "total": 0, "total_pages": 0}},
            },
        )
        page = await authed_client.retrievals.list(status="failed")
        assert page.total == 0


class TestRetrievalGet:
    @pytest.mark.asyncio
    async def test_get_by_id(self, authed_client, mock_api):
        mock_api.get("/api/retrievals/ret-1").respond(
            200,
            json={
                "id": "ret-1",
                "principal_id": "p1",
                "connector_id": "c1",
                "status": "completed",
                "total_results": 2,
                "granted_count": 1,
                "denied_count": 1,
                "outcomes": [
                    {"resource_id": "r1", "score": 0.9, "granted": True, "policy_traces": []},
                    {"resource_id": "r2", "score": 0.7, "granted": False, "policy_traces": []},
                ],
            },
        )
        result = await authed_client.retrievals.get("ret-1")
        assert isinstance(result, SecuredRetrieval)
        assert result.id == "ret-1"
        assert result.principal_id == "p1"
        assert result.connector_id == "c1"


class TestRetrievalListAll:
    @pytest.mark.asyncio
    async def test_list_all_paginates(self, authed_client, mock_api):
        call_count = 0

        def respond(request):
            nonlocal call_count
            call_count += 1
            from httpx import Response

            if call_count == 1:
                return Response(
                    200,
                    json={
                        "data": [{"id": "ret-1", "status": "completed", "total_results": 0, "granted_count": 0, "denied_count": 0, "outcomes": []}],
                        "meta": {"pagination": {"page": 1, "per_page": 1, "total": 2, "total_pages": 2}},
                    },
                )
            return Response(
                200,
                json={
                    "data": [{"id": "ret-2", "status": "completed", "total_results": 0, "granted_count": 0, "denied_count": 0, "outcomes": []}],
                    "meta": {"pagination": {"page": 2, "per_page": 1, "total": 2, "total_pages": 2}},
                },
            )

        mock_api.get("/api/retrievals").mock(side_effect=respond)
        items = await authed_client.retrievals.list_all(per_page=1).collect()
        assert len(items) == 2
        assert items[0].id == "ret-1"
        assert items[1].id == "ret-2"

"""``end_user_token`` becomes the ``X-End-User-Token`` header, and only when given.

The header is what the server verifies against the issuing identity
provider's JWKS; sending it empty or sending it when the caller did not ask
would either fail closed for no reason or silently claim a verification that
never happened.
"""

from __future__ import annotations

import pytest

_RECORD = {"id": "ret-1", "principal_id": "p1", "connector_id": "c1", "subject_verified": True}


class TestEndUserTokenHeader:
    @pytest.mark.asyncio
    async def test_execute_sends_the_header_when_given(self, authed_client, mock_api):
        route = mock_api.post("/api/retrievals/execute").respond(200, json=_RECORD)

        result = await authed_client.retrievals.execute(
            query="q", principal_id="p1", connector_id="c1", end_user_token="eyJ.tok.en"
        )

        assert route.calls.last.request.headers["X-End-User-Token"] == "eyJ.tok.en"
        assert result.subject_verified is True

    @pytest.mark.asyncio
    async def test_execute_sends_no_header_when_omitted(self, authed_client, mock_api):
        route = mock_api.post("/api/retrievals/execute").respond(200, json={**_RECORD, "subject_verified": False})

        result = await authed_client.retrievals.execute(query="q", principal_id="p1", connector_id="c1")

        assert "X-End-User-Token" not in route.calls.last.request.headers
        assert result.subject_verified is False

    @pytest.mark.asyncio
    async def test_filter_sends_the_header(self, authed_client, mock_api):
        route = mock_api.post("/api/retrievals/filter").respond(200, json=_RECORD)

        await authed_client.retrievals.filter(
            principal_id="p1", connector_id="c1",
            candidates=[{"vector_id": "v", "score": 0.5, "text": "t"}], end_user_token="tok",
        )

        assert route.calls.last.request.headers["X-End-User-Token"] == "tok"

    @pytest.mark.asyncio
    async def test_answers_sends_the_header(self, authed_client, mock_api):
        route = mock_api.post("/api/answers/execute").respond(
            200, json={"answer": "a", "outcome": "answered", "citations": []}
        )

        await authed_client.answers.execute(
            "why?", principal_id="p1", connector_id="c1", end_user_token="tok"
        )

        assert route.calls.last.request.headers["X-End-User-Token"] == "tok"

    @pytest.mark.asyncio
    async def test_auth_header_wins_over_a_caller_supplied_one(self, authed_client, mock_api):
        """A caller must not be able to overwrite the credential via the headers kwarg."""
        route = mock_api.get("/api/retrievals/ret-1").respond(200, json=_RECORD)

        await authed_client._request(
            "GET", "/api/retrievals/ret-1", headers={"Authorization": "Bearer forged"}
        )

        assert route.calls.last.request.headers["Authorization"] != "Bearer forged"


class TestRecordFields:
    @pytest.mark.asyncio
    async def test_actor_fields_are_typed(self, authed_client, mock_api):
        mock_api.get("/api/retrievals/ret-9").respond(200, json={
            "id": "ret-9", "actor_type": "api_key", "actor_name": "API key 'agent' (gck_ab12)",
            "actor_id": None, "api_key_id": "key-1", "subject_verified": False,
        })
        r = await authed_client.retrievals.get("ret-9")
        assert r.actor_type == "api_key"
        assert r.api_key_id == "key-1"
        assert r.actor_id is None
        assert r.subject_verified is False

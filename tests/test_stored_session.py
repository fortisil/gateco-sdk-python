"""1.13.0 (#8): the client reads the session `gateco login` stored, and writes refreshes back.

Cold run 2026-09-25: `AsyncGatecoClient()` with no credential raised on first use even
though the user had just run `gateco login`; copying the file's refresh token into a
second client revoked the CLI's (refresh rotates). These tests pin the fallback order,
the base_url carry-over, the write-back on refresh, and that nothing is read when a key
or token is supplied explicitly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from gateco_sdk import cli
from gateco_sdk._credentials import load_stored_session, save_stored_session
from gateco_sdk.client import AsyncGatecoClient, GatecoClient
from tests.conftest import make_jwt


def _write(path: Path, access: str, refresh: str | None = "ref_1", base_url: str | None = "http://stored.gateco.local/api") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"access_token": access, "refresh_token": refresh, "base_url": base_url}))


class TestFallbackOrder:
    def test_no_credential_reads_the_stored_session_and_its_base_url(self, tmp_path, monkeypatch):
        f = tmp_path / "creds.json"
        _write(f, make_jwt(exp=9e9))
        monkeypatch.setenv("GATECO_CREDENTIALS_FILE", str(f))
        monkeypatch.delenv("GATECO_API_KEY", raising=False)
        monkeypatch.delenv("GATECO_BASE_URL", raising=False)

        client = AsyncGatecoClient()

        assert client._token_manager.access_token is not None
        assert client._token_manager.refresh_token == "ref_1"
        # the CLI stores the URL it was given, sometimes with /api; the SDK wants the root
        assert client._transport.base_url.rstrip("/") == "http://stored.gateco.local"
        assert client._session_file == f

    def test_explicit_base_url_and_env_win_over_the_file(self, tmp_path, monkeypatch):
        f = tmp_path / "creds.json"
        _write(f, make_jwt(exp=9e9))
        monkeypatch.setenv("GATECO_CREDENTIALS_FILE", str(f))
        monkeypatch.delenv("GATECO_API_KEY", raising=False)

        monkeypatch.setenv("GATECO_BASE_URL", "http://env.gateco.local")
        assert AsyncGatecoClient()._transport.base_url.rstrip("/") == "http://env.gateco.local"
        assert AsyncGatecoClient("http://arg.gateco.local")._transport.base_url.rstrip("/") == "http://arg.gateco.local"

    def test_api_key_argument_or_env_skips_the_file(self, tmp_path, monkeypatch):
        f = tmp_path / "creds.json"
        _write(f, make_jwt(exp=9e9))
        monkeypatch.setenv("GATECO_CREDENTIALS_FILE", str(f))

        monkeypatch.delenv("GATECO_API_KEY", raising=False)
        by_arg = AsyncGatecoClient(api_key="gck_test_x")
        assert by_arg._token_manager.access_token is None
        assert by_arg._session_file is None

        monkeypatch.setenv("GATECO_API_KEY", "gck_test_env")
        by_env = AsyncGatecoClient()
        assert by_env._token_manager.access_token is None
        assert by_env._session_file is None

    def test_explicit_access_token_skips_the_file(self, tmp_path, monkeypatch):
        f = tmp_path / "creds.json"
        _write(f, "stored_token")
        monkeypatch.setenv("GATECO_CREDENTIALS_FILE", str(f))
        monkeypatch.delenv("GATECO_API_KEY", raising=False)

        client = AsyncGatecoClient(access_token="given_token")

        assert client._token_manager.access_token == "given_token"
        assert client._session_file is None

    def test_missing_or_malformed_file_means_unauthenticated(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GATECO_API_KEY", raising=False)
        monkeypatch.setenv("GATECO_CREDENTIALS_FILE", str(tmp_path / "absent.json"))
        assert AsyncGatecoClient()._token_manager.access_token is None

        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        monkeypatch.setenv("GATECO_CREDENTIALS_FILE", str(bad))
        assert AsyncGatecoClient()._token_manager.access_token is None
        assert load_stored_session(bad) is None

    def test_sync_client_gets_the_same_fallback(self, tmp_path, monkeypatch):
        f = tmp_path / "creds.json"
        _write(f, make_jwt(exp=9e9))
        monkeypatch.setenv("GATECO_CREDENTIALS_FILE", str(f))
        monkeypatch.delenv("GATECO_API_KEY", raising=False)
        monkeypatch.delenv("GATECO_BASE_URL", raising=False)

        client = GatecoClient()

        assert client._async_client._token_manager.refresh_token == "ref_1"
        assert client._async_client._transport.base_url.rstrip("/") == "http://stored.gateco.local"


class TestWriteBack:
    @pytest.mark.asyncio
    async def test_refresh_writes_the_rotated_pair_back_to_the_file(self, tmp_path, monkeypatch):
        """Refresh rotates server-side; the next process must find the new pair."""
        f = tmp_path / "creds.json"
        _write(f, make_jwt(exp=0), refresh="ref_old", base_url="http://stored.gateco.local")
        monkeypatch.setenv("GATECO_CREDENTIALS_FILE", str(f))
        monkeypatch.delenv("GATECO_API_KEY", raising=False)
        monkeypatch.delenv("GATECO_BASE_URL", raising=False)
        new_access = make_jwt(exp=9e9)

        async with respx.mock(base_url="http://stored.gateco.local") as mock:
            mock.post("/api/auth/refresh").mock(
                return_value=Response(200, json={"access_token": new_access, "refresh_token": "ref_new", "token_type": "bearer"})
            )
            mock.get("/api/connectors").mock(return_value=Response(200, json={"data": [], "meta": {"pagination": {"page": 1, "per_page": 20, "total": 0, "total_pages": 0}}}))
            async with AsyncGatecoClient() as client:
                await client.connectors.list()

        stored = json.loads(f.read_text())
        assert stored["access_token"] == new_access
        assert stored["refresh_token"] == "ref_new"
        assert stored["base_url"] == "http://stored.gateco.local"

    @pytest.mark.asyncio
    async def test_explicit_tokens_are_never_written_to_the_file(self, tmp_path, monkeypatch):
        f = tmp_path / "creds.json"
        monkeypatch.setenv("GATECO_CREDENTIALS_FILE", str(f))
        monkeypatch.delenv("GATECO_API_KEY", raising=False)

        async with respx.mock(base_url="http://x.gateco.local") as mock:
            mock.post("/api/auth/refresh").mock(
                return_value=Response(200, json={"access_token": make_jwt(exp=9e9), "refresh_token": "r2", "token_type": "bearer"})
            )
            mock.get("/api/connectors").mock(return_value=Response(200, json={"data": [], "meta": {"pagination": {"page": 1, "per_page": 20, "total": 0, "total_pages": 0}}}))
            async with AsyncGatecoClient("http://x.gateco.local", access_token=make_jwt(exp=0), refresh_token="r1") as client:
                await client.connectors.list()

        assert not f.exists()


class TestCliCompatibility:
    def test_sdk_reads_what_the_cli_writes(self, tmp_path, monkeypatch):
        """`gateco login` and the SDK must agree on the file; this pins the shape."""
        cred_file = tmp_path / ".gateco" / "credentials.json"
        monkeypatch.setattr("gateco_sdk.cli._CRED_DIR", cred_file.parent)
        monkeypatch.setattr("gateco_sdk.cli._CRED_FILE", cred_file)
        monkeypatch.setenv("GATECO_CREDENTIALS_FILE", str(cred_file))
        monkeypatch.delenv("GATECO_API_KEY", raising=False)
        monkeypatch.delenv("GATECO_BASE_URL", raising=False)

        cli._save_credentials(make_jwt(exp=9e9), "ref_cli", "http://cli.gateco.local/api")
        client = AsyncGatecoClient()

        assert client._token_manager.refresh_token == "ref_cli"
        assert client._transport.base_url.rstrip("/") == "http://cli.gateco.local"

    def test_sdk_writes_what_the_cli_reads(self, tmp_path, monkeypatch):
        cred_file = tmp_path / ".gateco" / "credentials.json"
        monkeypatch.setattr("gateco_sdk.cli._CRED_DIR", cred_file.parent)
        monkeypatch.setattr("gateco_sdk.cli._CRED_FILE", cred_file)
        monkeypatch.delenv("GATECO_API_KEY", raising=False)
        monkeypatch.delenv("GATECO_BASE_URL", raising=False)

        save_stored_session("tok", "ref", "http://sdk.gateco.local", path=cred_file)
        creds = cli._load_credentials()

        assert creds["access_token"] == "tok"
        assert creds["refresh_token"] == "ref"
        assert creds["base_url"] == "http://sdk.gateco.local"
        assert oct(cred_file.stat().st_mode & 0o777) == "0o600"

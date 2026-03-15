"""Tests for the Gateco CLI module."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateco_sdk.cli import (
    _build_parser,
    _load_credentials,
    _save_credentials,
    main,
)


# ---------------------------------------------------------------------------
# Credential save / load
# ---------------------------------------------------------------------------


class TestCredentials:
    """Test credential persistence helpers."""

    def test_save_and_load(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Credentials round-trip through save then load."""
        cred_dir = tmp_path / ".gateco"
        cred_file = cred_dir / "credentials.json"

        monkeypatch.setattr("gateco_sdk.cli._CRED_DIR", cred_dir)
        monkeypatch.setattr("gateco_sdk.cli._CRED_FILE", cred_file)

        _save_credentials("tok_abc", "ref_xyz", "http://example.com/api")

        assert cred_file.exists()
        # Verify file permissions are 0600
        file_stat = os.stat(cred_file)
        assert stat.S_IMODE(file_stat.st_mode) == 0o600

        creds = _load_credentials()
        assert creds["access_token"] == "tok_abc"
        assert creds["refresh_token"] == "ref_xyz"
        assert creds["base_url"] == "http://example.com/api"

    def test_load_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Loading from a non-existent file returns defaults."""
        cred_file = tmp_path / ".gateco" / "credentials.json"
        monkeypatch.setattr("gateco_sdk.cli._CRED_FILE", cred_file)
        monkeypatch.delenv("GATECO_API_KEY", raising=False)
        monkeypatch.delenv("GATECO_BASE_URL", raising=False)

        creds = _load_credentials()
        assert creds["access_token"] is None
        assert creds["api_key"] is None

    def test_env_vars_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Environment variables override file-based credentials."""
        cred_dir = tmp_path / ".gateco"
        cred_file = cred_dir / "credentials.json"

        monkeypatch.setattr("gateco_sdk.cli._CRED_DIR", cred_dir)
        monkeypatch.setattr("gateco_sdk.cli._CRED_FILE", cred_file)

        # Save some file-based credentials
        _save_credentials("file_token", "file_refresh", "http://file.com/api")

        # Override via env vars
        monkeypatch.setenv("GATECO_API_KEY", "env_api_key")
        monkeypatch.setenv("GATECO_BASE_URL", "http://env.com/api")

        creds = _load_credentials()
        assert creds["api_key"] == "env_api_key"
        assert creds["base_url"] == "http://env.com/api"
        # File-based token is still loaded
        assert creds["access_token"] == "file_token"


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


class TestArgParsing:
    """Test the argparse structure."""

    def test_login_args(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["login", "--email", "a@b.com", "--password", "secret"])
        assert args.command == "login"
        assert args.email == "a@b.com"
        assert args.password == "secret"
        assert args.base_url == "http://localhost:8000/api"

    def test_login_custom_url(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            ["login", "--email", "a@b.com", "--password", "s", "--base-url", "http://x.com/api"]
        )
        assert args.base_url == "http://x.com/api"

    def test_ingest_args(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            [
                "ingest",
                "doc.txt",
                "--connector-id",
                "c1",
                "--classification",
                "internal",
                "--sensitivity",
                "high",
                "--domain",
                "engineering",
            ]
        )
        assert args.command == "ingest"
        assert args.file == "doc.txt"
        assert args.connector_id == "c1"
        assert args.classification == "internal"
        assert args.sensitivity == "high"
        assert args.domain == "engineering"

    def test_ingest_batch_args(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            ["ingest-batch", "/tmp/docs", "--connector-id", "c2", "--glob", "*.md"]
        )
        assert args.command == "ingest-batch"
        assert args.directory == "/tmp/docs"
        assert args.connector_id == "c2"
        assert args.glob == "*.md"

    def test_retrieve_args(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            [
                "retrieve",
                "--vector-file",
                "vec.json",
                "--principal-id",
                "p1",
                "--connector-id",
                "c1",
                "--top-k",
                "5",
            ]
        )
        assert args.command == "retrieve"
        assert args.vector_file == "vec.json"
        assert args.principal_id == "p1"
        assert args.connector_id == "c1"
        assert args.top_k == 5

    def test_connectors_list(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["connectors", "list"])
        assert args.command == "connectors"
        assert args.subcommand == "list"

    def test_connectors_test(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["connectors", "test", "abc-123"])
        assert args.command == "connectors"
        assert args.subcommand == "test"
        assert args.connector_id == "abc-123"

    def test_connectors_create(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            [
                "connectors",
                "create",
                "--name",
                "My DB",
                "--type",
                "pgvector",
                "--config",
                '{"host": "localhost"}',
            ]
        )
        assert args.command == "connectors"
        assert args.subcommand == "create"
        assert args.name == "My DB"
        assert args.type == "pgvector"
        assert args.config == '{"host": "localhost"}'

    def test_policies_list(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["policies", "list"])
        assert args.command == "policies"
        assert args.subcommand == "list"

    def test_policies_create(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["policies", "create", "--from-file", "policy.json"])
        assert args.command == "policies"
        assert args.subcommand == "create"
        assert args.from_file == "policy.json"

    def test_retroactive_register(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(
            [
                "retroactive-register",
                "--connector-id",
                "c1",
                "--scan-limit",
                "3000",
                "--dry-run",
            ]
        )
        assert args.command == "retroactive-register"
        assert args.connector_id == "c1"
        assert args.scan_limit == 3000
        assert args.dry_run is True

    def test_audit_list(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["audit", "list", "--page", "2", "--per-page", "50"])
        assert args.command == "audit"
        assert args.subcommand == "list"
        assert args.page == 2
        assert args.per_page == 50


# ---------------------------------------------------------------------------
# Login command (mocked)
# ---------------------------------------------------------------------------


class TestLoginCommand:
    """Test the login command with mocked SDK calls."""

    def test_login_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        """Login stores credentials and outputs user info."""
        cred_dir = tmp_path / ".gateco"
        cred_file = cred_dir / "credentials.json"
        monkeypatch.setattr("gateco_sdk.cli._CRED_DIR", cred_dir)
        monkeypatch.setattr("gateco_sdk.cli._CRED_FILE", cred_file)

        mock_user = MagicMock()
        mock_user.email = "test@example.com"

        mock_token_resp = MagicMock()
        mock_token_resp.access_token = "new_access"
        mock_token_resp.refresh_token = "new_refresh"
        mock_token_resp.user = mock_user

        mock_client = AsyncMock()
        mock_client.login = AsyncMock(return_value=mock_token_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("gateco_sdk.client.AsyncGatecoClient", return_value=mock_client):
            monkeypatch.setattr(
                "sys.argv",
                ["gateco", "login", "--email", "test@example.com", "--password", "pass"],
            )
            main()

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "ok"
        assert output["user"] == "test@example.com"

        # Verify credentials were saved
        assert cred_file.exists()
        stored = json.loads(cred_file.read_text())
        assert stored["access_token"] == "new_access"
        assert stored["refresh_token"] == "new_refresh"

    def test_no_command_shows_help(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Running without a command exits with code 1."""
        monkeypatch.setattr("sys.argv", ["gateco"])
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

"""1.13.0 (#2/#18): connector search and ingestion configs get CLI verbs."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateco_sdk.cli import _build_parser, main
from gateco_sdk.types import CLASSIFICATIONS, SENSITIVITIES, Classification, Sensitivity


def _client() -> AsyncMock:
    c = AsyncMock()
    c.connectors = MagicMock()
    for name in ("get", "get_search_config", "update_search_config", "get_ingestion_config", "update_ingestion_config"):
        setattr(c.connectors, name, AsyncMock(return_value={"ok": name}))
    c.__aenter__ = AsyncMock(return_value=c)
    c.__aexit__ = AsyncMock(return_value=False)
    return c


class TestParser:
    @pytest.mark.parametrize("verb", ["get", "get-search-config", "get-ingestion-config"])
    def test_read_verbs_take_a_connector_id(self, verb):
        args = _build_parser().parse_args(["connectors", verb, "c1"])
        assert (args.command, args.subcommand, args.connector_id) == ("connectors", verb, "c1")

    @pytest.mark.parametrize("verb", ["set-search-config", "set-ingestion-config"])
    def test_set_verbs_need_exactly_one_source(self, verb, capsys):
        p = _build_parser()
        assert p.parse_args(["connectors", verb, "c1", "--json", "{}"]).config_json == "{}"
        assert p.parse_args(["connectors", verb, "c1", "--file", "x.json"]).config_file == "x.json"
        with pytest.raises(SystemExit):
            p.parse_args(["connectors", verb, "c1"])
        with pytest.raises(SystemExit):
            p.parse_args(["connectors", verb, "c1", "--json", "{}", "--file", "x.json"])

    def test_ingest_label_flags_list_the_vocabulary(self):
        p = _build_parser()
        args = p.parse_args(["ingest", "f.txt", "--connector-id", "c1", "--classification", "confidential", "--sensitivity", "high"])
        assert (args.classification, args.sensitivity) == ("confidential", "high")
        with pytest.raises(SystemExit):
            p.parse_args(["ingest", "f.txt", "--connector-id", "c1", "--classification", "secret"])


class TestHandlers:
    def test_set_search_config_from_json_flag(self, monkeypatch, capsys):
        client = _client()
        with patch("gateco_sdk.cli._get_client", return_value=client):
            monkeypatch.setattr("sys.argv", ["gateco", "connectors", "set-search-config", "c1", "--json", '{"table_name": "docs"}'])
            main()
        client.connectors.update_search_config.assert_awaited_once_with("c1", {"table_name": "docs"})
        assert json.loads(capsys.readouterr().out) == {"ok": "update_search_config"}

    def test_set_ingestion_config_from_file(self, monkeypatch, tmp_path, capsys):
        f = tmp_path / "ing.json"
        f.write_text(json.dumps({"chunk_size": 512}))
        client = _client()
        with patch("gateco_sdk.cli._get_client", return_value=client):
            monkeypatch.setattr("sys.argv", ["gateco", "connectors", "set-ingestion-config", "c1", "--file", str(f)])
            main()
        client.connectors.update_ingestion_config.assert_awaited_once_with("c1", {"chunk_size": 512})

    def test_non_object_json_is_refused_before_any_call(self, monkeypatch, capsys):
        client = _client()
        with patch("gateco_sdk.cli._get_client", return_value=client):
            monkeypatch.setattr("sys.argv", ["gateco", "connectors", "set-search-config", "c1", "--json", "[1, 2]"])
            with pytest.raises(SystemExit):
                main()
        client.connectors.update_search_config.assert_not_awaited()
        assert "JSON object" in capsys.readouterr().err

    @pytest.mark.parametrize("verb,method", [("get", "get"), ("get-search-config", "get_search_config"), ("get-ingestion-config", "get_ingestion_config")])
    def test_read_verbs_call_through(self, verb, method, monkeypatch, capsys):
        client = _client()
        with patch("gateco_sdk.cli._get_client", return_value=client):
            monkeypatch.setattr("sys.argv", ["gateco", "connectors", verb, "c9"])
            main()
        getattr(client.connectors, method).assert_awaited_once_with("c9")


class TestLabelVocabulary:
    def test_exported_and_matching_the_server_enums(self):
        assert CLASSIFICATIONS == ("public", "internal", "confidential", "restricted")
        assert SENSITIVITIES == ("low", "medium", "high", "critical")
        assert Classification is not None and Sensitivity is not None

    def test_request_models_reject_a_non_vocabulary_value(self):
        from pydantic import ValidationError

        from gateco_sdk.types import IngestDocumentRequest

        with pytest.raises(ValidationError):
            IngestDocumentRequest(connector_id="c", external_resource_id="r", text="t", classification="secret")
        assert IngestDocumentRequest(connector_id="c", external_resource_id="r", text="t", classification="internal").classification == "internal"

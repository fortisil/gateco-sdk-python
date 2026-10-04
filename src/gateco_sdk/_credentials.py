"""The stored session file, shared by the CLI, the MCP server and the client (1.13.0, #8).

``gateco login`` writes ``~/.gateco/credentials.json`` (mode 0600) with
``access_token``, ``refresh_token`` and ``base_url``. Until 1.13.0 only the CLI
and the MCP server read it; ``AsyncGatecoClient()`` with no credential at all
raised on the first call, so the "same machine, same login" path documented
in the quickstart did not exist (cold run 2026-09-25, finding #8, the root of
the three session expiries in #16 and #19).

Since 1.13.0 a client constructed with no ``api_key`` argument, no
``GATECO_API_KEY`` and no ``access_token`` loads this file and, because refresh
ROTATES (every ``POST /api/auth/refresh`` revokes the pair it was called
with), writes the refreshed pair back so the next process does not fail with
``Invalid or expired refresh token``.

``GATECO_CREDENTIALS_FILE`` overrides the path (tests, containers).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ENV_CREDENTIALS_FILE = "GATECO_CREDENTIALS_FILE"


def default_credentials_path() -> Path:
    """``$GATECO_CREDENTIALS_FILE`` if set, else ``~/.gateco/credentials.json``."""
    override = os.environ.get(ENV_CREDENTIALS_FILE)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".gateco" / "credentials.json"


def load_stored_session(path: Path | None = None) -> dict[str, Any] | None:
    """Return ``{access_token, refresh_token, base_url}`` or ``None`` when absent/unusable.

    Never raises: a missing, unreadable or malformed file means "no stored session".
    """
    p = path or default_credentials_path()
    try:
        if not p.exists():
            return None
        data = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or not data.get("access_token"):
        return None
    return {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "base_url": data.get("base_url"),
    }


def save_stored_session(
    access_token: str,
    refresh_token: str | None,
    base_url: str | None,
    path: Path | None = None,
) -> None:
    """Write the session file (mode 0600). Same shape ``gateco login`` writes."""
    p = path or default_credentials_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(
            {"access_token": access_token, "refresh_token": refresh_token, "base_url": base_url},
            indent=2,
        )
    )
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass

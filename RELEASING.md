# Releasing the Python SDK (which is also releasing the MCP server)

The MCP server ships inside this package and is listed in the official MCP registry as
`ai.gateco/gateco`. There is no separate MCP package. **Every `sdk-python-v*` tag is an
MCP release that strangers install from a marketplace**, and an MCP failure is read by a
model, not a person. This checklist exists because until 2 October 2026 nobody ran one
(Jordi's MCP quality pass, 27 September; the registry served 1.11.1 for two releases
because publishing was manual and nobody watched it).

The tag workflow (`.github/workflows/publish-sdk-python.yml`) enforces steps 2 and 7 by
machine. The rest is yours.

## Before the tag

1. **CHANGELOG.md** has an entry for the version, dated, with every user-visible change.
   Behaviour fix = patch; new public API = minor.
2. **Version in four places agrees**: `src/gateco_sdk/_version.py`, `pyproject.toml`,
   and both `version` fields in `server.json`. Preflight refuses the tag otherwise.
3. **MCP tool descriptions match the docs**: `src/gateco_sdk/mcp/server.py` docstrings
   (what a host shows the model) against the tool table in `README.md` and
   `apps/website/public/llms-full.txt`, including which tools need a user session.
   `server.json`'s `GATECO_API_KEY` description says how many tools run on a key.
4. **Suite green**: `pytest -v` here (the MCP tests in `tests/test_mcp/` included) and
   `ruff check src tests` with no new findings.
5. **Activation walk green** against the backend version production runs:
   `gateco/tests/mcp_activation/run.py` from the built wheel (the `mcp-activation` CI
   job does this on every push; run it by hand when the SDK describes a server behaviour
   that production does not have yet, and do not tag until it does).
6. **Backend first** when the SDK documents a server change (1.13.0: `gateco_list_groups`
   on a `retrieve` key needs `GET /api/groups` on that scope). The SDK on PyPI must
   describe the API at `api.gateco.ai`, not the API on `main`.
7. **TypeScript parity**: if the change has a TypeScript counterpart, its version and
   changelog move in the same PR; `npm run build` proves it compiles.
8. **Docs walked** (`CLAUDE.md`, pre-merge gate step 0b): README, `llms.txt`,
   `llms-full.txt`, the website `/docs` and `/docs/mcp-server` pages; rebuild the help
   corpus if any source changed.

## The tag

9. `git tag sdk-python-v<version> && git push origin sdk-python-v<version>` on the merged
   commit. The workflow: preflight (versions, registry secret present) → PyPI (Trusted
   Publishing, no token) → wait until PyPI serves the version → `mcp-publisher login dns
   --domain gateco.ai` and publish `server.json` → read back
   `/v0/servers/ai.gateco%2Fgateco/versions/latest`. Any step failing fails the release.

## After the tag

10. **Read back by hand**: `pip index versions gateco` (or the PyPI page),
    the registry `versions/latest`, and `pip install "gateco[mcp]==<version>"` in a clean
    venv followed by `python -c "import gateco_sdk; print(gateco_sdk.__version__)"` and
    `python -c "import gateco_sdk.mcp.server"` (the CLI has no `--version` flag; found on
    the 1.13.0 read-back, 4 Oct 2026). For npm: `npm view @gateco/sdk version`, allowing a
    minute for propagation (1.13.0 read 1.12.0 for about thirty seconds after publish).
11. **Subtree mirror**: `git subtree push --prefix=gateco/packages/sdk-python sdk-python main`.
12. **Tell Elinor** (marketing owns third-party listings: mcpindex, ConnectorZone and the
    rest scrape or pin a version; nothing points them at the new one by itself) and
    record the release in `docs/open_tasks.md`.

Nothing in this file authorises a tag. Who says "tag it" is in `CLAUDE.md`.

# Contributing

Thanks for helping. Bug reports, docs fixes and settings for other institutions are all welcome.

## Ground rules

These protect users' institution accounts and Elsevier's terms, and are not negotiable in a PR:

- **No scraping.** Only the official Elsevier APIs and the free OpenAlex / Semantic Scholar APIs. Never log in to EZproxy or fetch ScienceDirect web pages.
- **No limit bypasses.** Every counted fetch goes through `limits.check` and the minimum gap, one request at a time. Do not raise the UTM defaults; other institutions set their own through `ERM_MAX_*`.
- **No secrets, no papers.** Never commit an API key, insttoken, `.env`, downloaded PDF, full text or cache. Test fixtures must be invented data, not real API responses.
- **Never print a key.** Errors go through `client.redact`; new output that could contain a key needs a test proving it does not.

## Development setup

Needs [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/danialkamarolzaman/elsevier-research-mcp-utm
cd elsevier-research-mcp-utm
uv sync
uv run pytest -q              # mocked, no key or network needed
uv run ruff check .
claude plugin validate .      # if you change the plugin, skills or agent
```

Run the server from your checkout in Claude Code: `claude mcp add elsevier-dev -- uv run --directory <path-to-checkout> elsevier-research-mcp-utm`.

### Live tests

`tests/test_live.py` calls the real API with **your own** key and is skipped unless `ERM_LIVE=1`. It fetches metadata and at most one paper. Never run live tests in CI, on someone else's key, or in a loop.

## Code style

Match the existing code:

- module-level lowercase settings, `os.path`, short `#` comments, no docstrings
- single quotes, line length 110 (ruff enforces both)
- type hints only on the MCP tool functions in `server.py` (they become the tool schema)
- a new tool needs: a function in `server.py`, a row in `docs/tools.md` and the README table, and tests with mocked HTTP (`respx`)

## Pull requests

1. One change per PR; open an issue first for anything large.
2. Add or update tests; `pytest` and `ruff` must pass on Windows and Linux (CI runs both).
3. Add a line under the top section of `CHANGELOG.md`.
4. Fill in the PR checklist.

## Reporting security issues

Do not open a public issue. See [SECURITY.md](SECURITY.md).

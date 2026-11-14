# Changelog

## 0.6.0 (unreleased)

- Automated first-time key setup, two ways:
  - Claude Code plugin settings (`userConfig`): the plugin asks for the API key and insttoken with hidden
    input when it is enabled and keeps them in the system credential store, plus an optional OpenAlex
    email. They reach the server as `ERM_PLUGIN_*`, so an empty field never hides a key already set in
    the environment; unfilled `${user_config...}` placeholders are ignored.
  - `elsevier-research-mcp-utm setup`: opens the Elsevier key page, takes the key with hidden input,
    checks it with one Scopus search (not counted), retries up to 3 times, checks an optional insttoken,
    saves to the config file keeping other lines (created private, `chmod 600`), asks before replacing a
    saved key, warns when an env or plugin value wins, then runs `doctor`. Refuses without a real terminal.
- Key precedence: environment variable, then plugin settings, then config file. `doctor` reports
  `env`, `plugin`, `file` or `none`, and says where to fix a rejected key.
- Docs: `docs/` (setup, tools, access tiers, institutional access with an insttoken request template,
  research workflow, troubleshooting); shorter README.
- `CONTRIBUTING.md`, `SECURITY.md` (private vulnerability reporting), issue and PR templates.

## 0.5.0 (unreleased)

- `research-draft` skill: drafts a document grounded only in retrieved papers. Last 5 years from
  today, most-cited plus recent papers (two searches), two approval pauses, IEEE citations with
  [FT]/[AB] evidence labels, gaps stated instead of filled, references exported.
- `claim-verifier` agent: independent, read-only fact-check of every reference (DOI, title, author,
  year, journal), citation, claim and number against the sources; never downloads anything new.
  The skill reworks every blocking issue and re-verifies, at most 2 rounds, and reports what is left.
- README: full and short research prompts for any MCP client, with the verify-and-rework step.

## 0.4.1 (unreleased)

- Fix: API key not detected when the plugin runs from the Claude desktop app on macOS. The app does not
  pass the shell or launchd environment to plugin MCP servers, so `ELSEVIER_API_KEY` was never seen.
  Settings are now also read from a user config file (`KEY=value` lines, comments and quotes allowed):
  `$XDG_CONFIG_HOME` or `~/.config/elsevier-research-mcp-utm/.env` on macOS / Linux,
  `%APPDATA%\elsevier-research-mcp-utm\.env` on Windows, or `ERM_CONFIG_FILE`. Real environment
  variables still win.
- `check_access` / `doctor` report where the key and insttoken came from (`env`, `file`, `none`) and the
  config file path, never the values. Warns when the file is readable by other users (`chmod 600`).
- README and `elsevier-setup` skill: config-file setup first.

## 0.4.0 (unreleased)

- Claude Code plugin: `.claude-plugin/plugin.json` (MCP server `elsevier`, run with uvx) and
  `.claude-plugin/marketplace.json`, so the repo installs with `/plugin marketplace add`.
- Skills: `elsevier-setup` (first-run check, never asks for keys in chat) and `literature-review`
  (query → screen → verify → fetch within limits → export), with a Scopus query syntax sheet.
- `export_references` tool: BibTeX, RIS and CSV for up to 100 DOIs.

## 0.3.0 (unreleased)

- `get_fulltext` tool: ScienceDirect plain text after an entitlement check, paged from cache.
- `download_pdf` tool: open-access copy first (not counted), else Elsevier PDF if entitled.
  Streams to a `.part` file, refuses or stops when the MB budget would be exceeded, rejects non-PDF
  responses, logs partial transfers. Never downloads the same DOI twice; same-name papers kept apart.
- `download_batch` tool: up to 5 DOIs, sequential, stops at the first limit refusal.
- PDF naming from `ERM_PDF_NAME`, safe for Windows.
- CI: actions/checkout@v5 and astral-sh/setup-uv@v7 (Node 24).

## 0.2.0 (unreleased)

- `get_abstract` tool: Elsevier abstract when entitled, then OpenAlex, then Semantic Scholar, with notes
  explaining any gap. Skips Elsevier for an hour after a not-entitled answer to save quota.
- `find_open_access` tool: open-access status, PDF link, licence and version via OpenAlex.
- DOI clean-up (accepts `doi:` and `https://doi.org/` forms).
- Optional `SEMANTIC_SCHOLAR_API_KEY`; keys for all services hidden in errors.
- `.gitattributes` for consistent line endings.

## 0.1.0 (unreleased)

- Config from environment variables, with UTM Library limits as defaults.
- Shared HTTP client: retry on throttle and server errors, Elsevier error messages explained, keys hidden.
- SQLite cache for responses and a log of full-text fetches.
- Rolling-window download limits (articles and MB per window, per day, minimum gap).
- `doctor` command and `check_access` tool: key, access tier, quota, limit usage.
- `search_scopus` tool.

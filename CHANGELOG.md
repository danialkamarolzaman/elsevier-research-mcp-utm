# Changelog

## 0.9.0

- Closed papers through the user's browser. Tested on campus Wi-Fi in November 2026: the ScienceDirect
  Article API refuses full text at UTM and UTM Library does not issue an insttoken, so closed papers now
  come through the user's own logged-in browser session:
  - `browser_fetch_start` tool: checks the institution limits, waits the minimum gap, counts the paper and
    returns its EZproxy link and file name. `browser_fetch_done` tool: takes the newest PDF from the browser
    downloads folder (or a given path), checks it is a real PDF, files it under a clean name, records its
    size and marks the queue item done. New setting `ERM_BROWSER_DOWNLOADS`.
  - `browser-fetch` skill: Claude in Chrome opens one paper at a time in one tab after the user logs in to
    EZproxy; never types passwords or solves CAPTCHAs; stops at any limit or warning. Safari and other
    browsers: by hand, then `browser_fetch_done`.
- Docs: new `docs/manual-full-text.md` (closed papers through your browser) and `docs/README.md` index;
  README, access tiers, institutional access, tools and troubleshooting updated for UTM.
- `elsevier-setup` skill, `doctor` advice and worker messages point UTM users to the browser way instead of
  an insttoken or campus Wi-Fi.

## 0.8.0 (unreleased)

- Anti-hallucination checks that use no AI judgement:
  - `verify_references` tool: reads the reference list of a `.md`, `.txt`, `.docx` or `.pdf` file (or takes
    DOIs), confirms each DOI exists and that the title, first author and year written match the real record
    (journal advisory only). Entries without a DOI are searched in Scopus by title. Also lists DOIs used in
    the text but missing from the references. A service outage is `LOOKUP_FAILED`, never "fake".
  - `check_quotes` tool: every "quoted" passage in a draft's verification table or a verifier report must
    appear in the cited paper's abstract, cached full text or local PDF (ignores case, spacing,
    punctuation and line-break hyphens; `...` allowed). Never downloads.
  - New dependency `pypdf` to read PDF text locally.
- `verify-sources` skill: fact-check any draft, thesis chapter, pasted text or earlier answer with both tools
  plus the `claim-verifier` agent; writes `<file>-verify.md`, never edits the file.
- `grounded-answers` skill: rules for chat answers (no paper, DOI or number without a tool result in the
  session, [AB]/[FT]/[META] labels, "not found in the retrieved sources", Sources used list).
- `claim-verifier` runs both tools first, adds `FABRICATED_QUOTE`, and must put source words in quotes so
  its own evidence is checked. `research-draft` requires verbatim quotes in the verification table and
  PASS from both tools; `literature-review` adds a "DOI verified" column.

## 0.7.0 (unreleased)

- Background fetch queue: `queue_papers` (up to 200 DOIs) and `queue_status` tools, and an
  `elsevier-research-mcp-utm worker` command the user runs in their own terminal. The worker fetches
  one paper at a time, headless, until the queue is empty: open access first (not counted), then
  Elsevier through the official API when entitled, inside the institution limits (sleeps until the
  next allowed time, stops at the daily cap). Papers with no access wait as `blocked` and are fetched
  automatically when access appears (free re-check every `ERM_RECHECK_MINUTES`, default 30); other
  paywalled papers become `manual`. Both are listed in `_open_manually.md` with EZproxy links for the
  user to open by hand; PDFs saved there are picked up. It never automates EZproxy or ScienceDirect
  web pages. Only one worker at a time; network errors retried 3 times.
- One-at-a-time lock across processes, so the worker and the MCP tools never fetch at the same time.
- `research-draft` and `literature-review` skills queue the chosen papers and use the PDFs that arrive.

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
- Security: `export_references` no longer overwrites existing files. A `path` from the assistant
  (possibly steered by text inside a paper) could replace any file the user can write, e.g. a shell
  profile. The format's extension is now forced and an existing name gets ` (2)`, ` (3)`, ...

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

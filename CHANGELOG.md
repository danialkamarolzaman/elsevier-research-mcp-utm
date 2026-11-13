# Changelog

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

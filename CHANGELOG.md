# Changelog

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

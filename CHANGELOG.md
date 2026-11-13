# Changelog

## 0.1.0 (unreleased)

- Config from environment variables, with UTM Library limits as defaults.
- Shared HTTP client: retry on throttle and server errors, Elsevier error messages explained, keys hidden.
- SQLite cache for responses and a log of full-text fetches.
- Rolling-window download limits (articles and MB per window, per day, minimum gap).
- `doctor` command and `check_access` tool: key, access tier, quota, limit usage.
- `search_scopus` tool.

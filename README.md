# elsevier-research-mcp-utm

An MCP server (and, from v1.0, a Claude Code plugin) for searching Scopus and fetching ScienceDirect papers through the official Elsevier APIs, with **institution download limits built in**. The defaults follow the UTM Library e-resource rules.

> **Unofficial.** Not affiliated with or endorsed by Elsevier or Universiti Teknologi Malaysia. Content you fetch is governed by Elsevier's terms and your institution's licence: do not share or redistribute it.

**Status: 0.2 (early).** Full text, PDFs and export arrive in 0.3–0.4.

## Tools

| Tool | What it does | Counts toward limits |
|---|---|---|
| `check_access` | key valid?, access tier, Elsevier quota, limit usage | no |
| `search_scopus` | Scopus advanced search, sorted by citations, date or relevance | no |
| `get_abstract` | abstract + metadata for a DOI: Elsevier (if entitled) → OpenAlex → Semantic Scholar | no |
| `find_open_access` | free legal copy (PDF link, licence, version) via OpenAlex | no |

**About abstracts off-campus:** Elsevier withholds its own abstracts from OpenAlex and Semantic Scholar. Off-campus without an insttoken, most Elsevier papers therefore come back with full metadata but no abstract; the result says so and gives an EZproxy link. Open-access and most non-Elsevier papers do get abstracts.

## Why the limits matter

UTM Library warns that the following can get your UTM ID suspended:

- opening multiple tabs at the same time
- downloading more than 5 articles at once
- downloading more than 100 MB in 15 minutes

Every full-text or PDF fetch is logged locally. The tool refuses a fetch that would break a limit and tells you when the next one is allowed. Searches and metadata do not count.

| Setting | Default |
|---|---|
| `ERM_MAX_ARTICLES_PER_WINDOW` | 5 |
| `ERM_MAX_MB_PER_WINDOW` | 100 |
| `ERM_WINDOW_MINUTES` | 15 |
| `ERM_MAX_ARTICLES_PER_DAY` | 20 |
| `ERM_MIN_DELAY_SECONDS` | 10 |

Users at other institutions should set these to match their own library's rules.

## Access tiers

| Tier | What you get | How |
|---|---|---|
| metadata | titles, authors, DOI, PII, citations | any network, API key only |
| abstracts | + Elsevier abstracts (others come from free sources at every tier) | subscribed network or insttoken |
| fulltext | + ScienceDirect full text | subscribed network (campus Wi-Fi) or insttoken |

The tool is **headless only through the API**. It never scrapes ScienceDirect or logs in to EZproxy. Each paper includes a `proxy_url` (EZproxy link) that you can open yourself in a browser.

## Setup

1. Get an API key at <https://dev.elsevier.com> and set it as an environment variable:
   - Windows (PowerShell): `[Environment]::SetEnvironmentVariable('ELSEVIER_API_KEY', '<key>', 'User')`
   - macOS / Linux: add `export ELSEVIER_API_KEY=<key>` to your shell profile
2. Optional: ask your library for an Elsevier **insttoken** and set `ELSEVIER_INSTTOKEN`. UTM: libsupport@utm.my.
3. Install [uv](https://docs.astral.sh/uv/), then check your setup:

   ```
   uvx --from git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm elsevier-research-mcp-utm doctor
   ```

4. Add it to Claude Code:

   ```
   claude mcp add elsevier -- uvx --from git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm elsevier-research-mcp-utm
   ```

All settings are listed in [`.env.example`](.env.example).

## Development

```
uv sync
uv run pytest -q          # mocked tests, no key needed
uv run ruff check .
ERM_LIVE=1 uv run pytest tests/test_live.py   # real API, uses your key
```

## License

MIT for the code. See [LICENSE](LICENSE).

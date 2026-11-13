# elsevier-research-mcp-utm

A Claude Code plugin and MCP server for searching Scopus and fetching ScienceDirect papers through the official Elsevier APIs, with **institution download limits built in**. The defaults follow the UTM Library e-resource rules.

> **Unofficial.** Not affiliated with or endorsed by Elsevier or Universiti Teknologi Malaysia. Content you fetch is governed by Elsevier's terms and your institution's licence: do not share or redistribute it.

**Status: 0.4 (early).**

## Install in Claude Code

Needs [uv](https://docs.astral.sh/uv/) and an Elsevier API key in `ELSEVIER_API_KEY` (see [Setup](#setup)).

```
/plugin marketplace add danialkamarolzaman/elsevier-research-mcp-utm
/plugin install elsevier-research-mcp-utm@elsevier-research-mcp-utm
```

Restart Claude Code, then ask: *"check my Elsevier access"*. The plugin adds the MCP server (`elsevier`) and two skills: `elsevier-setup` (first-run check) and `literature-review` (search → screen → fetch → export, within the limits).

## Tools

| Tool | What it does | Counts toward limits |
|---|---|---|
| `check_access` | key valid?, access tier, Elsevier quota, limit usage | no |
| `search_scopus` | Scopus advanced search, sorted by citations, date or relevance | no |
| `get_abstract` | abstract + metadata for a DOI: Elsevier (if entitled) → OpenAlex → Semantic Scholar | no |
| `find_open_access` | free legal copy (PDF link, licence, version) via OpenAlex | no |
| `get_fulltext` | ScienceDirect full text as plain text, paged; re-reading is free from cache | **yes** |
| `download_pdf` | one PDF: open-access copy first (not counted), else Elsevier if entitled | **yes** (Elsevier only) |
| `download_batch` | up to 5 PDFs one after another; stops at the first limit refusal | **yes** (Elsevier only) |
| `export_references` | BibTeX, RIS (EndNote / Zotero / Mendeley) or CSV for up to 100 DOIs | no |

Before any counted fetch the tool checks entitlement (free). With no access nothing is downloaded and nothing is counted. PDFs are named `{first_author} {year} - {title}.pdf` (`ERM_PDF_NAME`), saved in `ERM_DOWNLOAD_DIR`, and never downloaded twice; two different papers with the same name are both kept (the second gets its DOI appended).

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

4. Add it to Claude Code as a plugin (above), or as a plain MCP server for any MCP client:

   ```
   claude mcp add elsevier -- uvx --from git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm elsevier-research-mcp-utm
   ```

   Other clients (Claude Desktop, Cursor, VS Code) use the same command: `uvx` with args `--from`, `git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm`, `elsevier-research-mcp-utm`.

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

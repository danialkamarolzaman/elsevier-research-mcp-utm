# Tools

The MCP server is called `elsevier`. Every tool returns JSON. Errors come back as a readable message with what to do next, never with your key in it.

| Tool | Counts toward download limits |
|---|---|
| [`check_access`](#check_access) | no |
| [`search_scopus`](#search_scopus) | no |
| [`get_abstract`](#get_abstract) | no |
| [`find_open_access`](#find_open_access) | no |
| [`get_fulltext`](#get_fulltext) | **yes** (first read of each paper) |
| [`download_pdf`](#download_pdf) | **yes** (Elsevier copies only) |
| [`download_batch`](#download_batch) | **yes** (Elsevier copies only) |
| [`export_references`](#export_references) | no |

## check_access

Is the key set and valid, where it came from, the access tier on this network, Elsevier quota left, current limit usage, advice. Optional `doi` checks entitlement for one specific paper (free, nothing downloaded).

## search_scopus

Scopus advanced search.

| Input | Default | Notes |
|---|---|---|
| `query` | | Scopus syntax, e.g. `TITLE-ABS-KEY("knowledge graph" AND maintenance)` |
| `year_from`, `year_to` | none | inclusive |
| `sort` | `citations` | `citations`, `date` or `relevance` |
| `count` | 25 | 1-25 per page |
| `start` | 0 | next page: `start=25` |

Returns total hits and papers with DOI, PII, title, authors, year, journal, citations, open-access flag and an EZproxy link (`proxy_url`) you can open yourself. Results are cached for `ERM_CACHE_DAYS`.

## get_abstract

Abstract and metadata for a DOI. Tries Elsevier (if your network or insttoken is entitled), then OpenAlex, then Semantic Scholar, and says which one answered (`abstract_source`). Elsevier withholds its own abstracts from the free sources, so off-campus many Elsevier papers come back without one; the result says so.

## find_open_access

A free, legal copy of a paper via OpenAlex: PDF link, licence, version (published / accepted / submitted). Nothing is downloaded.

## get_fulltext

ScienceDirect full text as plain text, in pages (`start`, `max_chars`). Checks entitlement first (free); with no access nothing is fetched or counted. The first read counts as one article; reading further pages, or re-reading later, comes from the cache and is free.

## download_pdf

One PDF into `ERM_DOWNLOAD_DIR`, named `{first_author} {year} - {title}.pdf` (`ERM_PDF_NAME`, or pass `filename`).

1. Already downloaded? Returns the path, nothing fetched.
2. Open-access copy available? Downloads it (not counted).
3. Otherwise Elsevier, if entitled and within limits (counted). The size is checked against the MB budget while downloading, and a file that is not a real PDF is rejected.

Two different papers with the same name are both kept; the second gets its DOI appended.

## download_batch

Up to 5 DOIs (`ERM_MAX_ARTICLES_PER_WINDOW`), one after another, with the minimum gap between them. Stops at the first limit refusal and lists what was not attempted and when to try again. Never runs in parallel (one tab, one download at a time).

## export_references

Up to 100 DOIs to `bibtex`, `ris` (EndNote / Zotero / Mendeley) or `csv`. Metadata comes from the same sources as `get_abstract` (cached, never counted). Optional `path`; default `ERM_DOWNLOAD_DIR/references_<time>.<ext>`.

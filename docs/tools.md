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
| [`queue_papers`](#queue_papers) | the worker's institutional fetches do |
| [`queue_status`](#queue_status) | no |
| [`verify_references`](#verify_references) | no |
| [`check_quotes`](#check_quotes) | no |

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

Up to 100 DOIs to `bibtex`, `ris` (EndNote / Zotero / Mendeley) or `csv`. Metadata comes from the same sources as `get_abstract` (cached, never counted). Optional `path`; default `ERM_DOWNLOAD_DIR/references_<time>.<ext>`. It never overwrites a file: the format's extension is added if missing, and an existing name gets ` (2)`, ` (3)`, ...

## queue_papers

Adds up to 200 DOIs to the fetch queue (kept in the cache database, so nothing is lost on restart). Queueing fetches nothing. A paper that failed before is re-queued; done papers are not fetched again. Returns `start_worker`, the command to run in your own terminal when no worker is running.

### The worker

`elsevier-research-mcp-utm worker` works through the queue:

1. one paper at a time, in the order queued, with `ERM_MIN_DELAY_SECONDS` between institutional fetches;
2. open-access copy first (not counted); otherwise Elsevier through the official API if entitled (counted);
3. on a limit it sleeps until the next allowed time; at the daily cap it sleeps until tomorrow;
4. papers with no access on this network become `blocked`; every `ERM_RECHECK_MINUTES` (30) it makes one free entitlement check, and when access appears (campus Wi-Fi, insttoken) it fetches them;
5. papers from other publishers that are not open access become `manual`;
6. `blocked` and `manual` papers are listed in `_open_manually.md` in the download folder, with EZproxy links and the file name to save under. PDFs you save there are picked up automatically;
7. network errors are retried after a minute, up to 3 times, then marked `failed`.

Only one worker runs at a time, and a cross-process lock makes the worker and the MCP tools take turns, so two institutional fetches never run at once. The worker saves into the download folder that was active when the papers were queued, unless `ERM_DOWNLOAD_DIR` is set. Ctrl+C stops it; start it again any time.

It never logs in to EZproxy, never loads ScienceDirect web pages and never opens browser tabs: publishers' terms forbid automated downloading through the website, and doing it with your library login risks your institution account.

## browser_fetch_start / browser_fetch_done

For closed papers the API cannot fetch (always at UTM), through the user's own logged-in browser. The `browser-fetch` skill drives them with Claude in Chrome; see [closed papers through your browser](manual-full-text.md).

- `browser_fetch_start(doi)`: refuses when a limit is reached (`next_allowed`); otherwise waits the minimum gap, counts the paper toward the limits and returns `open_url` (EZproxy link), `save_as` and `downloads_dir`. Calling it again within 30 minutes for the same paper does not count twice.
- `browser_fetch_done(doi, path=None, wait_seconds=60)`: takes `path`, or the newest PDF that appeared in the browser downloads folder since the start (waiting for the download to finish). Refuses a file that is not a real PDF (`NOT_PDF`, e.g. a login page). Moves it into the download folder under a clean name, records its size and marks the queue item done.

The browser downloads folder is `~/Downloads`; set `ERM_BROWSER_DOWNLOADS` if yours is elsewhere. Neither tool logs in, loads web pages or reads cookies: the user logs in, in their own browser.

## queue_status

Counts per status, each paper with its PDF path when done, whether the worker is running, when the next institutional fetch is allowed, and the path of `_open_manually.md`. Free.

## verify_references

Exact check of a reference list, with no AI judgement: plain lookups and string comparison.

| Input | Notes |
|---|---|
| `path` | a `.md`, `.txt`, `.docx` or `.pdf` file with a "References" (or "Bibliography") heading |
| `dois` | instead of a file: a list of DOIs to confirm and get real metadata for |

For each entry it looks up the DOI (Elsevier when entitled, OpenAlex, Semantic Scholar) and compares the title, first author and year written in the entry with the real record. The journal is compared too, but only as advice, because IEEE style abbreviates journal names. Entries with no DOI are searched in Scopus by their quoted title.

| Status | Meaning |
|---|---|
| `OK` | the DOI exists and the entry matches it |
| `MISMATCH` | title, first author or year differ: `problems` gives the correct values (blocking) |
| `NOT_FOUND` | no record for the DOI: fake, mistyped or very new (blocking) |
| `NO_DOI` | no DOI; `suggested_doi` when Scopus found the title |
| `LOOKUP_FAILED` | a service did not answer; not evidence of anything |

It also lists DOIs that appear in the text but not in the reference list.

## check_quotes

Exact check that quoted evidence is real. Give the `path` of a Markdown draft or verify report. In every table with a *quote* or *evidence* column and a *citation* / *cites* column, each text inside "double quotes" is looked for in the cited paper: its abstract, its full text already in the cache, and its PDF (from `pdf:<path>` in the Sources table, or one downloaded earlier). Case, spacing, punctuation, ligatures and line-break hyphens are ignored; `...` splits a quote into parts that must appear in order. Citation numbers are mapped to DOIs through the Sources table or the reference list.

| Status | Meaning |
|---|---|
| `FOUND` | the words are in the source (`in` says which text) |
| `NOT_FOUND` | not in any text of the cited paper: fabricated or paraphrased (blocking); `best_prefix_match` shows how much of the start matched |
| `NO_SOURCE` | the citation number has no DOI in the file (blocking) |
| `SOURCE_UNAVAILABLE` | no abstract, cached full text or PDF to check against |
| `TOO_SHORT`, `NOT_A_QUOTE` | too short to prove anything, or no quoted text in the cell |

It never downloads anything; PDFs are read locally with `pypdf`.

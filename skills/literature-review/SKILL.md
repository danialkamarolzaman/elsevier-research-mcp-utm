---
name: literature-review
description: Run a literature search and collection with the elsevier-research-mcp-utm tools - build Scopus queries, screen results by abstract, verify DOIs, fetch open-access and institutional full text within library download limits, and export references. Use when the user asks to find papers, do a literature review, search Scopus, collect references on a topic, download papers, or build a reference list or BibTeX file.
---

# Literature review with Scopus

## Rules that protect the user's institution account

- Full text and Elsevier PDFs count toward the library limits (UTM: 5 articles and 100 MB per 15 minutes, 20 per day). **When a tool refuses with a limit reason, tell the user the `next_allowed` time and stop. Never retry in a loop, never work around the limit.**
- Always try `find_open_access` / `download_pdf` (open access first) before institutional access.
- Use `download_batch` with at most 5 DOIs, only after the user agreed on which papers.
- Never scrape ScienceDirect or log in to EZproxy for the user. For papers without access, give the `proxy_url` for the user to open themselves, one at a time.
- Do not share or paste whole full texts back to other services; they are licensed to the user.

## Workflow

1. **Agree the scope** with the user: topic, synonyms, year range, document types, minimum citation count, how many papers.
2. **Build the query.** Use Scopus syntax (see `references/scopus-query-syntax.md`). Start broad with `TITLE-ABS-KEY(...)`, combine synonym groups with `OR` inside brackets and concepts with `AND`. Show the query to the user before running it.
3. **Search.** `search_scopus` with `year_from` / `year_to`, `sort='citations'` (or `date` for recent work). Report `total`. If total is huge, narrow (add a concept, `DOCTYPE(ar OR re)`, `LANGUAGE(english)`); if tiny, widen synonyms. Page with `start` (25 per page).
4. **Screen.** Present a compact table: year, first author, title, journal, citations, open access. For candidates, call `get_abstract` and judge relevance on the abstract. If no abstract is available (common for Elsevier papers off-campus), say so and judge on title/keywords, marking it as unverified.
5. **Verify before citing.** Only cite papers whose DOI came back from a tool call. Never invent or "fix" a DOI, author or year from memory.
6. **Get the papers.** For each chosen DOI: `find_open_access` first. Then `download_pdf` (tries open access, then Elsevier if entitled). For several papers use `download_batch` with at most 5 DOIs, then report what was saved, what was refused and why. For many papers (more than 5, or "fetch all of them"), use `queue_papers` instead and give the user the `start_worker` command to run in their own terminal; the worker fetches everything it legally can in the background within the limits and lists the rest (EZproxy links) for the user to open by hand. Check progress with `queue_status`. Never try to automate EZproxy or ScienceDirect web pages.
7. **Read.** `get_fulltext` returns pages; continue with `start = end` of the previous call. Re-reading is free (cached).
8. **Export.** `export_references` with `bibtex` (LaTeX), `ris` (EndNote, Zotero, Mendeley) or `csv` (Excel, includes abstracts). Report the file path and any `missing_metadata`.

## Output style

- Keep paper lists as tables, newest or most cited first, as the user asked.
- Say which source each abstract came from (`abstract_source`) when it matters.
- At the end: papers found, screened, downloaded (open access vs institutional), refused, and the export path.

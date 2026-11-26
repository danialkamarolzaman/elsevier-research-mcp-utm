from typing import Literal

from mcp.server.mcpserver import MCPServer

from . import (
    __version__,
    abstracts,
    browserfetch,
    client,
    config,
    doctor,
    export,
    fetch,
    fetchqueue,
    verify,
    worker,
)
from .sources import scopus

mcp = MCPServer(
    'elsevier-research-mcp-utm',
    version=__version__,
    instructions=(
        'Elsevier Scopus / ScienceDirect tools. Run check_access first. Searches and metadata are free; '
        'full text and PDFs are limited by institution rules (UTM: max 5 articles and 100 MB per 15 min).'),
)


def _error(e):
    return {'error': str(e), 'status': getattr(e, 'status', None), 'code': getattr(e, 'code', None)}


# type hints on tool functions are required: MCP builds each tool's input schema from them

@mcp.tool(description=(
    'Check the Elsevier setup: whether the API key works, the access tier on this network '
    '(metadata, abstracts or fulltext), remaining Elsevier quota and the institution download-limit usage. '
    'Optionally checks full-text access for one DOI. Never downloads anything. Run this first.'))
def check_access(doi: str | None = None) -> dict:
    try:
        return doctor.run(doi)
    except client.ApiError as e:
        return _error(e)


@mcp.tool(description=(
    'Search Scopus with its advanced query syntax, e.g. TITLE-ABS-KEY("remaining useful life") AND '
    'PUBYEAR > 2020. Returns papers with DOI, PII, journal, year, citation count, open-access flag and an '
    'EZproxy link. Abstracts are not included (use get_abstract). count is 1-25 per page; page with start.'))
def search_scopus(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    sort: Literal['citations', 'date', 'relevance'] = 'citations',
    count: int = 25,
    start: int = 0,
) -> dict:
    try:
        return scopus.search(query, year_from, year_to, sort, count, start)
    except client.ApiError as e:
        return _error(e)


@mcp.tool(description=(
    'Get the abstract and full metadata for one DOI. Tries Elsevier (only when entitled: campus network '
    'or insttoken), then OpenAlex, then Semantic Scholar; abstract_source says which one answered. '
    'Elsevier withholds its own abstracts from the free sources, so off-campus many Elsevier papers come '
    'back without an abstract: the notes explain why and proxy_url opens the paper via EZproxy. '
    'Does not count toward download limits.'))
def get_abstract(doi: str) -> dict:
    try:
        return abstracts.get_abstract(doi)
    except (client.ApiError, ValueError) as e:
        return _error(e)


@mcp.tool(description=(
    'Find a free, legal open-access copy of a paper by DOI (via OpenAlex): open-access status, PDF link, '
    'landing page, licence and version (published or accepted manuscript). Use this before institutional '
    'access. Does not count toward download limits.'))
def find_open_access(doi: str) -> dict:
    try:
        return abstracts.find_open_access(doi)
    except (client.ApiError, ValueError) as e:
        return _error(e)


limit_note = ('COUNTS toward institution download limits (UTM default: 5 articles and 100 MB per 15 min, '
              '20 per day, 10 s apart). When refused, the result gives the reason and next_allowed time: '
              'tell the user and wait, never retry in a loop.')


@mcp.tool(description=(
    'Get the full text of a ScienceDirect article as plain text, by DOI or PII. Needs institutional access '
    '(campus network or insttoken); access is checked first and nothing is fetched without it. '
    'Long texts are paged: read more with start=end of the previous call (re-reading is free, from cache). '
    + limit_note))
def get_fulltext(
    doi: str | None = None, pii: str | None = None, start: int = 0, max_chars: int = 40000,
) -> dict:
    try:
        return fetch.get_fulltext(doi, pii, start, max_chars)
    except (client.ApiError, ValueError) as e:
        return _error(e)


@mcp.tool(description=(
    'Download one paper as a PDF into the download folder (ERM_DOWNLOAD_DIR), named '
    '"{first_author} {year} - {title}.pdf" unless filename is given. With prefer_open_access (default) a '
    'free legal copy is tried first and does not count toward limits; otherwise the Elsevier PDF is fetched '
    'if entitled. Existing files are not downloaded again. ' + limit_note))
def download_pdf(doi: str, filename: str | None = None, prefer_open_access: bool = True) -> dict:
    try:
        return fetch.download_pdf(doi, filename, prefer_open_access)
    except (client.ApiError, ValueError) as e:
        return _error(e)


@mcp.tool(description=(
    'Download up to 5 papers as PDFs, one after another, then stop. Stops early at the first limit refusal '
    'and lists DOIs not attempted; never continues in the background. Use for small batches after '
    'checking find_open_access. For many papers use queue_papers instead. ' + limit_note))
def download_batch(dois: list[str], prefer_open_access: bool = True) -> dict:
    try:
        return fetch.download_batch(dois, prefer_open_access)
    except (client.ApiError, ValueError) as e:
        return _error(e)


@mcp.tool(description=(
    'Write a reference file for a list of DOIs (up to 100): bibtex (.bib), ris (.ris, for EndNote, Zotero, '
    'Mendeley) or csv (.csv, opens in Excel, includes abstracts where known). Metadata comes from the same '
    'cached lookup as get_abstract. Default path: the download folder, timestamped. Never overwrites a file: '
    'the format extension is added if missing, and an existing name gets " (2)", " (3)", ... '
    'Does not count toward download limits.'))
def export_references(
    dois: list[str], format: Literal['bibtex', 'ris', 'csv'] = 'bibtex', path: str | None = None,
) -> dict:
    try:
        return export.export_references(dois, format, path)
    except (client.ApiError, ValueError, OSError) as e:
        return _error(e)


@mcp.tool(description=(
    'Queue papers (up to 200 DOIs) for the background worker, which fetches them headless one at a time '
    'until all are done: open-access copies first (not counted), then Elsevier through the official API '
    'when this network or an insttoken is entitled, always inside the institution limits (it sleeps until '
    'the next allowed time, stops for the day at the daily cap, and starts again by itself when access '
    'appears, e.g. on campus Wi-Fi). It never logs in to EZproxy: papers it cannot get go to a list the user '
    'fetches with browser_fetch_start/done through their logged-in browser or '
    'opens by hand. The worker is a separate program the USER starts in their own terminal; tell them the '
    'command in "start_worker" if worker_running is false. Queueing itself fetches nothing.'))
def queue_papers(dois: list[str]) -> dict:
    try:
        result = fetchqueue.add(dois)
    except ValueError as e:
        return _error(e)
    running = fetchqueue.worker_active()
    return {**result, 'worker_running': running, 'download_dir': config.download_dir,
            'start_worker': None if running else worker.start_command}


@mcp.tool(description=(
    'Browser-assisted fetch of a closed (paywalled) paper, step 1 of 2. Use it when the API has no full-text '
    'access (always at UTM) and the USER is logged in to EZproxy in their own browser. Checks the '
    'institution limits, waits the minimum gap, counts the paper, and returns open_url (the EZproxy link) '
    'and save_as. '
    'Then open open_url in ONE browser tab (e.g. Claude in Chrome), download the PDF, and call '
    'browser_fetch_done. Refused with next_allowed when a limit is reached: stop and tell the user. Never '
    'type the user\'s password or solve a CAPTCHA; the user logs in. Follow the browser-fetch skill.'))
def browser_fetch_start(doi: str) -> dict:
    try:
        return browserfetch.start(doi)
    except (client.ApiError, ValueError) as e:
        return _error(e)


@mcp.tool(description=(
    'Browser-assisted fetch, step 2 of 2: after the PDF was downloaded in the browser, finds the newest PDF '
    'in the browser downloads folder (waits up to wait_seconds for the download to finish), or takes path, '
    'checks it is a real PDF, moves it into the download folder under the save_as name, records its size '
    'toward the limits and marks the paper done in the queue. The verify tools can then read it.'))
def browser_fetch_done(doi: str, path: str | None = None, wait_seconds: int = 60) -> dict:
    try:
        return browserfetch.finish(doi, path, min(max(int(wait_seconds), 0), 300))
    except (client.ApiError, ValueError, OSError) as e:
        return _error(e)


@mcp.tool(description=(
    'Anti-hallucination check of a reference list, by plain lookup (no AI judgement). With path (.md, .txt, '
    '.docx or .pdf): finds the References section, and for each entry looks its DOI up (Elsevier, OpenAlex) '
    'and compares the title, first author, year and journal written there with the real record. Entries '
    'without a DOI are searched in Scopus by their quoted title. With dois: just confirms each DOI exists '
    'and returns its real metadata. Status per reference: OK, MISMATCH (correct values given), NOT_FOUND '
    '(likely fake or mistyped), NO_DOI, LOOKUP_FAILED. Free: never fetches full text.'))
def verify_references(path: str | None = None, dois: list[str] | None = None) -> dict:
    try:
        return verify.verify_references(path, dois)
    except (client.ApiError, ValueError, OSError) as e:
        return _error(e)


@mcp.tool(description=(
    'Anti-hallucination check of quotes, by exact text matching (no AI judgement). Reads a Markdown draft '
    'or verifier report, takes every "double-quoted" text in a table column named quote or evidence, maps '
    'the row citation [n] to a DOI via the Sources table or reference list, and checks the quote really '
    'appears in that paper: its abstract, its cached ScienceDirect full text or its local PDF. Ignores '
    'case, spacing, punctuation and line-break hyphens. Status per quote: FOUND, NOT_FOUND (fabricated or '
    'paraphrased), SOURCE_UNAVAILABLE, NO_SOURCE, TOO_SHORT, NOT_A_QUOTE. Free: never downloads anything.'))
def check_quotes(path: str) -> dict:
    try:
        return verify.check_quotes(path)
    except (client.ApiError, ValueError, OSError) as e:
        return _error(e)


@mcp.tool(description=(
    'Progress of the background fetch queue: counts (waiting, done, blocked = needs campus Wi-Fi or an '
    'insttoken, manual = open it yourself, failed), each paper with its PDF path when done, whether the '
    'worker is running, the next allowed institutional fetch, and the path of the list of papers to open by '
    'hand. Free: fetches nothing.'))
def queue_status() -> dict:
    result = fetchqueue.status()
    if not result['worker_running'] and result['counts']['waiting']:
        result['start_worker'] = worker.start_command
    return result

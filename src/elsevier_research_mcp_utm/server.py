from typing import Literal

from mcp.server.mcpserver import MCPServer

from . import __version__, abstracts, client, doctor, export, fetch
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
    'checking find_open_access. ' + limit_note))
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

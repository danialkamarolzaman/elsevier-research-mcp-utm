from typing import Literal

from mcp.server.mcpserver import MCPServer

from . import __version__, client, doctor
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

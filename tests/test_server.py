import asyncio

from elsevier_research_mcp_utm.server import mcp


def test_tools_registered_with_schema():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    assert set(tools) == {'check_access', 'search_scopus', 'get_abstract', 'find_open_access'}
    assert tools['get_abstract'].input_schema['required'] == ['doi']
    schema = tools['search_scopus'].input_schema
    props = schema['properties']
    assert schema['required'] == ['query']
    assert set(props['sort']['enum']) == {'citations', 'date', 'relevance'}

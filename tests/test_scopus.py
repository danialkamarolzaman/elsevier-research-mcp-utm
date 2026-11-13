import httpx
import pytest
import respx

from conftest import load_fixture
from elsevier_research_mcp_utm import config, models
from elsevier_research_mcp_utm.sources import scopus

url = 'https://api.elsevier.com/content/search/scopus'


@respx.mock
def test_search_parses_papers():
    respx.get(url).mock(return_value=httpx.Response(200, json=load_fixture('scopus_search.json')))
    res = scopus.search('TITLE(maintenance)')
    assert res['total'] == 137 and res['count'] == 2 and not res['cached']
    p = res['papers'][0]
    assert p['doi'] == '10.9999/example.2024.001'
    assert p['scopus_id'] == '11111111111'
    assert p['year'] == 2024 and p['cited_by'] == 42 and p['open_access'] is False
    assert p['proxy_url'].startswith('https://ezproxy.utm.my/login?url=https://www.sciencedirect.com/')
    assert res['papers'][1]['pii'] is None
    assert 'doi.org' in res['papers'][1]['proxy_url']


@respx.mock
def test_search_params():
    route = respx.get(url).mock(return_value=httpx.Response(200, json=load_fixture('scopus_search.json')))
    scopus.search('q', year_from=2021, year_to=2026, sort='date', count=99, start=-3)
    params = route.calls[0].request.url.params
    assert params['date'] == '2021-2026'
    assert params['sort'] == '-coverDate'
    assert params['count'] == '25' and params['start'] == '0'
    assert 'pii' in params['field']


@respx.mock
def test_empty_result():
    respx.get(url).mock(return_value=httpx.Response(200, json=load_fixture('scopus_empty.json')))
    res = scopus.search('nothing')
    assert res['total'] == 0 and res['papers'] == []


@respx.mock
def test_second_call_uses_cache():
    route = respx.get(url).mock(return_value=httpx.Response(200, json=load_fixture('scopus_search.json')))
    scopus.search('same')
    res = scopus.search('same')
    assert route.call_count == 1 and res['cached']


def test_bad_sort():
    with pytest.raises(ValueError):
        scopus.search('q', sort='popular')


def test_proxy_off(monkeypatch):
    monkeypatch.setattr(config, 'proxy_host', '')
    assert models.proxy_url(doi='10.1/x') is None

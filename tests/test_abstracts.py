import re

import httpx
import respx

from conftest import load_fixture
from elsevier_research_mcp_utm import abstracts, models

els = re.compile(r'https://api\.elsevier\.com/content/abstract/doi/.*')
oa = re.compile(r'https://api\.openalex\.org/works/.*')
s2 = re.compile(r'https://api\.semanticscholar\.org/.*')


def els_error(status, code):
    return httpx.Response(status, json={'service-error': {'status': {'statusCode': code, 'statusText': 'x'}}})


def test_clean_doi():
    assert models.clean_doi('https://doi.org/10.1016/J.RESS.2022.109068') == '10.1016/j.ress.2022.109068'
    assert models.clean_doi('doi: 10.1/X ') == '10.1/x'
    assert models.clean_doi('') is None


def test_inverted_index():
    assert models.abstract_from_inverted({'b': [1], 'a': [0, 2]}) == 'a b a'
    assert models.abstract_from_inverted(None) is None


@respx.mock
def test_elsevier_abstract_when_entitled():
    respx.get(url__regex=els).mock(return_value=httpx.Response(200, json={
        'abstracts-retrieval-response': {'coredata': {
            'prism:doi': '10.9999/closed.2022.020', 'dc:title': 'T', 'pii': 'S1',
            'dc:creator': {'author': [{'ce:indexed-name': 'X'}]},
            'dc:description': '  An Elsevier abstract.  '}}}))
    respx.get(url__regex=oa).mock(return_value=httpx.Response(200, json=load_fixture('openalex_closed.json')))
    s2_route = respx.get(url__regex=s2)
    r = abstracts.get_abstract('10.9999/closed.2022.020')
    p = r['paper']
    assert p['abstract'] == 'An Elsevier abstract.' and p['abstract_source'] == 'elsevier'
    assert p['first_author'] == 'Closed Author'  # nested creator ignored, filled from openalex
    assert p['proxy_url'].endswith('/pii/S1')
    assert not s2_route.called


@respx.mock
def test_openalex_fallback_off_campus():
    route = respx.get(url__regex=els).mock(return_value=els_error(401, 'AUTHORIZATION_ERROR'))
    respx.get(url__regex=oa).mock(return_value=httpx.Response(200, json=load_fixture('openalex_oa.json')))
    r = abstracts.get_abstract('10.9999/open.2023.010')
    p = r['paper']
    assert p['abstract'] == 'Knowledge graphs help maintenance.' and p['abstract_source'] == 'openalex'
    assert p['authors'] == ['Example Author', 'Second Person'] and p['pages'] == '15-29'
    assert any('not entitled' in n for n in r['notes'])
    # second DOI: elsevier skipped for an hour after a not-entitled answer
    abstracts.get_abstract('10.9999/other')
    assert route.call_count == 1


@respx.mock
def test_semantic_scholar_fallback():
    respx.get(url__regex=els).mock(return_value=els_error(403, 'AUTHENTICATION_ERROR'))
    respx.get(url__regex=oa).mock(return_value=httpx.Response(200, json=load_fixture('openalex_closed.json')))
    respx.get(url__regex=s2).mock(return_value=httpx.Response(200, json={'abstract': 'From S2.'}))
    p = abstracts.get_abstract('10.9999/closed.2022.020')['paper']
    assert p['abstract'] == 'From S2.' and p['abstract_source'] == 'semanticscholar'
    assert p['cited_by'] == 168


@respx.mock
def test_no_abstract_anywhere_explains_why():
    respx.get(url__regex=els).mock(return_value=els_error(401, 'AUTHORIZATION_ERROR'))
    respx.get(url__regex=oa).mock(return_value=httpx.Response(200, json=load_fixture('openalex_closed.json')))
    respx.get(url__regex=s2).mock(return_value=httpx.Response(200, json={'abstract': None}))
    r = abstracts.get_abstract('10.9999/closed.2022.020')
    assert r['paper']['abstract'] is None
    assert any('withholds' in n for n in r['notes'])
    assert r['paper']['proxy_url'].startswith('https://ezproxy.utm.my/login?url=https://doi.org/')


@respx.mock
def test_results_are_cached():
    respx.get(url__regex=els).mock(return_value=els_error(401, 'AUTHORIZATION_ERROR'))
    oa_route = respx.get(url__regex=oa).mock(
        return_value=httpx.Response(200, json=load_fixture('openalex_oa.json')))
    abstracts.get_abstract('10.9999/open.2023.010')
    r = abstracts.get_abstract('10.9999/open.2023.010')
    assert r['cached'] and oa_route.call_count == 1


@respx.mock
def test_unknown_doi():
    respx.get(url__regex=els).mock(return_value=els_error(404, 'RESOURCE_NOT_FOUND'))
    respx.get(url__regex=oa).mock(return_value=httpx.Response(404))
    respx.get(url__regex=s2).mock(return_value=httpx.Response(404))
    r = abstracts.get_abstract('10.9999/missing')
    assert r['paper']['title'] is None
    assert 'openalex: DOI not found' in r['notes']


@respx.mock
def test_find_open_access():
    respx.get(url__regex=oa).mock(return_value=httpx.Response(200, json=load_fixture('openalex_oa.json')))
    r = abstracts.find_open_access('https://doi.org/10.9999/open.2023.010')
    assert r['is_oa'] and r['oa_status'] == 'gold'
    assert r['pdf_url'] == 'https://example.org/paper.pdf' and r['license'] == 'cc-by'


@respx.mock
def test_find_open_access_closed():
    respx.get(url__regex=oa).mock(return_value=httpx.Response(200, json=load_fixture('openalex_closed.json')))
    r = abstracts.find_open_access('10.9999/closed.2022.020')
    assert r['is_oa'] is False and r['pdf_url'] is None and r['proxy_url']

import re

import httpx
import respx

from conftest import load_fixture
from elsevier_research_mcp_utm import config, doctor

search = re.compile(r'https://api\.elsevier\.com/content/search/scopus.*')
abstract = re.compile(r'https://api\.elsevier\.com/content/abstract/.*')
entitlement = re.compile(r'https://api\.elsevier\.com/content/article/entitlement/.*')


def err(code):
    return {'service-error': {'status': {'statusCode': code, 'statusText': 'x'}}}


def test_no_key(monkeypatch):
    monkeypatch.setattr(config, 'api_key', '')
    r = doctor.run()
    assert r['tier'] == 'none' and not r['api_key_set']
    assert 'dev.elsevier.com' in r['advice'][0]


@respx.mock
def test_metadata_only_off_campus():
    respx.get(url__regex=search).mock(return_value=httpx.Response(
        200, json=load_fixture('scopus_search.json'), headers={'X-RateLimit-Remaining': '19000'}))
    respx.get(url__regex=abstract).mock(return_value=httpx.Response(401, json=err('AUTHORIZATION_ERROR')))
    respx.get(url__regex=entitlement).mock(return_value=httpx.Response(403, json=err('AUTHENTICATION_ERROR')))
    r = doctor.run()
    assert r['api_key_valid'] and r['tier'] == 'metadata'
    assert r['abstracts'] is False and r['fulltext'] is False
    assert any('insttoken' in a for a in r['advice'])
    out = doctor.text(r)
    assert 'access tier      : metadata' in out and 'testkey123' not in out


@respx.mock
def test_fulltext_on_campus():
    data = load_fixture('scopus_search.json')
    respx.get(url__regex=search).mock(return_value=httpx.Response(200, json=data))
    respx.get(url__regex=abstract).mock(return_value=httpx.Response(200, json={}))
    respx.get(url__regex=entitlement).mock(return_value=httpx.Response(
        200, json={'entitlement-response': {'document-entitlement': {'entitled': True}}}))
    r = doctor.run()
    assert r['tier'] == 'fulltext' and r['advice'] == []


@respx.mock
def test_bad_key():
    respx.get(url__regex=search).mock(return_value=httpx.Response(401, json=err('AUTHENTICATION_ERROR')))
    r = doctor.run()
    assert r['api_key_valid'] is False and r['tier'] == 'none'

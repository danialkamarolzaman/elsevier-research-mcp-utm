import os
import re
import time

import httpx
import pytest
import respx

from conftest import load_fixture
from elsevier_research_mcp_utm import cache, config, fetch, limits

entitle = re.compile(r'https://api\.elsevier\.com/content/article/entitlement/.*')
article = re.compile(r'https://api\.elsevier\.com/content/article/(doi|pii)/.*')
els_abs = re.compile(r'https://api\.elsevier\.com/content/abstract/.*')
oa = re.compile(r'https://api\.openalex\.org/works/.*')
s2 = re.compile(r'https://api\.semanticscholar\.org/.*')
pdf_bytes = b'%PDF-1.7\n' + b'0' * 5000
doi = '10.9999/closed.2022.020'


def entitled(yes=True):
    if yes:
        body = {'entitlement-response': {'document-entitlement': {'entitled': True}}}
        return httpx.Response(200, json=body)
    return httpx.Response(403, json={'service-error': {'status': {
        'statusCode': 'AUTHENTICATION_ERROR', 'statusText': 'insufficient'}}})


def metadata_mocks(oa_fixture='openalex_closed.json'):
    respx.get(url__regex=els_abs).mock(return_value=httpx.Response(401, json={'service-error': {
        'status': {'statusCode': 'AUTHORIZATION_ERROR', 'statusText': 'x'}}}))
    respx.get(url__regex=oa).mock(return_value=httpx.Response(200, json=load_fixture(oa_fixture)))
    respx.get(url__regex=s2).mock(return_value=httpx.Response(200, json={'abstract': None}))


def fill_window(n=5):
    for i in range(n):
        cache.log_fetch(f'10.1/{i}', 'pdf', 1000, ts=time.time() - 60 - i)


# ---------------- full text ----------------
@respx.mock
def test_fulltext_not_entitled_fetches_nothing():
    respx.get(url__regex=entitle).mock(return_value=entitled(False))
    route = respx.get(url__regex=article)
    r = fetch.get_fulltext(doi)
    assert not r['ok'] and 'no full-text access' in r['reason'] and r['proxy_url']
    assert not route.called and limits.usage()['window_articles'] == 0


@respx.mock
def test_fulltext_counted_once_then_paged_from_cache():
    respx.get(url__regex=entitle).mock(return_value=entitled())
    route = respx.get(url__regex=article).mock(return_value=httpx.Response(200, text='abcdefghij' * 300))
    r = fetch.get_fulltext(doi, max_chars=1000)
    assert r['ok'] and r['total_chars'] == 3000 and r['end'] == 1000 and r['more']
    r2 = fetch.get_fulltext(doi, start=r['end'], max_chars=5000)
    assert r2['cached'] and r2['end'] == 3000 and not r2['more']
    assert route.call_count == 1 and limits.usage()['window_articles'] == 1


@respx.mock
def test_fulltext_refused_at_limit():
    fill_window()
    respx.get(url__regex=entitle).mock(return_value=entitled())
    route = respx.get(url__regex=article)
    r = fetch.get_fulltext(doi)
    assert not r['ok'] and '5/5' in r['reason'] and r['next_allowed']
    assert not route.called


def test_fulltext_needs_id():
    with pytest.raises(ValueError):
        fetch.get_fulltext()


# ---------------- pdf ----------------
@respx.mock
def test_pdf_open_access_first_not_counted():
    metadata_mocks('openalex_oa.json')
    respx.get('https://example.org/paper.pdf').mock(return_value=httpx.Response(200, content=pdf_bytes))
    ent = respx.get(url__regex=entitle)
    r = fetch.download_pdf('10.9999/open.2023.010')
    assert r['ok'] and r['source'] == 'open_access' and not r['counted']
    name = 'Author 2023 - An invented open-access paper about knowledge graphs.pdf'
    assert os.path.basename(r['path']) == name
    assert open(r['path'], 'rb').read() == pdf_bytes
    assert not ent.called and limits.usage()['window_articles'] == 0


@respx.mock
def test_pdf_elsevier_counted_and_named():
    metadata_mocks()
    respx.get(url__regex=entitle).mock(return_value=entitled())
    respx.get(url__regex=article).mock(return_value=httpx.Response(200, content=pdf_bytes))
    r = fetch.download_pdf(doi)
    assert r['ok'] and r['source'] == 'elsevier' and r['counted']
    assert os.path.basename(r['path']) == 'Author 2022 - An invented subscription paper.pdf'
    u = limits.usage()
    assert u['window_articles'] == 1 and u['window_mb'] == round(len(pdf_bytes) / 1e6, 2)
    again = fetch.download_pdf(doi)
    assert again['source'] == 'already_downloaded' and limits.usage()['window_articles'] == 1


@respx.mock
def test_pdf_not_entitled():
    metadata_mocks()
    respx.get(url__regex=entitle).mock(return_value=entitled(False))
    route = respx.get(url__regex=article)
    r = fetch.download_pdf(doi, filename='[012] Mine')
    assert not r['ok'] and 'no institutional access' in r['reason']
    assert 'no open-access PDF listed' in r['notes']
    assert not route.called and not os.listdir(config.download_dir)


@respx.mock
def test_pdf_too_large_refused_before_body(monkeypatch):
    metadata_mocks()
    respx.get(url__regex=entitle).mock(return_value=entitled())
    respx.get(url__regex=article).mock(return_value=httpx.Response(
        200, content=pdf_bytes, headers={'Content-Length': str(200_000_000)}))
    r = fetch.download_pdf(doi)
    assert not r['ok'] and 'MB left' in r['reason']
    assert limits.usage()['window_articles'] == 0 and not os.listdir(config.download_dir)


@respx.mock
def test_pdf_stopped_midway_is_logged(monkeypatch):
    monkeypatch.setattr(config, 'max_mb_per_window', 1)
    metadata_mocks()
    respx.get(url__regex=entitle).mock(return_value=entitled())
    chunks = [b'%PDF'] + [b'0' * 500_000] * 6  # streamed, no Content-Length up front
    respx.get(url__regex=article).mock(return_value=httpx.Response(200, content=iter(chunks)))
    r = fetch.download_pdf(doi)
    assert not r['ok'] and 'stopped at' in r['reason']
    assert limits.usage()['window_articles'] == 1  # partial bytes still count
    assert not os.listdir(config.download_dir)


@respx.mock
def test_html_instead_of_pdf_rejected():
    metadata_mocks()
    respx.get(url__regex=entitle).mock(return_value=entitled())
    respx.get(url__regex=article).mock(return_value=httpx.Response(200, content=b'<html>login</html>'))
    r = fetch.download_pdf(doi)
    assert not r['ok'] and 'did not return a PDF' in r['reason']
    assert not os.listdir(config.download_dir)


# ---------------- batch ----------------
def test_batch_max_five():
    with pytest.raises(ValueError):
        fetch.download_batch([f'10.1/{i}' for i in range(6)])


@respx.mock
def test_batch_stops_at_limit():
    fill_window(4)
    metadata_mocks()
    respx.get(url__regex=entitle).mock(return_value=entitled())
    respx.get(url__regex=article).mock(return_value=httpx.Response(200, content=pdf_bytes))
    r = fetch.download_batch(['10.9999/a', '10.9999/b', '10.9999/c'], prefer_open_access=False)
    oks = [x['ok'] for x in r['results']]
    assert oks == [True, False]
    assert 'limit' in r['results'][1]['reason']
    assert r['not_attempted'] == ['10.9999/c']


@respx.mock
def test_same_name_different_paper_keeps_both():
    metadata_mocks()  # every DOI gets the same title / author / year
    respx.get(url__regex=entitle).mock(return_value=entitled())
    respx.get(url__regex=article).mock(return_value=httpx.Response(200, content=pdf_bytes))
    a = fetch.download_pdf('10.9999/a', prefer_open_access=False)
    b = fetch.download_pdf('10.9999/b', prefer_open_access=False)
    assert a['source'] == b['source'] == 'elsevier' and a['path'] != b['path']
    assert b['path'].endswith('(10.9999_b).pdf')
    assert fetch.download_pdf('10.9999/b')['source'] == 'already_downloaded'
    assert limits.usage()['window_articles'] == 2

import csv
import os
import re

import httpx
import pytest
import respx

from conftest import load_fixture
from elsevier_research_mcp_utm import export, models

oa = re.compile(r'https://api\.openalex\.org/works/.*')
els_abs = re.compile(r'https://api\.elsevier\.com/content/abstract/.*')
s2 = re.compile(r'https://api\.semanticscholar\.org/.*')


def paper(**kw):
    p = models.empty_paper()
    p.update({'doi': '10.1/x', 'title': 'Graph methods for maintenance',
              'authors': ['Liqiao Xia', 'Jo Bloggs'], 'first_author': 'Liqiao Xia', 'year': 2022, 'journal': 'R&D Journal', 'volume': '9',
              'issue': '2', 'pages': '10-20'})
    p.update(kw)
    return p


def test_bibtex():
    text = export.to_bibtex([paper(), paper(doi='10.1/y')])
    assert '@article{xia2022graph,' in text and '@article{xia2022grapha,' in text
    assert 'author = {Liqiao Xia and Jo Bloggs},' in text
    assert 'journal = {R\\&D Journal},' in text
    assert 'pages = {10--20},' in text and 'doi = {10.1/x},' in text


def test_bibtex_accents_in_key():
    text = export.to_bibtex([paper(first_author='José Müller', authors=['José Müller'])])
    assert '@article{muller2022graph,' in text


def test_ris():
    text = export.to_ris([paper(abstract='An abstract.')])
    assert text.startswith('TY  - JOUR\nAU  - Liqiao Xia\nAU  - Jo Bloggs\n')
    assert 'SP  - 10\nEP  - 20' in text and 'AB  - An abstract.' in text
    assert text.rstrip().endswith('ER  -')


def test_csv(tmp_path):
    path = str(tmp_path / 'r.csv')
    export.write_csv([paper()], path)
    with open(path, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    assert rows[0]['authors'] == 'Liqiao Xia; Jo Bloggs' and rows[0]['year'] == '2022'


@respx.mock
def test_export_tool_end_to_end():
    respx.get(url__regex=els_abs).mock(return_value=httpx.Response(401, json={'service-error': {
        'status': {'statusCode': 'AUTHORIZATION_ERROR', 'statusText': 'x'}}}))

    def openalex(request):
        if 'missing' in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200, json=load_fixture('openalex_oa.json'))
    respx.get(url__regex=oa).mock(side_effect=openalex)
    respx.get(url__regex=s2).mock(return_value=httpx.Response(404))
    dois = ['10.9999/open.2023.010', 'doi:10.9999/OPEN.2023.010', '10.9999/missing']  # dup + unknown
    r = export.export_references(dois, 'ris')
    assert r['exported'] == 1 and r['missing_metadata'] == ['10.9999/missing']
    assert os.path.basename(r['path']).startswith('references_') and r['path'].endswith('.ris')
    assert 'TI  - An invented open-access paper' in open(r['path'], encoding='utf-8').read()


def test_export_rejects_bad_input():
    with pytest.raises(ValueError):
        export.export_references(['10.1/x'], 'docx')
    with pytest.raises(ValueError):
        export.export_references([], 'csv')
    with pytest.raises(ValueError):
        export.export_references([f'10.1/{i}' for i in range(101)], 'csv')

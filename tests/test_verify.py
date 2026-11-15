import zipfile

import pytest

from elsevier_research_mcp_utm import abstracts, cache, models, verify
from elsevier_research_mcp_utm.sources import scopus

real = {
    '10.1016/j.jmsy.2022.01.001': {
        'title': 'Knowledge graph based fault diagnosis for machine tools', 'first_author': 'Liqiao Xia',
        'year': 2022, 'journal': 'Journal of Manufacturing Systems',
        'abstract': 'We propose a knowledge graph for fault diagnosis. The method reached an accuracy of '
                    '94.2% on the CNC dataset, outperforming rule-based baselines.'},
    '10.1016/j.rcim.2023.102555': {
        'title': 'Maintenance knowledge graphs: a review', 'first_author': 'Ana Silva', 'year': 2023,
        'journal': 'Robotics and Computer-Integrated Manufacturing', 'abstract': None,
        'pii': 'S0736584523000000'},
}

draft = '''# Knowledge graphs for maintenance

Knowledge graphs improve fault diagnosis [1, AB]. Reviews exist [2, AB].

## References

[1] L. Xia, J. Bloggs, "Knowledge graph based fault diagnosis for machine tools," J. Manuf. Syst., vol. 62,
pp. 1-10, 2022, doi: 10.1016/j.jmsy.2022.01.001.

[2] A. Silva, "Maintenance knowledge graphs: a review," Robot. Comput.-Integr. Manuf., 2023,
doi: 10.1016/j.rcim.2023.102555.

## Sources

| n | DOI | evidence | full text from |
|---|---|---|---|
| 1 | 10.1016/j.jmsy.2022.01.001 | [AB] | - |
| 2 | 10.1016/j.rcim.2023.102555 | [AB] | sciencedirect |

## Verification table

| claim | citation | [FT]/[AB] | supporting quote or section |
|---|---|---|---|
| KG for diagnosis | [1, AB] | AB | "We propose a knowledge-graph for fault diagnosis." |
| accuracy | [1] | AB | "accuracy of 94.2 % on the CNC data-set" |
| invented | [1] | AB | "the method cut downtime by 40% in three factories" |
| ellipsis | [1] | AB | "We propose a knowledge graph ... outperforming rule-based baselines" |
| review | [2] | AB | "maintenance knowledge graphs are reviewed in depth" |
| uncited | [7] | AB | "something that has no reference at all" |
| section | [1] | AB | Section 3 |
| short | [1] | AB | "94.2%" |
'''


@pytest.fixture(autouse=True)
def fake_lookup(monkeypatch):
    def get_abstract(doi):
        doi = models.clean_doi(doi)
        p = models.empty_paper()
        p['doi'] = doi
        if doi in real:
            p.update(real[doi])
            return {'paper': p, 'notes': []}
        return {'paper': p, 'notes': ['openalex: DOI not found']}
    monkeypatch.setattr(abstracts, 'get_abstract', get_abstract)


def write(tmp_path, text, name='draft.md'):
    path = tmp_path / name
    path.write_text(text, encoding='utf-8')
    return str(path)


# ---------------- helpers ----------------
def test_squash_ignores_layout():
    assert verify.squash('Degra-\ndation  of ﬁbre') == verify.squash('degradation of fibre')


def test_find_dois_strips_punctuation():
    text = 'see doi: 10.1016/j.x.2020.1). and https://doi.org/10.1234/ABC.'
    assert verify.find_dois(text) == ['10.1016/j.x.2020.1', '10.1234/abc']


def test_reference_section_and_entries():
    entries = verify.split_entries(verify.reference_section(draft))
    assert len(entries) == 2 and entries[0].startswith('[1] L. Xia')
    assert 'Sources' not in entries[1]


def test_numbered_heading_found():
    assert verify.reference_section('text\n\n7. REFERENCES\n\n[1] A, "B c d e f," 2020.\n') is not None
    assert verify.reference_section('References to prior work are many.\n') is None


# ---------------- references ----------------
def test_verify_references_ok(tmp_path):
    out = verify.verify_references(write(tmp_path, draft))
    assert out['verdict'] == 'PASS' and out['counts'] == {'OK': 2}
    # abbreviated journal is only advisory
    assert any(p.get('advisory') for p in out['results'][0]['problems'])


def test_verify_references_mismatch_and_fake(tmp_path):
    bad = draft.replace('L. Xia', 'K. Wong').replace('2022, doi', '2019, doi')
    bad = bad.replace('10.1016/j.rcim.2023.102555', '10.1016/j.fake.2023.999')
    out = verify.verify_references(write(tmp_path, bad))
    assert out['verdict'] == 'FAIL' and out['blocking'] == 2
    first, second = out['results']
    assert first['status'] == 'MISMATCH'
    assert {p['field'] for p in first['problems'] if not p.get('advisory')} == {'first_author', 'year'}
    assert second['status'] == 'NOT_FOUND'


def test_year_not_read_from_doi(tmp_path):
    # the DOI contains 2023 but the written year is right
    out = verify.verify_references(write(tmp_path, draft))
    assert not [p for p in out['results'][1].get('problems', []) if p['field'] == 'year']


def test_lookup_failure_is_not_fake(monkeypatch):
    p = models.empty_paper()
    monkeypatch.setattr(abstracts, 'get_abstract',
                        lambda d: {'paper': p, 'notes': ['openalex: HTTP 503 service unavailable']})
    assert verify.check_doi('10.1/x')['status'] == 'LOOKUP_FAILED'


def test_no_doi_searched_by_title(tmp_path, monkeypatch):
    hit = {**models.empty_paper(), **real['10.1016/j.jmsy.2022.01.001'], 'doi': '10.1016/j.jmsy.2022.01.001'}
    monkeypatch.setattr(scopus, 'search', lambda *a, **k: {'papers': [hit]})
    text = ('## References\n\n[1] L. Xia, "Knowledge graph based fault diagnosis for machine tools," '
            'J. Manuf. Syst., 2022.\n')
    out = verify.verify_references(write(tmp_path, text))
    r = out['results'][0]
    assert r['status'] == 'NO_DOI' and r['suggested_doi'] == '10.1016/j.jmsy.2022.01.001'
    assert out['verdict'] == 'PASS'


def test_dois_mode():
    out = verify.verify_references(dois=['https://doi.org/10.1016/J.JMSY.2022.01.001', '10.9/none'])
    assert [r['status'] for r in out['results']] == ['OK', 'NOT_FOUND']


def test_dois_in_text_missing_from_references(tmp_path):
    text = draft.replace('Reviews exist', 'See 10.1016/j.other.2021.5 and reviews exist')
    out = verify.verify_references(write(tmp_path, text))
    assert out['dois_in_text_not_in_references'] == ['10.1016/j.other.2021.5']


def test_docx_reference_list(tmp_path):
    ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    paras = ['Chapter 2', 'References',
             'L. Xia, "Knowledge graph based fault diagnosis for machine tools," 2022, '
             'doi: 10.1016/j.jmsy.2022.01.001.',
             'A. Silva, "Maintenance knowledge graphs: a review," 2023, doi: 10.1016/j.rcim.2023.102555.']
    body = ''.join(f'<w:p><w:r><w:t>{p}</w:t></w:r></w:p>' for p in paras)
    path = tmp_path / 'thesis.docx'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('word/document.xml', f'<w:document xmlns:w="{ns}"><w:body>{body}</w:body></w:document>')
    out = verify.verify_references(str(path))
    assert out['checked'] == 2 and out['verdict'] == 'PASS'


def test_missing_references_heading(tmp_path):
    with pytest.raises(ValueError):
        verify.verify_references(write(tmp_path, 'no list here'))


# ---------------- quotes ----------------
def test_check_quotes(tmp_path):
    out = verify.check_quotes(write(tmp_path, draft))
    by_claim = {}
    for r in out['results']:
        by_claim.setdefault(r['claim'], r)
    assert by_claim['KG for diagnosis']['status'] == 'FOUND'
    assert by_claim['accuracy']['status'] == 'FOUND'
    assert by_claim['invented']['status'] == 'NOT_FOUND'
    assert by_claim['ellipsis']['status'] == 'FOUND'
    assert by_claim['review']['status'] == 'SOURCE_UNAVAILABLE'
    assert by_claim['uncited']['status'] == 'NO_SOURCE'
    assert by_claim['section']['status'] == 'NOT_A_QUOTE'
    assert by_claim['short']['status'] == 'TOO_SHORT'
    assert out['verdict'] == 'FAIL' and out['blocking'] == 2


def test_check_quotes_uses_cached_fulltext(tmp_path):
    cache.put('fulltext:S0736584523000000', {'text': 'In this paper, maintenance knowledge graphs are '
                                                     'reviewed in depth across 120 studies.'})
    out = verify.check_quotes(write(tmp_path, draft))
    review = [r for r in out['results'] if r['claim'] == 'review'][0]
    assert review['status'] == 'FOUND' and review['in'] == 'fulltext:[2]'


def test_check_quotes_reads_local_pdf(tmp_path, monkeypatch):
    pdf = tmp_path / 'silva.pdf'
    pdf.write_bytes(b'%PDF')
    monkeypatch.setattr(verify, 'pdf_text', lambda p: 'Maintenance knowledge graphs are reviewed in depth.')
    text = draft.replace('| [AB] | sciencedirect |', f'| [FT] | pdf:{pdf} |')
    out = verify.check_quotes(write(tmp_path, text))
    review = [r for r in out['results'] if r['claim'] == 'review'][0]
    assert review['status'] == 'FOUND' and review['in'] == 'pdf:[2]'


def test_verifier_report_table(tmp_path):
    report = draft + '''
VERDICT: FAIL

| # | Location | Claim (short) | Cites | Verdict | Evidence (short quote from source) | Fix |
|---|---|---|---|---|---|---|
| 1 | Intro | downtime | [1] | UNSUPPORTED | source says "outperforming rule-based baselines" | remove |
| 2 | Intro | made up | [1] | CONTRADICTED | "the method failed on every dataset" | remove |
'''
    out = verify.check_quotes(write(tmp_path, report))
    statuses = {r['claim']: r['status'] for r in out['results']}
    assert statuses['downtime'] == 'FOUND' and statuses['made up'] == 'NOT_FOUND'


def test_real_pdf_text(tmp_path):
    # a minimal one-page PDF with one line of text, read with pypdf
    content = b'BT /F1 12 Tf 72 720 Td (Fault diagnosis with knowledge graphs) Tj ET'
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R '
            b'/Resources << /Font << /F1 5 0 R >> >> >>',
            b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    out, offsets = b'%PDF-1.4\n', []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    out += b''.join(b'%010d 00000 n \n' % o for o in offsets)
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, xref)
    path = tmp_path / 'p.pdf'
    path.write_bytes(out)
    assert 'Fault diagnosis with knowledge graphs' in verify.pdf_text(str(path))

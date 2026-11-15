import logging
import os
import re
import unicodedata
import zipfile
from xml.etree import ElementTree

from . import abstracts, cache, client, models
from .sources import scopus

# deterministic checks against hallucination: no model judgement, only lookups and exact text matching.
# nothing here downloads full text or counts toward institution limits.
max_file_mb = 50
max_refs = 300
min_quote_chars = 12  # shorter quotes (after normalising) are too weak to prove anything
doi_re = re.compile(r'10\.\d{4,9}/[^\s"<>|`]+', re.I)
year_re = re.compile(r'\b(19|20)\d{2}\b')
ref_heading_re = re.compile(
    r'^\s*(#+\s*|\*\*)?\s*(\d+(\.\d+)*\.?\s+)?(references|bibliography|reference list|works cited)'
    r'\s*(\*\*)?\s*:?\s*$', re.I | re.M)
url_re = re.compile(r'https?://\S+|10\.\d{4,9}/\S+', re.I)
next_heading_re = re.compile(r'^\s*(#+\s|\*\*[A-Z])', re.M)
entry_start_re = re.compile(r'^\s*(\[\d+\]|\d+[.)]\s|[-*]\s)')
cite_num_re = re.compile(r'\d+')
quote_re = re.compile(r'"([^"]+)"|“([^”]+)”')
ellipsis_re = re.compile(r'\.\.\.|…|\[[^\]]*\]')
pdf_texts = {}  # path + mtime -> extracted text, for this process


# ---------------- reading files ----------------
def _docx_text(path):
    ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
    with zipfile.ZipFile(path) as z:
        root = ElementTree.fromstring(z.read('word/document.xml'))
    lines = []
    for p in root.iter(ns + 'p'):
        lines.append(''.join(t.text or '' for t in p.iter(ns + 't')))
    return '\n\n'.join(lines)  # blank line between paragraphs: one Word paragraph = one reference


def pdf_text(path):
    key = f'{path}|{os.path.getmtime(path)}'
    if key not in pdf_texts:
        from pypdf import PdfReader
        logging.getLogger('pypdf').setLevel(logging.ERROR)  # font warnings are noise here
        reader = PdfReader(path)
        pdf_texts[key] = '\n'.join((page.extract_text() or '') for page in reader.pages)
    return pdf_texts[key]


def read_document(path):
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(path):
        raise ValueError(f'file not found: {path}')
    if os.path.getsize(path) > max_file_mb * 1e6:
        raise ValueError(f'file is larger than {max_file_mb} MB')
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        return _docx_text(path)
    if ext == '.pdf':
        return pdf_text(path)
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        return f.read()


# ---------------- text helpers ----------------
def squash(text):
    # lower-case letters and digits only: ignores spacing, case, punctuation, ligatures, line-break hyphens
    text = unicodedata.normalize('NFKC', text or '').lower()
    return ''.join(ch for ch in text if ch.isalnum())


def _words(text):
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode().lower()
    return re.findall(r'[a-z0-9]+', text)


def _strip_doi(doi):
    return models.clean_doi(doi.rstrip('.,;:)]}*_\'')) if doi else None


def find_dois(text):
    seen = []
    for m in doi_re.finditer(text or ''):
        d = _strip_doi(m.group(0))
        if d and d not in seen:
            seen.append(d)
    return seen


def reference_section(text):
    # text after the last References heading, up to the next heading
    starts = list(ref_heading_re.finditer(text))
    if not starts:
        return None
    body = text[starts[-1].end():]
    body = body.split('\n', 1)[1] if '\n' in body else ''
    nxt = next_heading_re.search(body)
    return body[:nxt.start()] if nxt else body


def split_entries(section):
    entries, cur = [], []
    for line in section.splitlines():
        if not line.strip() or line.strip().startswith('|'):
            if cur:
                entries.append(' '.join(cur))
                cur = []
            continue
        if entry_start_re.match(line) and cur:
            entries.append(' '.join(cur))
            cur = []
        cur.append(line.strip())
    if cur:
        entries.append(' '.join(cur))
    return [e for e in entries if len(e) > 15]


def _entry_number(entry):
    m = re.match(r'\s*\[(\d+)\]|\s*(\d+)[.)]\s', entry)
    return int(m.group(1) or m.group(2)) if m else None


def _quoted_title(entry):
    m = quote_re.search(entry)
    if m:
        return (m.group(1) or m.group(2)).strip(' ,.')
    return None


# ---------------- references ----------------
def _title_match(title, entry):
    want = [w for w in _words(title) if len(w) > 2]
    if not want:
        return True
    have = set(_words(entry))
    return sum(w in have for w in want) / len(want) >= 0.8


def compare(paper, entry):
    # fields written in the reference entry that disagree with the looked-up metadata
    problems = []
    if paper.get('title') and not _title_match(paper['title'], entry):
        problems.append({'field': 'title', 'correct': paper['title']})
    year = paper.get('year')
    years = {int(m.group(0)) for m in year_re.finditer(url_re.sub(' ', entry))}  # not digits inside DOIs
    if year and years and year not in years:
        # online-first vs issue year can differ by one: flag, but say so
        near = any(abs(y - year) == 1 for y in years)
        problems.append({'field': 'year', 'correct': year, 'written': sorted(years),
                         'note': 'off by one (online-first vs issue year?)' if near else None})
    first = paper.get('first_author') or ''
    names = [w for w in _words(first) if len(w) > 1]  # initials alone prove nothing
    if names and not set(names) & set(_words(entry)):
        problems.append({'field': 'first_author', 'correct': first})
    journal = paper.get('journal')
    if journal and not _title_match(journal, entry):
        # abbreviated journal names are normal in IEEE style, so this one is advisory
        problems.append({'field': 'journal', 'correct': journal, 'advisory': True})
    return problems


def check_doi(doi, entry=None):
    try:
        got = abstracts.get_abstract(doi)
    except (client.ApiError, ValueError) as e:
        return {'doi': doi, 'status': 'LOOKUP_FAILED', 'reason': str(e)}
    p = got['paper']
    if not p.get('title'):
        if 'openalex: DOI not found' in got['notes']:
            return {'doi': doi, 'status': 'NOT_FOUND', 'notes': got['notes'],
                    'reason': 'no Elsevier or OpenAlex record for this DOI (fake, mistyped or very new)'}
        return {'doi': doi, 'status': 'LOOKUP_FAILED', 'notes': got['notes'],
                'reason': 'a lookup service did not answer; try again later'}
    found = {k: p.get(k) for k in ('title', 'first_author', 'year', 'journal')}
    out = {'doi': doi, 'found': found, 'has_abstract': bool(p.get('abstract'))}
    if entry is None:
        return {**out, 'status': 'OK'}
    problems = compare(p, entry)
    blocking = [x for x in problems if not x.get('advisory')]
    return {**out, 'status': 'MISMATCH' if blocking else 'OK', 'problems': problems}


def _search_title(title):
    clean = re.sub(r'[^\w\s-]', ' ', title)
    clean = re.sub(r'\s+', ' ', clean).strip()
    try:
        res = scopus.search(f'TITLE("{clean}")', sort='relevance', count=3)
    except client.ApiError as e:
        return None, str(e)
    for p in res['papers']:
        if p.get('title') and squash(p['title']) == squash(title):
            return p, None
    if res['papers'] and _title_match(title, res['papers'][0].get('title') or ''):
        return res['papers'][0], 'closest title, not exact'
    return None, None


def verify_references(path=None, dois=None):
    if not path and not dois:
        raise ValueError('give a file path or a list of DOIs')
    results = []
    if dois:
        for d in [models.clean_doi(x) for x in dois][:max_refs]:
            if d:
                results.append(check_doi(d))
        return _summary(results, {})
    text = read_document(path)
    section = reference_section(text)
    if section is None:
        raise ValueError('no "References" (or "Bibliography") heading found in the file')
    entries = split_entries(section)[:max_refs]
    for i, entry in enumerate(entries):
        n = _entry_number(entry) or i + 1
        found = find_dois(entry)
        if found:
            r = check_doi(found[0], entry)
        else:
            title = _quoted_title(entry)
            if not title:
                r = {'status': 'NO_DOI', 'reason': 'no DOI and no quoted title to search for'}
            else:
                hit, note = _search_title(title)
                if hit:
                    r = {'status': 'NO_DOI', 'suggested_doi': hit.get('doi'), 'note': note,
                         'found': {k: hit.get(k) for k in ('title', 'first_author', 'year', 'journal')}}
                else:
                    r = {'status': 'NOT_FOUND', 'reason': note or 'title not found in Scopus'}
        results.append({'ref': n, 'entry': entry[:300], **r})
    body = text[:text.find(section)] if section in text else text
    listed = {r.get('doi') for r in results}
    extra = {'dois_in_text_not_in_references': [d for d in find_dois(body) if d not in listed]}
    return _summary(results, extra)


def _summary(results, extra):
    counts = {}
    for r in results:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    blocking = sum(counts.get(s, 0) for s in ('NOT_FOUND', 'MISMATCH'))
    return {'verdict': 'FAIL' if blocking else 'PASS', 'blocking': blocking, 'counts': counts,
            'checked': len(results), 'results': results, **extra,
            'note': 'NOT_FOUND and MISMATCH are blocking. NO_DOI is not proof of a fake reference: '
                    'add the suggested DOI or check it by hand. LOOKUP_FAILED means a service was down.'}


# ---------------- quotes ----------------
def _cells(line):
    line = line.strip()
    if not line.startswith('|'):
        return None
    return [c.strip() for c in line.strip('|').split('|')]


def tables(text):
    # markdown tables as (header cells, list of row cells)
    out, lines, i = [], text.splitlines(), 0
    while i < len(lines) - 1:
        head, sep = _cells(lines[i]), _cells(lines[i + 1])
        if head and sep and all(re.fullmatch(r':?-{2,}:?', c or '--') for c in sep):
            rows, j = [], i + 2
            while j < len(lines) and _cells(lines[j]) is not None:
                rows.append(_cells(lines[j]))
                j += 1
            out.append((head, rows))
            i = j
        else:
            i += 1
    return out


def _col(head, *names, exact=False):
    # first name (in priority order) that matches a header cell
    for n in names:
        for k, h in enumerate(head):
            h = h.lower().strip(' *')
            if (h == n) if exact else (n in h):
                return k
    return None


def source_map(text):
    # ref number -> {doi, pdf} from the Sources table, else from the reference list
    refs = {}
    for head, rows in tables(text):
        c_doi, c_n = _col(head, 'doi'), _col(head, 'n', '#', 'ref', 'no', 'no.', exact=True)
        c_from = _col(head, 'from')
        if c_doi is None or c_n is None:
            continue
        for row in rows:
            if len(row) <= max(c_doi, c_n):
                continue
            num, d = cite_num_re.search(row[c_n]), find_dois(row[c_doi])
            if not num or not d:
                continue
            entry = {'doi': d[0], 'pdf': None}
            where = row[c_from] if c_from is not None and c_from < len(row) else ''
            m = re.search(r'pdf:\s*`?([^`|]+?)`?\s*$', where)
            if m:
                entry['pdf'] = m.group(1).strip()
            refs[int(num.group(0))] = entry
    section = reference_section(text)
    for i, entry in enumerate(split_entries(section) if section else []):
        n, d = _entry_number(entry) or i + 1, find_dois(entry)
        if d and n not in refs:
            refs[n] = {'doi': d[0], 'pdf': None}
    return refs


def source_texts(doi, pdf=None):
    # only what is already on this machine or free: abstract (cached lookup), cached full text, local PDF
    texts, notes = {}, []
    try:
        p = abstracts.get_abstract(doi)['paper']
    except (client.ApiError, ValueError) as e:
        p = {}
        notes.append(f'abstract lookup failed: {e}')
    if p.get('abstract'):
        texts['abstract'] = p['abstract']
    for key in filter(None, [p.get('pii'), doi]):
        hit = cache.get('fulltext:' + key, max_days=3650)
        if hit:
            texts['fulltext'] = hit['text']
            break
    if not pdf:
        hit = cache.get('pdf_path:' + doi, max_days=3650)
        pdf = hit and hit['path']
    if pdf and os.path.isfile(pdf):
        try:
            texts['pdf'] = pdf_text(pdf)
        except Exception as e:  # damaged or scanned pdf: report, do not fail the whole check
            notes.append(f'could not read PDF text: {e}')
    elif pdf:
        notes.append(f'PDF not found: {pdf}')
    return texts, notes


def _prefix_found(q, hay):
    # length of the longest prefix of q found in hay (prefix presence is monotone: binary search)
    lo, hi = 0, len(q)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if q[:mid] in hay:
            lo = mid
        else:
            hi = mid - 1
    return lo


def match_quote(quote, texts):
    parts = [squash(p) for p in ellipsis_re.split(quote)]
    parts = [p for p in parts if len(p) >= 3]
    total = sum(len(p) for p in parts)
    if total < min_quote_chars:
        return {'status': 'TOO_SHORT'}
    best = 0
    for name, text in texts.items():
        hay, pos, ok = squash(text), 0, True
        for p in parts:  # ellipsis parts must appear in order
            k = hay.find(p, pos)
            if k < 0:
                ok = False
                break
            pos = k + len(p)
        if ok:
            return {'status': 'FOUND', 'in': name}
        best = max(best, _prefix_found(parts[0], hay) / max(len(parts[0]), 1))
    return {'status': 'NOT_FOUND', 'best_prefix_match': round(best, 2)}


def check_quotes(path):
    text = read_document(path)
    refs = source_map(text)
    cache_src, results = {}, []
    for head, rows in tables(text):
        c_q = _col(head, 'quote', 'evidence')
        c_c = _col(head, 'citation', 'cites', 'cite')
        if c_q is None or c_c is None or c_q == c_c:
            continue
        c_claim = _col(head, 'claim')
        for row in rows:
            if len(row) <= max(c_q, c_c):
                continue
            claim = row[c_claim][:120] if c_claim is not None and c_claim < len(row) else ''
            nums = [int(x) for x in cite_num_re.findall(re.sub(r'\b(FT|AB)\b', '', row[c_c]))]
            quotes = [a or b for a, b in quote_re.findall(row[c_q])]
            base = {'claim': claim, 'cites': nums}
            if not quotes:
                results.append({**base, 'status': 'NOT_A_QUOTE', 'cell': row[c_q][:120]})
                continue
            unknown = [n for n in nums if n not in refs]
            dois = [refs[n]['doi'] for n in nums if n in refs]
            texts = {}
            for n in nums:
                if n not in refs:
                    continue
                d = refs[n]['doi']
                if d not in cache_src:
                    cache_src[d] = source_texts(d, refs[n]['pdf'])
                for name, t in cache_src[d][0].items():
                    texts[f'{name}:[{n}]'] = t
            for q in quotes:
                r = {**base, 'quote': q[:200], 'dois': dois}
                if not nums or (unknown and not dois):
                    r['status'] = 'NO_SOURCE'
                    r['reason'] = 'citation number not found in the Sources table or reference list'
                elif not texts:
                    r['status'] = 'SOURCE_UNAVAILABLE'
                    r['reason'] = 'no abstract, cached full text or local PDF for the cited paper'
                else:
                    r.update(match_quote(q, texts))
                    r['searched'] = sorted(texts)
                results.append(r)
    counts = {}
    for r in results:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    blocking = counts.get('NOT_FOUND', 0) + counts.get('NO_SOURCE', 0)
    return {'verdict': 'FAIL' if blocking else 'PASS', 'blocking': blocking, 'counts': counts,
            'quotes_checked': len(results), 'results': results,
            'source_notes': {d: v[1] for d, v in cache_src.items() if v[1]},
            'note': 'NOT_FOUND = the quoted words are not in the cited source (fabricated or paraphrased): '
                    'blocking. NO_SOURCE is blocking. SOURCE_UNAVAILABLE and TOO_SHORT cannot be checked '
                    'automatically: check by hand or mark UNCHECKABLE. Matching ignores case, spacing, '
                    'punctuation and line-break hyphens; "..." splits a quote into parts that must appear '
                    'in order.'}

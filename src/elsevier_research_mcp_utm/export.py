import csv
import os
import re
import time
import unicodedata

from . import abstracts, config, models, naming

max_dois = 100  # per call, metadata lookups take about 1 s each when not cached
formats = {'csv': '.csv', 'bibtex': '.bib', 'ris': '.ris'}
csv_columns = ['doi', 'title', 'authors', 'year', 'journal', 'volume', 'issue', 'pages', 'cited_by',
               'open_access', 'abstract_source', 'abstract', 'pii', 'scopus_id', 'url', 'proxy_url']


# ---------------- bibtex ----------------
def _ascii(text):
    return unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode()


def _authors(p):
    return p.get('authors') or ([p['first_author']] if p.get('first_author') else [])


def _bib_escape(text):
    return re.sub(r'([&%$#_])', r'\\\1', str(text))


def bib_key(paper, used):
    author = re.sub(r'[^A-Za-z]', '', _ascii(naming.surname(paper.get('first_author')))) or 'anon'
    words = [w for w in re.findall(r'[A-Za-z]+', _ascii(paper.get('title') or '')) if len(w) > 3]
    key = f"{author.lower()}{paper.get('year') or ''}{words[0].lower() if words else ''}"
    base, n = key, 0
    while key in used:
        n += 1
        key = base + chr(ord('a') + n - 1)
    used.add(key)
    return key


def to_bibtex(papers):
    used, out = set(), []
    for p in papers:
        fields = [
            ('author', ' and '.join(_authors(p))),
            ('title', '{' + (p.get('title') or '') + '}'),
            ('journal', p.get('journal')),
            ('year', p.get('year')),
            ('volume', p.get('volume')),
            ('number', p.get('issue')),
            ('pages', (p.get('pages') or '').replace('-', '--') or None),
            ('doi', p.get('doi')),
        ]
        lines = [f'@article{{{bib_key(p, used)},']
        for name, value in fields:
            if value not in (None, '', '{}'):
                value = value if name in ('title', 'doi') else _bib_escape(value)
                lines.append(f'  {name} = {{{value}}},')
        lines.append('}')
        out.append('\n'.join(lines))
    return '\n\n'.join(out) + '\n'


# ---------------- ris ----------------
def to_ris(papers):
    out = []
    for p in papers:
        lines = ['TY  - JOUR']
        for a in _authors(p):
            lines.append(f'AU  - {a}')
        pages = (p.get('pages') or '').split('-')
        for tag, value in [('TI', p.get('title')), ('T2', p.get('journal')), ('PY', p.get('year')),
                           ('VL', p.get('volume')), ('IS', p.get('issue')),
                           ('SP', pages[0] or None), ('EP', pages[1] if len(pages) > 1 else None),
                           ('DO', p.get('doi')), ('UR', p.get('url')), ('AB', p.get('abstract'))]:
            if value not in (None, ''):
                lines.append(f'{tag}  - {value}')
        lines.append('ER  - ')
        out.append('\n'.join(lines))
    return '\n\n'.join(out) + '\n'


# ---------------- csv ----------------
def write_csv(papers, path, mode='w'):
    with open(path, mode, newline='', encoding='utf-8-sig') as f:  # bom so Excel reads utf-8
        w = csv.DictWriter(f, fieldnames=csv_columns, extrasaction='ignore')
        w.writeheader()
        for p in papers:
            w.writerow({**p, 'authors': '; '.join(p.get('authors') or [])})


# ---------------- tool ----------------
def safe_path(path, fmt):
    # the path may come from an assistant: force the format's extension and never overwrite a file
    ext = formats[fmt]
    path = os.path.abspath(os.path.expanduser(path))
    if not path.lower().endswith(ext):
        path += ext
    stem, n = path[:-len(ext)], 2
    while os.path.exists(path):
        path = f'{stem} ({n}){ext}'
        n += 1
    return path


def export_references(dois, fmt='bibtex', path=None):
    if fmt not in formats:
        raise ValueError(f'format must be one of {sorted(formats)}')
    clean = []
    for d in dois or []:
        d = models.clean_doi(d)
        if d and d not in clean:
            clean.append(d)
    if not clean:
        raise ValueError('give at least one DOI')
    if len(clean) > max_dois:
        raise ValueError(f'at most {max_dois} DOIs per call, split the list')
    papers, missing = [], []
    for d in clean:
        p = abstracts.get_abstract(d)['paper']  # cached metadata, never counts toward limits
        (papers if p.get('title') else missing).append(p if p.get('title') else d)
    if not path:
        os.makedirs(config.download_dir, exist_ok=True)
        path = os.path.join(config.download_dir, f"references_{time.strftime('%Y%m%d-%H%M%S')}{formats[fmt]}")
    path = safe_path(path, fmt)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if fmt == 'csv':
        write_csv(papers, path, mode='x')  # 'x' fails rather than overwrite
    else:
        text = to_bibtex(papers) if fmt == 'bibtex' else to_ris(papers)
        with open(path, 'x', encoding='utf-8', newline='\n') as f:
            f.write(text)
    return {'path': path, 'format': fmt, 'exported': len(papers),
            'missing_metadata': missing}

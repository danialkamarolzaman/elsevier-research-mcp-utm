import re
from urllib.parse import quote

from . import config

# one paper shape for every source


def empty_paper():
    return {
        'doi': None, 'pii': None, 'scopus_id': None, 'eid': None,
        'title': None, 'authors': [], 'first_author': None, 'year': None,
        'journal': None, 'volume': None, 'issue': None, 'pages': None,
        'cited_by': None, 'open_access': None,
        'abstract': None, 'abstract_source': None,
        'url': None, 'proxy_url': None,
    }


def clean_doi(doi):
    # accepts 10.x/y, doi:10.x/y or https://doi.org/10.x/y
    doi = (doi or '').strip()
    doi = re.sub(r'^(https?://(dx\.)?doi\.org/|doi:\s*)', '', doi, flags=re.I)
    return doi.lower() or None


def proxy_url(doi=None, pii=None):
    # ezproxy 'starting point' link, opened by the user in a browser
    if not config.proxy_host:
        return None
    if pii:
        target = f'https://www.sciencedirect.com/science/article/pii/{pii}'
    elif doi:
        target = f'https://doi.org/{doi}'
    else:
        return None
    return f'https://{config.proxy_host}/login?url={quote(target, safe=":/")}'


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _finish(p):
    p['url'] = f"https://doi.org/{p['doi']}" if p['doi'] else None
    p['proxy_url'] = proxy_url(p['doi'], p['pii'])
    return p


def merge(base, extra):
    # fill empty fields of base from extra
    out = dict(base)
    for k, v in extra.items():
        if out.get(k) in (None, [], '') and v not in (None, [], ''):
            out[k] = v
    return _finish(out)


# ---------------- scopus ----------------
def from_scopus(entry):
    p = empty_paper()
    p['doi'] = clean_doi(entry.get('prism:doi'))
    p['pii'] = entry.get('pii')
    p['scopus_id'] = (entry.get('dc:identifier') or '').replace('SCOPUS_ID:', '') or None
    p['eid'] = entry.get('eid')
    p['title'] = entry.get('dc:title')
    creator = entry.get('dc:creator')
    p['first_author'] = creator if isinstance(creator, str) else None  # abstract api nests it
    if p['first_author']:
        p['authors'] = [p['first_author']]
    p['year'] = _int((entry.get('prism:coverDate') or '')[:4])
    p['journal'] = entry.get('prism:publicationName')
    p['volume'] = entry.get('prism:volume')
    p['issue'] = entry.get('prism:issueIdentifier')
    p['pages'] = entry.get('prism:pageRange')
    p['cited_by'] = _int(entry.get('citedby-count'))
    flag = entry.get('openaccessFlag')  # bool or 'true'/'false' depending on view
    if flag is not None:
        p['open_access'] = flag if isinstance(flag, bool) else str(flag).lower() == 'true'
    return _finish(p)


# ---------------- openalex ----------------
def abstract_from_inverted(inv):
    # openalex stores abstracts as {word: [positions]}
    if not inv:
        return None
    words = {}
    for word, positions in inv.items():
        for i in positions:
            words[i] = word
    return ' '.join(words[i] for i in sorted(words)) or None


def from_openalex(work):
    p = empty_paper()
    p['doi'] = clean_doi(work.get('doi'))
    p['title'] = work.get('title') or work.get('display_name')
    p['authors'] = [a['author']['display_name'] for a in work.get('authorships') or []
                    if (a.get('author') or {}).get('display_name')]
    p['first_author'] = p['authors'][0] if p['authors'] else None
    p['year'] = _int(work.get('publication_year'))
    source = (work.get('primary_location') or {}).get('source') or {}
    p['journal'] = source.get('display_name')
    biblio = work.get('biblio') or {}
    p['volume'] = biblio.get('volume')
    p['issue'] = biblio.get('issue')
    first, last = biblio.get('first_page'), biblio.get('last_page')
    p['pages'] = f'{first}-{last}' if first and last else first
    p['cited_by'] = _int(work.get('cited_by_count'))
    p['open_access'] = (work.get('open_access') or {}).get('is_oa')
    return _finish(p)

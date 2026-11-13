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


def from_scopus(entry):
    p = empty_paper()
    p['doi'] = entry.get('prism:doi')
    p['pii'] = entry.get('pii')
    p['scopus_id'] = (entry.get('dc:identifier') or '').replace('SCOPUS_ID:', '') or None
    p['eid'] = entry.get('eid')
    p['title'] = entry.get('dc:title')
    p['first_author'] = entry.get('dc:creator')
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
    p['url'] = f"https://doi.org/{p['doi']}" if p['doi'] else None
    p['proxy_url'] = proxy_url(p['doi'], p['pii'])
    return p

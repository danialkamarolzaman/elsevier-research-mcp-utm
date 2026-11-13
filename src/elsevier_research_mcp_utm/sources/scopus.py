import json
import time

from .. import cache, client, config, models

search_path = '/content/search/scopus'
abstract_path = '/content/abstract/doi/'
max_count = 25  # largest page Scopus allows without extra entitlement
sorts = {'citations': '-citedby-count', 'date': '-coverDate', 'relevance': 'relevancy'}
fields = ','.join([
    'dc:identifier', 'eid', 'dc:title', 'dc:creator', 'prism:publicationName', 'prism:volume',
    'prism:issueIdentifier', 'prism:pageRange', 'prism:coverDate', 'prism:doi', 'pii',
    'citedby-count', 'openaccessFlag',
])
blocked_for = 3600  # seconds to skip elsevier abstracts after a not-entitled answer
abstracts_blocked_until = 0.0


def search(query, year_from=None, year_to=None, sort='citations', count=25, start=0, use_cache=True):
    if sort not in sorts:
        raise ValueError(f'sort must be one of {sorted(sorts)}')
    params = {
        'query': query,
        'start': max(int(start), 0),
        'count': min(max(int(count), 1), max_count),
        'sort': sorts[sort],
        'field': fields,
    }
    if year_from or year_to:
        params['date'] = f'{year_from or 1900}-{year_to or 2100}'
    key = 'scopus_search:' + json.dumps(params, sort_keys=True)
    data = cache.get(key) if use_cache else None
    cached = data is not None
    if not cached:
        data = client.get_json(config.base_url + search_path, params)
        cache.put(key, data)
    results = data.get('search-results', {})
    # an empty result set comes back as one error entry
    entries = [e for e in results.get('entry', []) if 'error' not in e]
    papers = [models.from_scopus(e) for e in entries]
    return {
        'query': query,
        'total': int(results.get('opensearch:totalResults', 0) or 0),
        'start': params['start'],
        'count': len(papers),
        'cached': cached,
        'papers': papers,
    }


def abstract(doi):
    # returns (paper or None, note); paper has the elsevier abstract when entitled
    global abstracts_blocked_until
    doi = models.clean_doi(doi)
    if time.time() < abstracts_blocked_until:
        return None, 'elsevier abstracts not entitled on this network (skipped)'
    try:
        data = client.get_json(config.base_url + abstract_path + doi, {'view': 'META_ABS'})
    except client.ApiError as e:
        # 403 or 401 AUTHORIZATION_ERROR = not entitled; 401 AUTHENTICATION_ERROR = bad key, raise
        not_entitled = e.status == 403 or (e.status == 401 and e.code == 'AUTHORIZATION_ERROR')
        if not_entitled:
            abstracts_blocked_until = time.time() + blocked_for
            return None, str(e)
        if e.status == 404:
            return None, 'not in Scopus'
        raise
    core = data.get('abstracts-retrieval-response', {}).get('coredata', {})
    p = models.from_scopus(core)
    text = (core.get('dc:description') or '').strip()
    if text:
        p['abstract'], p['abstract_source'] = text, 'elsevier'
    return p, None

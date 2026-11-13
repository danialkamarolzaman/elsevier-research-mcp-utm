import json

from .. import cache, client, config, models

search_path = '/content/search/scopus'
max_count = 25  # largest page Scopus allows without extra entitlement
sorts = {'citations': '-citedby-count', 'date': '-coverDate', 'relevance': 'relevancy'}
fields = ','.join([
    'dc:identifier', 'eid', 'dc:title', 'dc:creator', 'prism:publicationName', 'prism:volume',
    'prism:issueIdentifier', 'prism:pageRange', 'prism:coverDate', 'prism:doi', 'pii',
    'citedby-count', 'openaccessFlag',
])


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

import time

from .. import cache, client, config, models

base_url = 'https://api.semanticscholar.org/graph/v1/paper'
min_gap = 1.1  # seconds, public S2 limit is about 1 request per second
last_call = 0.0


def abstract(doi, use_cache=True, sleep=time.sleep):
    global last_call
    doi = models.clean_doi(doi)
    key = 's2_abstract:' + doi
    if use_cache:
        hit = cache.get(key)
        if hit is not None:
            return hit.get('abstract')
    wait = last_call + min_gap - time.time()
    if wait > 0:
        sleep(wait)
    hdrs = {'x-api-key': config.semantic_scholar_key} if config.semantic_scholar_key else None
    try:
        data = client.get_public_json(f'{base_url}/DOI:{doi}', {'fields': 'abstract'}, hdrs)
    finally:
        last_call = time.time()
    text = (data or {}).get('abstract') or None
    cache.put(key, {'abstract': text})
    return text

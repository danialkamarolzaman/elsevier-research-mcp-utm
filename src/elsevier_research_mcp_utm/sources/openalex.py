from .. import cache, client, config, models

base_url = 'https://api.openalex.org'


def work(doi, use_cache=True):
    # full openalex record for a DOI, None if openalex does not know it
    doi = models.clean_doi(doi)
    key = 'openalex:' + doi
    if use_cache:
        hit = cache.get(key)
        if hit is not None:
            return hit or None  # {} = known miss
    params = {'mailto': config.openalex_mailto} if config.openalex_mailto else None
    data = client.get_public_json(f'{base_url}/works/doi:{doi}', params)
    cache.put(key, data or {})
    return data


def paper(doi):
    w = work(doi)
    if not w:
        return None
    p = models.from_openalex(w)
    text = models.abstract_from_inverted(w.get('abstract_inverted_index'))
    if text:
        p['abstract'], p['abstract_source'] = text, 'openalex'
    return p


def open_access(doi):
    w = work(doi)
    if not w:
        return None
    oa = w.get('open_access') or {}
    best = w.get('best_oa_location') or {}
    return {
        'is_oa': bool(oa.get('is_oa')),
        'oa_status': oa.get('oa_status'),  # gold, green, hybrid, bronze, diamond, closed
        'pdf_url': best.get('pdf_url'),
        'landing_url': best.get('landing_page_url') or oa.get('oa_url'),
        'license': best.get('license'),
        'version': best.get('version'),  # publishedVersion, acceptedVersion, submittedVersion
        'title': w.get('title') or w.get('display_name'),
    }

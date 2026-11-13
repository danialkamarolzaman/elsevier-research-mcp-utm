from . import cache, client, models
from .sources import openalex, scopus, semanticscholar

# abstract chain: elsevier (when entitled) -> openalex -> semantic scholar
miss_days = 1  # re-try papers without an abstract after this many days


def get_abstract(doi):
    doi = models.clean_doi(doi)
    if not doi:
        raise ValueError('a DOI is required')
    key = 'abstract:' + doi
    hit = cache.get(key)
    if hit and (hit['paper']['abstract'] or cache.get(key, max_days=miss_days)):
        return {**hit, 'cached': True}
    notes = []
    paper = models.empty_paper()
    paper['doi'] = doi

    # 1 elsevier
    try:
        els, note = scopus.abstract(doi)
    except client.ApiError as e:
        els, note = None, str(e)
    if note:
        notes.append(f'elsevier: {note}')
    if els:
        paper = models.merge(els, paper)

    # 2 openalex (also fills metadata)
    try:
        oa = openalex.paper(doi)
        if oa:
            paper = models.merge(paper, oa)
        else:
            notes.append('openalex: DOI not found')
    except client.ApiError as e:
        notes.append(f'openalex: {e}')

    # 3 semantic scholar
    if not paper['abstract']:
        try:
            text = semanticscholar.abstract(doi)
            if text:
                paper['abstract'], paper['abstract_source'] = text, 'semanticscholar'
        except client.ApiError as e:
            notes.append(f'semanticscholar: {e}')

    if not paper['abstract']:
        notes.append('no free source has this abstract (Elsevier withholds its abstracts from OpenAlex and '
                     'Semantic Scholar). Open proxy_url in your browser, or use campus Wi-Fi / an insttoken.')
    paper = models.merge(paper, {})  # refresh url / proxy_url
    result = {'paper': paper, 'notes': notes}
    cache.put(key, result)
    return {**result, 'cached': False}


def find_open_access(doi):
    doi = models.clean_doi(doi)
    if not doi:
        raise ValueError('a DOI is required')
    info = openalex.open_access(doi)
    if info is None:
        return {'doi': doi, 'found': False, 'is_oa': None, 'proxy_url': models.proxy_url(doi),
                'notes': ['openalex: DOI not found']}
    return {'doi': doi, 'found': True, **info, 'proxy_url': models.proxy_url(doi), 'source': 'openalex'}

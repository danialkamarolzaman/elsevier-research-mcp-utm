import os

from . import abstracts, cache, client, config, limits, models, naming
from .sources import openalex, sciencedirect

# full text and PDFs. every institutional fetch goes through limits:
# entitlement check (free) -> one-at-a-time slot -> limits.check -> wait for gap -> fetch -> log bytes
busy = 'another full-text fetch (e.g. the background worker) is still running; try again in a few minutes'


def _refused(reason, doi=None, pii=None, **extra):
    return {'ok': False, 'doi': doi, 'pii': pii, 'reason': reason,
            'proxy_url': models.proxy_url(doi, pii), 'limits': limits.usage(), **extra}


def _limit_refusal(doi, pii):
    ok, reason, nxt = limits.check()
    if ok:
        return None
    return _refused(reason, doi, pii, next_allowed=limits.describe_time(nxt))


# ---------------- full text ----------------
def get_fulltext(doi=None, pii=None, start=0, max_chars=40000):
    doi = models.clean_doi(doi)
    if not doi and not pii:
        raise ValueError('give a DOI or a PII')
    key = 'fulltext:' + (pii or doi)
    hit = cache.get(key, max_days=3650)  # paging through a cached text is free
    if hit is None:
        ok, note = sciencedirect.entitled(doi, pii)
        if not ok:
            reason = f'no full-text access: {note}. Try find_open_access, or open proxy_url.'
            return _refused(reason, doi, pii)
        with limits.fetch_slot() as got:
            if not got:
                return _refused(busy, doi, pii)
            refusal = _limit_refusal(doi, pii)
            if refusal:
                return refusal
            limits.wait_for_gap()
            try:
                text, nbytes = sciencedirect.fulltext(doi, pii)
            except client.ApiError as e:
                return _refused(str(e), doi, pii)
            cache.log_fetch(pii or doi, 'text', nbytes)
        hit = {'text': text}
        cache.put(key, hit)
        cached = False
    else:
        cached = True
    text = hit['text']
    start = max(int(start), 0)
    max_chars = min(max(int(max_chars), 1000), 100000)
    part = text[start:start + max_chars]
    end = start + len(part)
    return {'ok': True, 'doi': doi, 'pii': pii, 'cached': cached, 'total_chars': len(text),
            'start': start, 'end': end, 'more': end < len(text), 'text': part, 'limits': limits.usage()}


# ---------------- pdf ----------------
def _saved_path(doi):
    # file already downloaded for this DOI (tracked in cache, file must still exist)
    hit = cache.get('pdf_path:' + doi, max_days=3650)
    if hit and os.path.exists(hit['path']):
        return hit['path']
    return None


def _target_path(doi, filename):
    os.makedirs(config.download_dir, exist_ok=True)
    paper = abstracts.get_abstract(doi)['paper']  # metadata for name and pii, cached
    if filename:
        name = naming.clean(filename)
        name = name if name.lower().endswith('.pdf') else name + '.pdf'
    else:
        name = naming.pdf_filename(paper)
    path = os.path.join(config.download_dir, name)
    if os.path.exists(path):
        # same name, different paper: keep both, add the DOI
        stem = name[:-4]
        path = os.path.join(config.download_dir, naming.clean(f"{stem} ({doi.replace('/', '_')})") + '.pdf')
    return path, paper


def _try_open_access(doi, path):
    info = openalex.open_access(doi)
    if not info or not info.get('is_oa') or not info.get('pdf_url'):
        return None, 'no open-access PDF listed'
    try:
        # open-access copies do not use the institution subscription, so they are not counted
        nbytes = client.stream_to_file(info['pdf_url'], path, 200_000_000, elsevier=False)
        return {'source': 'open_access', 'bytes': nbytes, 'license': info.get('license'),
                'version': info.get('version')}, None
    except (client.ApiError, client.TooLarge) as e:
        return None, f'open-access download failed: {e}'


def download_pdf(doi, filename=None, prefer_open_access=True):
    doi = models.clean_doi(doi)
    if not doi:
        raise ValueError('a DOI is required')
    saved = _saved_path(doi)
    if saved:
        return {'ok': True, 'doi': doi, 'path': saved, 'source': 'already_downloaded',
                'mb': round(os.path.getsize(saved) / 1e6, 2), 'counted': False, 'limits': limits.usage()}
    path, paper = _target_path(doi, filename)
    notes = []
    if prefer_open_access:
        got, note = _try_open_access(doi, path)
        if got:
            cache.put('pdf_path:' + doi, {'path': path})
            return {'ok': True, 'doi': doi, 'path': path, 'mb': round(got['bytes'] / 1e6, 2),
                    **got, 'counted': False, 'limits': limits.usage()}
        notes.append(note)

    pii = (paper or {}).get('pii')
    ok, note = sciencedirect.entitled(doi, pii)
    if not ok:
        return _refused(f'no institutional access: {note}', doi, pii, notes=notes)
    with limits.fetch_slot() as free:
        if not free:
            return _refused(busy, doi, pii, notes=notes)
        refusal = _limit_refusal(doi, pii)
        if refusal:
            return {**refusal, 'notes': notes}
        limits.wait_for_gap()
        budget = int(limits.remaining_mb() * 1e6)
        try:
            nbytes = sciencedirect.pdf_to_file(path, budget, doi, pii)
        except (client.ApiError, client.TooLarge) as e:
            got = getattr(e, 'received', 0)
            if got:
                cache.log_fetch(doi, 'aborted', got)  # bytes did cross the institution link
            return _refused(str(e), doi, pii, notes=notes)
        cache.log_fetch(doi, 'pdf', nbytes)
    cache.put('pdf_path:' + doi, {'path': path})
    return {'ok': True, 'doi': doi, 'pii': pii, 'path': path, 'source': 'elsevier',
            'mb': round(nbytes / 1e6, 2), 'counted': True, 'notes': notes, 'limits': limits.usage()}


def download_batch(dois, prefer_open_access=True):
    dois = [d for d in (dois or []) if models.clean_doi(d)]
    if not dois:
        raise ValueError('give at least one DOI')
    if len(dois) > config.max_articles_per_window:
        raise ValueError(f'at most {config.max_articles_per_window} DOIs per batch (institution rule)')
    results = []
    for doi in dois:
        try:
            r = download_pdf(doi, prefer_open_access=prefer_open_access)
        except (client.ApiError, ValueError) as e:
            r = {'ok': False, 'doi': doi, 'reason': str(e)}
        results.append(r)
        if not r['ok'] and ('limit' in r.get('reason', '')):
            break  # stop at the first limit hit, never queue in the background
    done = [r['doi'] for r in results]
    return {'results': results, 'not_attempted': [d for d in dois if d not in done],
            'limits': limits.usage()}

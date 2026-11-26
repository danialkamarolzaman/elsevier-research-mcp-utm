import os
import shutil
import time

from . import cache, config, fetch, fetchqueue, limits, models

# browser-assisted fetch of closed papers (UTM: the only way to Elsevier full text).
# the USER logs in to EZproxy in their own browser; Claude (e.g. Claude in Chrome) opens one paper at a
# time. these two steps keep the library limits and file the PDF. nothing here logs in or loads web pages.
kind = 'browser'
pending_minutes = 30  # a started paper may be finished within this time without counting again
wait_step = 2  # seconds between looks at the downloads folder


def _pending(doi):
    hit = cache.get('browser_start:' + doi, max_days=1)
    if hit and time.time() - hit['ts'] < pending_minutes * 60:
        return hit
    return None


def start(doi):
    doi = models.clean_doi(doi)
    if not doi:
        raise ValueError('a DOI is required')
    saved = fetch._saved_path(doi)
    if saved:
        return {'ok': True, 'doi': doi, 'already_saved': saved, 'limits': limits.usage()}
    path, paper = fetch._target_path(doi, None)
    open_url = paper.get('proxy_url') or f'https://doi.org/{doi}'
    hit = _pending(doi)
    if not hit:
        with limits.fetch_slot() as free:
            if not free:
                return {'ok': False, 'doi': doi, 'reason': fetch.busy, 'limits': limits.usage()}
            ok, reason, nxt = limits.check()
            if not ok:
                return {'ok': False, 'doi': doi, 'reason': reason, 'next_allowed': limits.describe_time(nxt),
                        'limits': limits.usage()}
            limits.wait_for_gap()
            # counted now, so the worker and other tools see it; the size is filled in by finish()
            hit = {'ts': time.time()}
            cache.log_fetch(doi, kind, 0, hit['ts'])
            cache.put('browser_start:' + doi, hit)
    return {'ok': True, 'doi': doi, 'title': paper.get('title'), 'open_url': open_url,
            'save_as': os.path.basename(path), 'downloads_dir': config.browser_downloads_dir,
            'finish_within_minutes': pending_minutes, 'limits': limits.usage()}


def _is_pdf(path):
    try:
        with open(path, 'rb') as f:
            return f.read(5) == b'%PDF-'
    except OSError:
        return False


def _newest_pdf(since):
    folder = config.browser_downloads_dir
    try:
        names = os.listdir(folder)
    except OSError:
        return None
    found = []
    for name in names:
        p = os.path.join(folder, name)
        if name.lower().endswith('.pdf') and os.path.isfile(p) and os.path.getmtime(p) >= since - 2:
            found.append((os.path.getmtime(p), p))
    return max(found)[1] if found else None


def finish(doi, path=None, wait_seconds=60, sleep=None):
    sleep = sleep or time.sleep
    doi = models.clean_doi(doi)
    if not doi:
        raise ValueError('a DOI is required')
    hit = cache.get('browser_start:' + doi, max_days=1)
    if not hit or not hit['ts']:
        raise ValueError('call browser_fetch_start for this DOI first')
    if not path:
        # wait for the browser to finish writing the file (Chrome keeps .crdownload until done)
        waited = 0
        while True:
            path = _newest_pdf(hit['ts'])
            if path or waited >= wait_seconds:
                break
            sleep(wait_step)
            waited += wait_step
        if not path:
            return {'ok': False, 'doi': doi, 'reason': f'no new PDF in {config.browser_downloads_dir} yet. '
                    'Check the download finished, or give its path.'}
    if not _is_pdf(path):
        return {'ok': False, 'doi': doi, 'reason': f'NOT_PDF: {path} is not a PDF (a login or web page?)'}
    nbytes = os.path.getsize(path)
    target, _ = fetch._target_path(doi, None)
    shutil.move(path, target)
    cache.set_fetch_bytes(doi, kind, hit['ts'], nbytes)
    cache.put('pdf_path:' + doi, {'path': target})
    cache.put('browser_start:' + doi, {'ts': 0})
    if any(item['doi'] == doi for item in fetchqueue.items()):
        fetchqueue.update(doi, 'done', 'saved via browser', target)
    return {'ok': True, 'doi': doi, 'path': target, 'mb': round(nbytes / 1e6, 2), 'counted': True,
            'limits': limits.usage()}

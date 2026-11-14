import os
import time

from . import abstracts, cache, client, config, fetch, fetchqueue, limits, naming
from .sources import sciencedirect

# background worker: works through the queue one paper at a time, headless, official APIs only.
# open access first (not counted), then Elsevier when entitled, always inside the institution limits.
# it never logs in to EZproxy or fetches web pages: papers it cannot get go to a list you open yourself.
max_tries = 3
nap = 30  # seconds per sleep step, so the heartbeat stays fresh


def sleep_until(ts, say):
    say(f'  waiting until {limits.describe_time(ts)} ...')
    while True:
        left = ts - time.time()
        if left <= 0:
            return
        fetchqueue.beat()
        time.sleep(min(nap, left))


def _is_pdf(path):
    try:
        with open(path, 'rb') as f:
            return f.read(5) == b'%PDF-'
    except OSError:
        return False


def expected_path(doi):
    paper = abstracts.get_abstract(doi)['paper']  # cached
    return os.path.join(config.download_dir, naming.pdf_filename(paper)), paper


def pick_up_saved(say):
    # papers the user saved by hand under the suggested name count as done
    for item in fetchqueue.items('manual') + fetchqueue.items('blocked'):
        path = item['path'] or expected_path(item['doi'])[0]
        if path and _is_pdf(path):
            cache.put('pdf_path:' + item['doi'], {'path': path})
            fetchqueue.update(item['doi'], 'done', 'saved by you', path)
            say(f"  picked up {os.path.basename(path)}")


def write_manual_list():
    rows = fetchqueue.items('manual') + fetchqueue.items('blocked')
    path = fetchqueue.manual_list_path()
    if not rows:
        if os.path.exists(path):
            os.remove(path)
        return None
    lines = ['# Papers to open yourself', '',
             'The background worker cannot fetch these headless. Open each link in your browser, one at',
             'a time, log in to the library if asked, and save the PDF into this folder under the name',
             'given. The worker picks them up on its next pass. Keep to the library rules: at most '
             f'{config.max_articles_per_window} articles and {config.max_mb_per_window} MB per '
             f'{config.window_minutes} minutes, no multiple tabs at once.', '',
             '| # | Paper | Why | Open | Save as |', '|---|---|---|---|---|']
    for n, item in enumerate(rows, 1):
        path_, paper = expected_path(item['doi'])
        title = (paper.get('title') or item['doi']).replace('|', '/')
        link = paper.get('proxy_url') or paper.get('url') or f"https://doi.org/{item['doi']}"
        why = 'waiting for campus Wi-Fi or an insttoken' if item['status'] == 'blocked' else item['note']
        lines.append(f"| {n} | {title} ({item['doi']}) | {why} | [link]({link}) | "
                     f"`{os.path.basename(path_)}` |")
    os.makedirs(config.download_dir, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    return path


def process(item, say):
    doi = item['doi']
    try:
        r = fetch.download_pdf(doi)
    except (client.ApiError, ValueError) as e:
        r = {'ok': False, 'reason': str(e)}
    if r['ok']:
        fetchqueue.update(doi, 'done', r.get('source', ''), r.get('path'))
        say(f"  done  {doi}  ({r.get('source')}, {r.get('mb')} MB{', counted' if r.get('counted') else ''})")
        return 'done'
    reason = r.get('reason', '')
    if 'next_allowed' in r:
        return 'limit'
    if fetch.busy in reason:
        return 'busy'
    if 'not on ScienceDirect' in reason:
        fetchqueue.update(doi, 'manual', 'not open access and not on ScienceDirect', expected_path(doi)[0])
        say(f'  manual {doi}  (other publisher, see the list)')
        return 'manual'
    if reason.startswith('no institutional access'):
        fetchqueue.update(doi, 'blocked', 'no access on this network', expected_path(doi)[0])
        say(f'  blocked {doi}  (needs campus Wi-Fi or an insttoken)')
        return 'blocked'
    tries = (item['tries'] or 0) + 1
    note = client.redact(reason)[:300]
    fetchqueue.update(doi, 'failed' if tries >= max_tries else 'waiting', note, tries=tries)
    say(f'  error {doi}  try {tries}/{max_tries}: {client.redact(reason)[:150]}')
    return 'error'


def access_back():
    # one free entitlement check on a blocked paper; if it passes, retry all blocked papers
    blocked = fetchqueue.items('blocked')
    if not blocked:
        return False
    doi = blocked[0]['doi']
    paper = abstracts.get_abstract(doi)['paper']
    ok, _ = sciencedirect.entitled(doi, paper.get('pii'))
    if ok:
        for item in blocked:
            fetchqueue.update(item['doi'], 'waiting', 'access found')
    return ok


def summary():
    c = fetchqueue.status()['counts']
    return ', '.join(f'{k} {v}' for k, v in c.items() if v)


def run(say=print, until_blocked=False):
    # until_blocked=True: stop when only blocked / manual papers are left instead of re-checking forever
    if fetchqueue.worker_active():
        say('Another worker is already running. Only one may run at a time '
            '(library rule: one download at once).')
        return 1
    fetchqueue.beat()
    if config.source('ERM_DOWNLOAD_DIR') == 'none' and fetchqueue.get_meta('download_dir'):
        config.download_dir = fetchqueue.get_meta('download_dir')  # same folder the papers were queued for
    say(f'Download folder: {config.download_dir}')
    say(f'elsevier-research-mcp-utm worker: {summary() or "queue is empty"}')
    say(f'Limits: {config.max_articles_per_window} articles / {config.max_mb_per_window} MB per '
        f'{config.window_minutes} min, {config.max_articles_per_day} per day, '
        f'{config.min_delay_seconds} s apart. '
        'Ctrl+C stops; it is safe to start again later.')
    next_recheck = time.time() + config.recheck_minutes * 60
    try:
        while True:
            fetchqueue.beat()
            pick_up_saved(say)
            waiting = fetchqueue.items('waiting')
            if waiting:
                result = process(waiting[0], say)
                if result == 'limit':
                    ok, reason, nxt = limits.check()
                    say(f'  {reason}')
                    sleep_until(nxt, say)
                elif result in ('busy', 'error'):
                    sleep_until(time.time() + 60, say)
                continue
            write_manual_list()
            if fetchqueue.items('blocked') and not until_blocked:
                if time.time() >= next_recheck:
                    next_recheck = time.time() + config.recheck_minutes * 60
                    if access_back():
                        say('Access found (campus network or insttoken), fetching the blocked papers.')
                        continue
                say(f'{len(fetchqueue.items("blocked"))} paper(s) wait for campus Wi-Fi or an insttoken; '
                    f'list: {fetchqueue.manual_list_path()}')
                sleep_until(next_recheck, say)
                continue
            path = write_manual_list()
            say(f'Finished: {summary()}.' + (f' Open the rest yourself: {path}' if path else ''))
            return 0
    except KeyboardInterrupt:
        say(f'\nStopped. {summary()}. Start again any time; nothing is lost.')
        return 0
    finally:
        fetchqueue.release()


start_command = ('uvx --from git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm '
                 'elsevier-research-mcp-utm worker')

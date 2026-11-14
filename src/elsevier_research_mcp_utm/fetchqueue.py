import os
import time

from . import cache, config, limits, models

# papers waiting for the background worker, kept in the cache database so restarts lose nothing
# status: waiting -> done | blocked (no access on this network yet) | manual (open it yourself) | failed
statuses = ('waiting', 'done', 'blocked', 'manual', 'failed')
heartbeat_seconds = 120  # a worker that has not checked in for this long is gone
max_add = 200
manual_list_name = '_open_manually.md'


def connect():
    db = cache.connect()
    db.execute('create table if not exists queue (doi text primary key, added real, status text, '
               'note text, path text, tries integer, updated real)')
    db.execute('create table if not exists worker (id integer primary key, ts real)')
    db.execute('create table if not exists queue_meta (key text primary key, value text)')
    return db


def get_meta(key):
    with connect() as db:
        row = db.execute('select value from queue_meta where key = ?', (key,)).fetchone()
    return row[0] if row else None


def add(dois):
    clean = []
    for d in dois or []:
        d = models.clean_doi(d)
        if d and d not in clean:
            clean.append(d)
    if not clean:
        raise ValueError('give at least one DOI')
    if len(clean) > max_add:
        raise ValueError(f'at most {max_add} DOIs per call, split the list')
    now = time.time()
    added = []
    with connect() as db:
        # the worker runs from another folder; remember where these papers should go
        db.execute("insert or replace into queue_meta values ('download_dir', ?)", (config.download_dir,))
        for d in clean:
            sql = "insert or ignore into queue values (?, ?, 'waiting', '', '', 0, ?)"
            cur = db.execute(sql, (d, now, now))
            if cur.rowcount:
                added.append(d)
            else:
                # re-queue a paper that failed earlier; done / waiting / blocked stay as they are
                db.execute("update queue set status = 'waiting', tries = 0, updated = ? "
                           "where doi = ? and status = 'failed'", (now, d))
    return {'added': added, 'already_queued': [d for d in clean if d not in added]}


def items(status=None):
    sql = 'select doi, status, note, path, tries, added, updated from queue'
    args = ()
    if status:
        sql += ' where status = ?'
        args = (status,)
    with connect() as db:
        rows = db.execute(sql + ' order by added, doi', args).fetchall()
    keys = ('doi', 'status', 'note', 'path', 'tries', 'added', 'updated')
    return [dict(zip(keys, r)) for r in rows]


def update(doi, status, note='', path=None, tries=None):
    with connect() as db:
        db.execute('update queue set status = ?, note = ?, path = coalesce(?, path), '
                   'tries = coalesce(?, tries), updated = ? where doi = ?',
                   (status, note, path, tries, time.time(), doi))


def remove(dois):
    with connect() as db:
        for d in dois:
            db.execute('delete from queue where doi = ?', (models.clean_doi(d),))


# ---------------- worker heartbeat: only one worker at a time ----------------
def beat():
    with connect() as db:
        db.execute('insert or replace into worker values (1, ?)', (time.time(),))


def release():
    with connect() as db:
        db.execute('delete from worker')


def worker_active(now=None):
    with connect() as db:
        row = db.execute('select ts from worker where id = 1').fetchone()
    return bool(row) and (now or time.time()) - row[0] < heartbeat_seconds


def manual_list_path():
    return os.path.join(config.download_dir, manual_list_name)


def status():
    rows = items()
    counts = {s: 0 for s in statuses}
    for r in rows:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    ok, reason, nxt = limits.check()
    return {
        'counts': counts,
        'total': len(rows),
        'worker_running': worker_active(),
        'next_institutional_fetch': 'now' if ok else f'{limits.describe_time(nxt)} ({reason})',
        'limits': limits.usage(),
        'manual_list': manual_list_path() if counts['manual'] or counts['blocked'] else None,
        'papers': [{k: r[k] for k in ('doi', 'status', 'note', 'path')} for r in rows[:200]],
    }

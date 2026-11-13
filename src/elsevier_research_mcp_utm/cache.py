import json
import os
import sqlite3
import time

from . import config


def connect():
    os.makedirs(config.cache_dir, exist_ok=True)
    db = sqlite3.connect(os.path.join(config.cache_dir, 'cache.sqlite'))
    db.execute('create table if not exists responses (key text primary key, ts real, body text)')
    db.execute('create table if not exists fetch_log (ts real, doi text, kind text, bytes integer)')
    return db


# ---------------- response cache ----------------
def get(key, max_days=None):
    max_days = config.cache_days if max_days is None else max_days
    with connect() as db:
        row = db.execute('select ts, body from responses where key = ?', (key,)).fetchone()
    if not row or time.time() - row[0] > max_days * 86400:
        return None
    return json.loads(row[1])


def put(key, value):
    with connect() as db:
        db.execute('insert or replace into responses values (?, ?, ?)', (key, time.time(), json.dumps(value)))


# ---------------- full-text fetch log (for limits) ----------------
def log_fetch(doi, kind, nbytes, ts=None):
    with connect() as db:
        db.execute('insert into fetch_log values (?, ?, ?, ?)', (ts or time.time(), doi, kind, int(nbytes)))


def fetches_since(ts):
    with connect() as db:
        sql = 'select ts, doi, kind, bytes from fetch_log where ts >= ? order by ts'
        return db.execute(sql, (ts,)).fetchall()

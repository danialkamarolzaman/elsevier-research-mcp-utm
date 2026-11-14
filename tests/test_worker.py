import os
import time

import pytest

from elsevier_research_mcp_utm import config, fetch, fetchqueue, limits, server, worker


class Clock:
    # fake time: sleeping moves the clock instead of waiting
    def __init__(self):
        self.now = 1_800_000_000.0
        self.slept = []

    def time(self):
        return self.now

    def sleep(self, s):
        self.slept.append(s)
        self.now += s


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(worker.time, 'time', c.time)
    monkeypatch.setattr(worker.time, 'sleep', c.sleep)
    return c


@pytest.fixture(autouse=True)
def papers(monkeypatch):
    # invented metadata, no network
    def get_abstract(doi):
        return {'paper': {'doi': doi, 'title': f'Paper {doi[-1]}', 'first_author': 'Tan A.', 'year': '2024',
                          'proxy_url': f'https://ezproxy.utm.my/login?url=https://doi.org/{doi}'}}
    monkeypatch.setattr(worker.abstracts, 'get_abstract', get_abstract)
    monkeypatch.setattr(config, 'sources', {})


def fake_downloads(monkeypatch, answers):
    # answers: doi -> list of results returned one after another
    calls = []

    def download_pdf(doi, filename=None, prefer_open_access=True):
        calls.append(doi)
        return answers[doi].pop(0)
    monkeypatch.setattr(worker.fetch, 'download_pdf', download_pdf)
    return calls


ok_oa = {'ok': True, 'source': 'open_access', 'mb': 1.2, 'counted': False, 'path': 'x.pdf'}
no_access = {'ok': False, 'reason': 'no institutional access: not entitled to this article'}
other_publisher = {'ok': False, 'reason': 'no institutional access: not on ScienceDirect'}
limit_hit = {'ok': False, 'reason': 'limit: 5/5 articles in 15 min', 'next_allowed': 'later'}


# ---------------- queue ----------------
def test_add_dedupes_and_requeues_failed():
    r = fetchqueue.add(['10.1/a', 'doi:10.1/A', 'https://doi.org/10.1/b'])
    assert r == {'added': ['10.1/a', '10.1/b'], 'already_queued': []}
    fetchqueue.update('10.1/a', 'failed', 'x', tries=3)
    fetchqueue.update('10.1/b', 'done', 'open_access', 'b.pdf')
    r = fetchqueue.add(['10.1/a', '10.1/b'])
    assert r['already_queued'] == ['10.1/a', '10.1/b']
    states = {i['doi']: i['status'] for i in fetchqueue.items()}
    assert states == {'10.1/a': 'waiting', '10.1/b': 'done'}
    assert fetchqueue.get_meta('download_dir') == config.download_dir
    with pytest.raises(ValueError):
        fetchqueue.add([])
    with pytest.raises(ValueError):
        fetchqueue.add([f'10.1/{i}' for i in range(201)])


def test_queue_tools_tell_user_to_start_worker():
    r = server.queue_papers(['10.1/a'])
    assert r['added'] == ['10.1/a'] and not r['worker_running']
    assert r['start_worker'].endswith('elsevier-research-mcp-utm worker')
    s = server.queue_status()
    assert s['counts']['waiting'] == 1 and 'start_worker' in s
    fetchqueue.beat()
    assert 'start_worker' not in server.queue_status()


# ---------------- worker ----------------
def test_works_through_queue_and_lists_the_rest(monkeypatch, clock):
    fetchqueue.add(['10.1/a', '10.1/b', '10.1/c'])
    answers = {'10.1/a': [ok_oa], '10.1/b': [no_access], '10.1/c': [other_publisher]}
    calls = fake_downloads(monkeypatch, answers)
    out = []
    assert worker.run(say=out.append, until_blocked=True) == 0
    assert calls == ['10.1/a', '10.1/b', '10.1/c']  # one at a time, in order
    states = {i['doi']: i['status'] for i in fetchqueue.items()}
    assert states == {'10.1/a': 'done', '10.1/b': 'blocked', '10.1/c': 'manual'}
    listing = open(fetchqueue.manual_list_path(), encoding='utf-8').read()
    assert 'ezproxy.utm.my/login?url=https://doi.org/10.1/b' in listing
    assert '`Tan 2024 - Paper c.pdf`' in listing and '10.1/a' not in listing
    assert not fetchqueue.worker_active()  # heartbeat released


def test_sleeps_until_limit_window_frees(monkeypatch, clock):
    fetchqueue.add(['10.1/a'])
    fake_downloads(monkeypatch, {'10.1/a': [limit_hit, ok_oa]})
    monkeypatch.setattr(worker.limits, 'check', lambda now=None: (False, 'limit: 5/5', clock.now + 900))
    out = []
    worker.run(say=out.append, until_blocked=True)
    assert sum(clock.slept) >= 900
    assert all(s <= worker.nap for s in clock.slept)  # short naps keep the heartbeat fresh
    assert fetchqueue.items('done')[0]['doi'] == '10.1/a'


def test_errors_retry_then_fail(monkeypatch, clock):
    fetchqueue.add(['10.1/a'])
    boom = {'ok': False, 'reason': 'HTTP 500: testkey123 broke'}
    fake_downloads(monkeypatch, {'10.1/a': [boom, boom, boom]})
    out = []
    worker.run(say=out.append, until_blocked=True)
    item = fetchqueue.items()[0]
    assert item['status'] == 'failed' and item['tries'] == 3
    assert 'testkey123' not in item['note'] and not any('testkey123' in str(o) for o in out)


def test_only_one_worker(clock):
    fetchqueue.beat()
    out = []
    assert worker.run(say=out.append) == 1
    assert 'already running' in out[0]


def test_blocked_papers_start_when_access_appears(monkeypatch, clock):
    fetchqueue.add(['10.1/a'])
    fake_downloads(monkeypatch, {'10.1/a': [no_access, ok_oa]})
    checks = []

    def entitled(doi, pii):
        checks.append(clock.now)
        return True, None  # e.g. the laptop is now on campus Wi-Fi
    monkeypatch.setattr(worker.sciencedirect, 'entitled', entitled)
    out = []
    worker.run(say=out.append)  # not until_blocked: it waits and re-checks
    assert len(checks) == 1 and sum(clock.slept) >= config.recheck_minutes * 60
    assert fetchqueue.items()[0]['status'] == 'done'
    assert any('Access found' in str(o) for o in out)


def test_picks_up_pdf_saved_by_hand(monkeypatch, clock):
    fetchqueue.add(['10.1/c'])
    fake_downloads(monkeypatch, {'10.1/c': [other_publisher]})
    worker.run(say=lambda s: None, until_blocked=True)
    path = os.path.join(config.download_dir, 'Tan 2024 - Paper c.pdf')
    with open(path, 'wb') as f:
        f.write(b'%PDF-1.7 fake')
    worker.run(say=lambda s: None, until_blocked=True)
    item = fetchqueue.items()[0]
    assert item['status'] == 'done' and item['path'] == path
    assert not os.path.exists(fetchqueue.manual_list_path())


def test_uses_download_dir_from_queue_time(monkeypatch, clock, tmp_path):
    monkeypatch.setattr(config, 'download_dir', str(tmp_path / 'thesis papers'))
    fetchqueue.add(['10.1/a'])
    monkeypatch.setattr(config, 'download_dir', str(tmp_path / 'somewhere else'))
    fake_downloads(monkeypatch, {'10.1/a': [ok_oa]})
    worker.run(say=lambda s: None, until_blocked=True)
    assert config.download_dir == str(tmp_path / 'thesis papers')


# ---------------- one fetch at a time across processes ----------------
def test_fetch_slot_is_exclusive_and_recovers_from_crash():
    with limits.fetch_slot() as first:
        assert first
        with limits.fetch_slot(timeout=0) as second:
            assert not second
    with limits.fetch_slot(timeout=0) as again:
        assert again
    lock = os.path.join(config.cache_dir, 'fetch.lock')
    open(lock, 'w').close()
    old = time.time() - limits.slot_stale_seconds - 10
    os.utime(lock, (old, old))  # left over from a crash
    with limits.fetch_slot(timeout=0) as got:
        assert got


def test_download_refused_while_another_fetch_runs(monkeypatch):
    monkeypatch.setattr(fetch, '_saved_path', lambda doi: None)
    target = os.path.join(config.download_dir, 'x.pdf')
    monkeypatch.setattr(fetch, '_target_path', lambda doi, fn: (target, {}))
    monkeypatch.setattr(fetch.sciencedirect, 'entitled', lambda doi, pii: (True, None))
    monkeypatch.setattr(fetch.limits, 'fetch_slot', lambda: _busy_slot())
    r = fetch.download_pdf('10.1/a', prefer_open_access=False)
    assert not r['ok'] and r['reason'] == fetch.busy


class _busy_slot:
    def __enter__(self):
        return False

    def __exit__(self, *a):
        return False

import time

from elsevier_research_mcp_utm import cache


def test_put_get_roundtrip():
    cache.put('k', {'a': [1, 2]})
    assert cache.get('k') == {'a': [1, 2]}


def test_missing_key():
    assert cache.get('nope') is None


def test_expired_entry(monkeypatch):
    cache.put('old', {'x': 1})
    real = time.time()
    monkeypatch.setattr(cache.time, 'time', lambda: real + 31 * 86400)
    assert cache.get('old') is None
    assert cache.get('old', max_days=60) == {'x': 1}


def test_fetch_log():
    now = time.time()
    cache.log_fetch('10.1/a', 'pdf', 1000, ts=now - 100)
    cache.log_fetch('10.1/b', 'text', 2000, ts=now)
    rows = cache.fetches_since(now - 50)
    assert [r[1] for r in rows] == ['10.1/b']

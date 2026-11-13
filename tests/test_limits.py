import time

from elsevier_research_mcp_utm import cache, limits

# fixed midday time so the day boundary never interferes
noon = time.mktime((2026, 11, 13, 12, 0, 0, 0, 0, -1))


def log(n, minutes_ago=1, mb=1):
    for i in range(n):
        cache.log_fetch(f'10.1/{minutes_ago}-{i}', 'pdf', mb * 1_000_000, ts=noon - minutes_ago * 60 - i)


def test_empty_is_ok():
    ok, reason, _ = limits.check(noon)
    assert ok and reason == 'ok'


def test_four_articles_still_ok():
    log(4)
    assert limits.check(noon)[0]


def test_five_articles_in_window_blocks():
    log(5)
    ok, reason, nxt = limits.check(noon)
    assert not ok
    assert '5/5 articles' in reason
    assert nxt > noon


def test_old_articles_leave_the_window():
    log(5, minutes_ago=20)
    assert limits.check(noon)[0]


def test_megabytes_block():
    log(2, mb=60)
    ok, reason, _ = limits.check(noon)
    assert not ok and 'MB' in reason
    assert limits.remaining_mb(noon) == 0.0


def test_remaining_mb():
    log(1, mb=30)
    assert limits.remaining_mb(noon) == 70.0


def test_daily_limit():
    for hour in range(1, 5):
        log(5, minutes_ago=hour * 60)  # 20 articles spread over the morning
    ok, reason, _ = limits.check(noon)
    assert not ok and 'daily' in reason


def test_gap_waits_for_min_delay():
    cache.log_fetch('10.1/x', 'pdf', 1, ts=noon - 3)
    slept = []
    waited = limits.wait_for_gap(noon, sleep=slept.append)
    assert round(waited) == 7 and round(slept[0]) == 7


def test_no_gap_needed():
    cache.log_fetch('10.1/x', 'pdf', 1, ts=noon - 60)
    assert limits.wait_for_gap(noon, sleep=lambda s: None) == 0.0

import time

from . import cache, config

# guards full-text / PDF fetches so an institution's e-resource rules are kept
# (UTM Library: max 5 articles at once, max 100 MB in 15 min)


def _day_start(now):
    t = time.localtime(now)
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))


def usage(now=None):
    now = now or time.time()
    window_start = now - config.window_minutes * 60
    day_rows = cache.fetches_since(_day_start(now))
    window_rows = [r for r in day_rows if r[0] >= window_start]
    # window can reach back into yesterday
    if window_start < _day_start(now):
        window_rows = cache.fetches_since(window_start)
    last = cache.fetches_since(now - 86400)
    return {
        'window_minutes': config.window_minutes,
        'window_articles': len(window_rows),
        'window_mb': round(sum(r[3] for r in window_rows) / 1e6, 2),
        'day_articles': len(day_rows),
        'max_articles_per_window': config.max_articles_per_window,
        'max_mb_per_window': config.max_mb_per_window,
        'max_articles_per_day': config.max_articles_per_day,
        'last_fetch_ts': last[-1][0] if last else None,
        'oldest_window_ts': window_rows[0][0] if window_rows else None,
    }


def remaining_mb(now=None):
    u = usage(now)
    return max(0.0, config.max_mb_per_window - u['window_mb'])


def check(now=None):
    # returns (ok, reason, next_allowed_ts)
    now = now or time.time()
    u = usage(now)
    window_free = (u['oldest_window_ts'] or now) + config.window_minutes * 60
    if u['day_articles'] >= config.max_articles_per_day:
        nxt = _day_start(now) + 86400
        return False, f"daily limit: {u['day_articles']}/{config.max_articles_per_day} articles today", nxt
    if u['window_articles'] >= config.max_articles_per_window:
        return (False, f"limit: {u['window_articles']}/{config.max_articles_per_window} articles "
                f"in {config.window_minutes} min", window_free)
    if u['window_mb'] >= config.max_mb_per_window:
        reason = f"limit: {u['window_mb']}/{config.max_mb_per_window} MB in {config.window_minutes} min"
        return False, reason, window_free
    return True, 'ok', now


def wait_for_gap(now=None, sleep=time.sleep):
    # keep min_delay_seconds between two fetches, one at a time
    now = now or time.time()
    last = usage(now)['last_fetch_ts']
    if last is None:
        return 0.0
    wait = last + config.min_delay_seconds - now
    if wait > 0:
        sleep(wait)
        return wait
    return 0.0


def describe_time(ts):
    return time.strftime('%Y-%m-%d %H:%M', time.localtime(ts))

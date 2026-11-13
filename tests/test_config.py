import importlib

from elsevier_research_mcp_utm import config


def reload_with(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return importlib.reload(config)


def test_utm_defaults(monkeypatch):
    for k in ('ERM_MAX_ARTICLES_PER_WINDOW', 'ERM_MAX_MB_PER_WINDOW', 'ERM_WINDOW_MINUTES',
              'ERM_MAX_ARTICLES_PER_DAY', 'ERM_MIN_DELAY_SECONDS', 'ERM_PROXY_HOST'):
        monkeypatch.delenv(k, raising=False)
    c = importlib.reload(config)
    assert (c.max_articles_per_window, c.max_mb_per_window, c.window_minutes) == (5, 100, 15)
    assert (c.max_articles_per_day, c.min_delay_seconds) == (20, 10)
    assert c.proxy_host == 'ezproxy.utm.my'
    assert c.problems == []


def test_bad_values_fall_back(monkeypatch):
    c = reload_with(monkeypatch, ERM_MAX_MB_PER_WINDOW='lots', ERM_WINDOW_MINUTES='0')
    assert c.max_mb_per_window == 100
    assert c.window_minutes == 15
    assert len(c.problems) == 2


def test_empty_proxy_turns_links_off(monkeypatch):
    c = reload_with(monkeypatch, ERM_PROXY_HOST='')
    assert c.proxy_host == ''


def teardown_module():
    importlib.reload(config)

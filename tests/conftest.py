import json
import os

import pytest

from elsevier_research_mcp_utm import client, config
from elsevier_research_mcp_utm.sources import scopus, semanticscholar

fixtures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


def load_fixture(name):
    with open(os.path.join(fixtures_dir, name), encoding='utf-8') as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def clean_config(tmp_path, monkeypatch):
    # every test gets its own cache, a fake key and the UTM default limits
    monkeypatch.setattr(config, 'cache_dir', str(tmp_path / 'cache'))
    monkeypatch.setattr(config, 'api_key', 'testkey123')
    monkeypatch.setattr(config, 'insttoken', '')
    monkeypatch.setattr(config, 'proxy_host', 'ezproxy.utm.my')
    monkeypatch.setattr(config, 'max_articles_per_window', 5)
    monkeypatch.setattr(config, 'max_mb_per_window', 100)
    monkeypatch.setattr(config, 'window_minutes', 15)
    monkeypatch.setattr(config, 'max_articles_per_day', 20)
    monkeypatch.setattr(config, 'min_delay_seconds', 10)
    monkeypatch.setattr(config, 'semantic_scholar_key', '')
    monkeypatch.setattr(config, 'openalex_mailto', '')
    monkeypatch.setattr(client.time, 'sleep', lambda s: None)
    monkeypatch.setattr(scopus, 'abstracts_blocked_until', 0.0)
    monkeypatch.setattr(semanticscholar, 'last_call', 0.0)
    monkeypatch.setattr(semanticscholar.time, 'sleep', lambda s: None)
    client.last_rate.clear()
    yield
    client.last_rate.clear()

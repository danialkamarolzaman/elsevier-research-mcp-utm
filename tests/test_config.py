import importlib
import os

import httpx
import pytest
import respx

from conftest import load_fixture
from elsevier_research_mcp_utm import config, doctor

settings = ('ELSEVIER_API_KEY', 'ELSEVIER_INSTTOKEN', 'ERM_MAX_ARTICLES_PER_WINDOW', 'ERM_MAX_MB_PER_WINDOW',
            'ERM_WINDOW_MINUTES', 'ERM_MAX_ARTICLES_PER_DAY', 'ERM_MIN_DELAY_SECONDS', 'ERM_PROXY_HOST')


@pytest.fixture
def cfg_file(tmp_path, monkeypatch):
    # isolated config file; real env settings removed
    path = tmp_path / 'erm' / '.env'
    path.parent.mkdir()
    monkeypatch.setenv('ERM_CONFIG_FILE', str(path))
    for k in settings:
        monkeypatch.delenv(k, raising=False)
    return path


def reload_with(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return importlib.reload(config)


def test_utm_defaults(cfg_file):
    c = importlib.reload(config)
    assert (c.max_articles_per_window, c.max_mb_per_window, c.window_minutes) == (5, 100, 15)
    assert (c.max_articles_per_day, c.min_delay_seconds) == (20, 10)
    assert c.proxy_host == 'ezproxy.utm.my'
    assert c.problems == [] and c.api_key == '' and c.source('ELSEVIER_API_KEY') == 'none'


def test_bad_values_fall_back(cfg_file, monkeypatch):
    c = reload_with(monkeypatch, ERM_MAX_MB_PER_WINDOW='lots', ERM_WINDOW_MINUTES='0')
    assert c.max_mb_per_window == 100
    assert c.window_minutes == 15
    assert len(c.problems) == 2


def test_empty_proxy_turns_links_off(cfg_file, monkeypatch):
    c = reload_with(monkeypatch, ERM_PROXY_HOST='')
    assert c.proxy_host == ''


# ---------------- config file ----------------
def test_key_read_from_file(cfg_file):
    cfg_file.write_text(
        '# my settings\n'
        'export ELSEVIER_API_KEY = "abc123"\n'
        "ELSEVIER_INSTTOKEN='tok 9'\n"
        'ERM_MAX_ARTICLES_PER_DAY=12   # stricter than default\n'
        '\n', encoding='utf-8')
    c = importlib.reload(config)
    assert c.api_key == 'abc123' and c.source('ELSEVIER_API_KEY') == 'file'
    assert c.insttoken == 'tok 9'
    assert c.max_articles_per_day == 12


def test_env_wins_over_file(cfg_file, monkeypatch):
    cfg_file.write_text('ELSEVIER_API_KEY=from_file\n', encoding='utf-8')
    c = reload_with(monkeypatch, ELSEVIER_API_KEY='from_env')
    assert c.api_key == 'from_env' and c.source('ELSEVIER_API_KEY') == 'env'


def test_empty_env_falls_back_to_file(cfg_file, monkeypatch):
    cfg_file.write_text('ELSEVIER_API_KEY=from_file\n', encoding='utf-8')
    c = reload_with(monkeypatch, ELSEVIER_API_KEY='  ')
    assert c.api_key == 'from_file'


def test_empty_proxy_in_file(cfg_file):
    cfg_file.write_text('ERM_PROXY_HOST=\n', encoding='utf-8')
    assert importlib.reload(config).proxy_host == ''


def test_missing_file_is_fine(cfg_file):
    c = importlib.reload(config)
    assert c.file_values == {} and c.problems == []


def test_malformed_lines_skipped_without_leaking(cfg_file):
    cfg_file.write_text('just some text secretvalue\n1BAD=x\nELSEVIER_API_KEY=good\n', encoding='utf-8')
    c = importlib.reload(config)
    assert c.api_key == 'good'
    assert len(c.problems) == 2
    assert not any('secretvalue' in p for p in c.problems)


def test_windows_bom_file(cfg_file):
    cfg_file.write_bytes('﻿ELSEVIER_API_KEY=bomkey\r\n'.encode('utf-8'))
    assert importlib.reload(config).api_key == 'bomkey'


@pytest.mark.skipif(os.name == 'nt', reason='unix permissions')
def test_loose_permissions_warned(cfg_file):
    cfg_file.write_text('ELSEVIER_API_KEY=x\n', encoding='utf-8')
    os.chmod(cfg_file, 0o644)
    c = importlib.reload(config)
    assert any('chmod 600' in p for p in c.problems)
    os.chmod(cfg_file, 0o600)
    assert not any('chmod 600' in p for p in importlib.reload(config).problems)


def test_default_paths(monkeypatch):
    monkeypatch.delenv('ERM_CONFIG_FILE', raising=False)
    path = config.config_file_path()
    assert path.endswith(os.path.join('elsevier-research-mcp-utm', '.env'))
    if os.name == 'nt':
        assert path.startswith(os.environ['APPDATA'])
    else:
        monkeypatch.setenv('XDG_CONFIG_HOME', '/tmp/xdg')
        assert config.config_file_path() == '/tmp/xdg/elsevier-research-mcp-utm/.env'


@respx.mock
def test_doctor_reports_source_not_key(cfg_file):
    cfg_file.write_text('ELSEVIER_API_KEY=filekey999\n', encoding='utf-8')
    importlib.reload(config)
    respx.get(url__regex=r'https://api\.elsevier\.com/content/search/.*').mock(
        return_value=httpx.Response(200, json=load_fixture('scopus_search.json')))
    respx.get(url__regex=r'https://api\.elsevier\.com/content/(abstract|article)/.*').mock(
        return_value=httpx.Response(403, json={}))
    r = doctor.run()
    assert r['api_key_valid'] and r['api_key_source'] == 'file' and r['config_file_found']
    out = doctor.text(r)
    assert '(from file)' in out and 'filekey999' not in out


def test_doctor_no_key_names_config_file(cfg_file):
    importlib.reload(config)
    r = doctor.run()
    assert r['api_key_source'] == 'none' and not r['config_file_found']
    assert str(cfg_file) in r['advice'][0]


def teardown_module():
    importlib.reload(config)

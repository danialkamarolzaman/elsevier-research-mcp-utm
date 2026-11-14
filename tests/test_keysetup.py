import os
import re

import httpx
import pytest
import respx

from conftest import load_fixture
from elsevier_research_mcp_utm import config, doctor, keysetup

search = re.compile(r'https://api\.elsevier\.com/content/search/scopus.*')
good = 'goodkey1234567890'
bad = 'badkey0987654321'


def err(code):
    return {'service-error': {'status': {'statusCode': code, 'statusText': 'x'}}}


def by_key(request):
    # the fake elsevier: only the good key (and, if sent, the good token) works
    token = request.headers.get('X-ELS-Insttoken')
    if request.headers.get('X-ELS-APIKey') != good or token not in (None, 'goodtok'):
        return httpx.Response(401, json=err('AUTHENTICATION_ERROR'))
    return httpx.Response(200, json=load_fixture('scopus_search.json'))


@pytest.fixture
def env(tmp_path, monkeypatch):
    path = tmp_path / 'erm' / '.env'
    monkeypatch.setattr(config, 'config_file', str(path))
    monkeypatch.setattr(config, 'sources', {})
    monkeypatch.setattr(config, 'api_key', '')
    monkeypatch.setattr(doctor, 'run', lambda doi=None: {})
    monkeypatch.setattr(doctor, 'text', lambda report: 'DOCTOR REPORT')
    return path


def session(secrets, answers=()):
    # scripted terminal: hidden answers, visible answers, captured output, opened urls
    secrets, answers, out, opened = list(secrets), list(answers), [], []
    kw = dict(ask=lambda p: (out.append(p), answers.pop(0))[1],
              ask_secret=lambda p: (out.append(p), secrets.pop(0))[1],
              say=out.append, browser=opened.append, interactive=True)
    return kw, out, opened


@respx.mock
def test_happy_path_saves_checked_key(env):
    respx.get(url__regex=search).mock(side_effect=by_key)
    kw, out, opened = session([good, ''], [''])
    assert keysetup.run(**kw) == 0
    assert opened == [keysetup.key_page]
    assert env.read_text(encoding='utf-8') == f'ELSEVIER_API_KEY={good}\n'
    assert config.api_key == good and config.source('ELSEVIER_API_KEY') == 'file'
    assert 'DOCTOR REPORT' in out
    assert not any(good in str(line) for line in out)  # key never shown
    if os.name != 'nt':
        assert oct(os.stat(env).st_mode & 0o777) == '0o600'


@respx.mock
def test_rejected_three_times_saves_nothing(env):
    respx.get(url__regex=search).mock(side_effect=by_key)
    kw, out, _ = session([bad, bad, bad])
    assert keysetup.run(**kw) == 1
    assert not env.exists()
    assert sum('Key rejected' in str(line) for line in out) == 3
    assert not any(bad in str(line) for line in out)


@respx.mock
def test_retry_after_typo(env):
    respx.get(url__regex=search).mock(side_effect=by_key)
    kw, out, _ = session([bad, good, ''], [''])
    assert keysetup.run(**kw) == 0
    assert f'ELSEVIER_API_KEY={good}' in env.read_text(encoding='utf-8')


@respx.mock
def test_keeps_other_lines_and_replaces_old_key(env):
    env.parent.mkdir()
    env.write_text('# mine\nexport ELSEVIER_API_KEY=old\nERM_MAX_ARTICLES_PER_DAY=10\n', encoding='utf-8')
    respx.get(url__regex=search).mock(side_effect=by_key)
    kw, _, _ = session([good, ''], ['y', 'me@example.org'])
    assert keysetup.run(**kw) == 0
    assert env.read_text(encoding='utf-8') == (
        f'# mine\nELSEVIER_API_KEY={good}\nERM_MAX_ARTICLES_PER_DAY=10\nOPENALEX_MAILTO=me@example.org\n')


@respx.mock
def test_existing_key_kept_unless_confirmed(env):
    env.parent.mkdir()
    env.write_text(f'ELSEVIER_API_KEY={good}\n', encoding='utf-8')
    respx.get(url__regex=search).mock(side_effect=by_key)
    kw, out, opened = session([''], ['', ''])  # no to replace, skip token and email
    assert keysetup.run(**kw) == 0
    assert opened == [] and 'Keeping the saved key.' in out
    assert env.read_text(encoding='utf-8') == f'ELSEVIER_API_KEY={good}\n'


@respx.mock
def test_insttoken_checked_before_saving(env):
    respx.get(url__regex=search).mock(side_effect=by_key)
    kw, out, _ = session([good, 'wrongtok'], [''])
    assert keysetup.run(**kw) == 0
    assert 'ELSEVIER_INSTTOKEN' not in env.read_text(encoding='utf-8')
    assert any('Insttoken not accepted' in str(line) for line in out)
    kw, _, _ = session(['goodtok'], ['', ''])
    assert keysetup.run(**kw) == 0
    assert 'ELSEVIER_INSTTOKEN=goodtok' in env.read_text(encoding='utf-8')


@respx.mock
def test_network_error_asks_before_saving(env):
    respx.get(url__regex=search).mock(side_effect=httpx.ConnectError('offline'))
    kw, out, _ = session([good], ['n'])
    assert keysetup.run(**kw) == 1
    assert not env.exists()


def test_env_key_warned(env, monkeypatch):
    monkeypatch.setattr(config, 'sources', {'ELSEVIER_API_KEY': 'env'})
    kw, out, _ = session([''])
    keysetup.run(**kw)
    assert any('wins over the config file' in str(line) for line in out)


def test_no_terminal_refuses(env):
    out = []
    assert keysetup.run(say=out.append, interactive=False) == 2
    assert 'real terminal' in out[0] and not env.exists()


def test_check_key_restores_config():
    with respx.mock:
        respx.get(url__regex=search).mock(side_effect=by_key)
        assert keysetup.check_key(good) == (True, None)
        ok, why = keysetup.check_key(bad)
    assert ok is False and bad not in why
    assert config.api_key == 'testkey123'

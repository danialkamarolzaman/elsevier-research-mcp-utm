import httpx
import pytest
import respx

from elsevier_research_mcp_utm import client, config

url = 'https://api.elsevier.com/content/search/scopus'


def err(code, text):
    return {'service-error': {'status': {'statusCode': code, 'statusText': text}}}


def test_headers_add_insttoken_only_when_set(monkeypatch):
    assert 'X-ELS-Insttoken' not in client.headers()
    monkeypatch.setattr(config, 'insttoken', 'tok999')
    assert client.headers()['X-ELS-Insttoken'] == 'tok999'


def test_redact_hides_key_and_token(monkeypatch):
    monkeypatch.setattr(config, 'insttoken', 'tok999')
    assert client.redact('key=testkey123 tok=tok999') == 'key=*** tok=***'


def test_no_key(monkeypatch):
    monkeypatch.setattr(config, 'api_key', '')
    with pytest.raises(client.ApiError) as e:
        client.get(url)
    assert e.value.code == 'NO_KEY'


@respx.mock
def test_bad_key_message():
    respx.get(url).mock(return_value=httpx.Response(401, json=err('AUTHENTICATION_ERROR', 'Invalid API Key')))
    with pytest.raises(client.ApiError) as e:
        client.get(url)
    assert e.value.status == 401
    assert 'API key rejected' in str(e.value)


@respx.mock
def test_view_not_entitled_is_not_bad_key():
    respx.get(url).mock(return_value=httpx.Response(401, json=err('AUTHORIZATION_ERROR', 'not authorized')))
    with pytest.raises(client.ApiError) as e:
        client.get(url)
    assert 'not entitled' in str(e.value)


@respx.mock
def test_error_never_leaks_key():
    respx.get(url).mock(return_value=httpx.Response(400, json=err('INVALID_INPUT', 'bad key testkey123')))
    with pytest.raises(client.ApiError) as e:
        client.get(url)
    assert 'testkey123' not in str(e.value)


@respx.mock
def test_throttle_429_is_retried():
    route = respx.get(url).mock(side_effect=[
        httpx.Response(429, headers={'X-RateLimit-Remaining': '50'}),
        httpx.Response(200, json={'ok': True}, headers={'X-RateLimit-Remaining': '49'}),
    ])
    assert client.get_json(url) == {'ok': True}
    assert route.call_count == 2
    assert client.last_rate['X-RateLimit-Remaining'] == '49'


@respx.mock
def test_quota_gone_429_is_not_retried():
    route = respx.get(url).mock(return_value=httpx.Response(
        429, headers={'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '1900000000'}))
    with pytest.raises(client.ApiError) as e:
        client.get(url)
    assert route.call_count == 1
    assert 'quota' in str(e.value)


@respx.mock
def test_server_error_retried_then_raised():
    route = respx.get(url).mock(return_value=httpx.Response(503))
    with pytest.raises(client.ApiError):
        client.get(url)
    assert route.call_count == config.retries

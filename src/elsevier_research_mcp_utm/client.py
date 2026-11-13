import logging
import time

import httpx

from . import __version__, config

logging.getLogger('httpx').setLevel(logging.WARNING)  # no per-request log lines
user_agent = f'elsevier-research-mcp-utm/{__version__}'
last_rate = {}  # latest Elsevier rate-limit headers


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(redact(message))
        self.status = status  # http status
        self.code = code  # elsevier statusCode, e.g. AUTHORIZATION_ERROR


def redact(text):
    text = str(text)
    for secret in (config.api_key, config.insttoken):
        if secret:
            text = text.replace(secret, '***')
    return text


def headers(accept='application/json'):
    h = {'X-ELS-APIKey': config.api_key, 'Accept': accept, 'User-Agent': user_agent}
    if config.insttoken:
        h['X-ELS-Insttoken'] = config.insttoken
    return h


def _read_rate(resp):
    for name in ('X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset'):
        if name in resp.headers:
            last_rate[name] = resp.headers[name]


def _service_error(resp):
    try:
        status = resp.json()['service-error']['status']
        return status.get('statusCode', ''), status.get('statusText', '')
    except Exception:
        return '', resp.text[:200]


def _explain(status, code, text):
    # turn elsevier errors into something a user can act on
    if status == 401 and code == 'AUTHORIZATION_ERROR':
        return 'not entitled to this view (normal off-campus): ' + text
    if status == 401:
        return 'API key rejected, check ELSEVIER_API_KEY: ' + text
    if status == 403:
        return 'no access from this network or token (needs campus IP or insttoken): ' + text
    if status == 404:
        return 'not found: ' + text
    if status == 429:
        reset = last_rate.get('X-RateLimit-Reset', '')
        when = time.strftime('%Y-%m-%d %H:%M', time.localtime(int(reset))) if reset.isdigit() else 'later'
        return f'Elsevier quota or throttle limit hit, try again {when}: ' + text
    return f'HTTP {status}: ' + text


def get(url, params=None, accept='application/json'):
    if not config.api_key:
        raise ApiError(0, 'NO_KEY', 'ELSEVIER_API_KEY is not set')
    resp = None
    for attempt in range(config.retries):
        try:
            resp = httpx.get(url, params=params, headers=headers(accept), timeout=config.timeout)
        except httpx.HTTPError as e:
            if attempt == config.retries - 1:
                raise ApiError(0, 'NETWORK', f'network error: {e}')
            time.sleep(2 ** attempt)
            continue
        _read_rate(resp)
        quota_gone = last_rate.get('X-RateLimit-Remaining') == '0'
        retry = resp.status_code >= 500 or (resp.status_code == 429 and not quota_gone)
        if retry and attempt < config.retries - 1:
            time.sleep(2 ** attempt)
            continue
        break
    if resp.status_code >= 400:
        code, text = _service_error(resp)
        raise ApiError(resp.status_code, code, _explain(resp.status_code, code, text))
    return resp


def get_json(url, params=None):
    return get(url, params).json()

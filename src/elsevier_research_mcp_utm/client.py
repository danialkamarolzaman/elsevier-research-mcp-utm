import logging
import os
import time
from urllib.parse import urlparse

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
    for secret in (config.api_key, config.insttoken, config.semantic_scholar_key):
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


def _send(url, params, hdrs, elsevier):
    # one request with retry on throttle / server errors
    resp = None
    for attempt in range(config.retries):
        try:
            resp = httpx.get(url, params=params, headers=hdrs, timeout=config.timeout, follow_redirects=True)
        except httpx.HTTPError as e:
            if attempt == config.retries - 1:
                raise ApiError(0, 'NETWORK', f'network error: {e}')
            time.sleep(2 ** attempt)
            continue
        if elsevier:
            _read_rate(resp)
        quota_gone = elsevier and last_rate.get('X-RateLimit-Remaining') == '0'
        retry = resp.status_code >= 500 or (resp.status_code == 429 and not quota_gone)
        if retry and attempt < config.retries - 1:
            time.sleep(2 ** attempt)
            continue
        break
    return resp


# ---------------- elsevier ----------------
def get(url, params=None, accept='application/json'):
    if not config.api_key:
        raise ApiError(0, 'NO_KEY', 'ELSEVIER_API_KEY is not set')
    resp = _send(url, params, headers(accept), elsevier=True)
    if resp.status_code >= 400:
        code, text = _service_error(resp)
        raise ApiError(resp.status_code, code, _explain(resp.status_code, code, text))
    return resp


def get_json(url, params=None):
    return get(url, params).json()


# ---------------- streamed downloads ----------------
class TooLarge(Exception):
    pass


def stream_to_file(url, path, max_bytes, accept='application/pdf', elsevier=True):
    # streams into path.part, renames when complete. returns bytes received.
    # raises TooLarge (before or during download) or ApiError; partial files are removed.
    # every return / raise carries .received so the caller can log what was transferred
    if elsevier and not config.api_key:
        raise ApiError(0, 'NO_KEY', 'ELSEVIER_API_KEY is not set')
    hdrs = headers(accept) if elsevier else {'User-Agent': user_agent, 'Accept': accept}
    part = path + '.part'
    received = 0
    try:
        with httpx.stream('GET', url, headers=hdrs, timeout=config.timeout, follow_redirects=True) as resp:
            if elsevier:
                _read_rate(resp)
            if resp.status_code >= 400:
                resp.read()
                code, text = _service_error(resp) if elsevier else ('HTTP', resp.text[:150])
                raise ApiError(resp.status_code, code, _explain(resp.status_code, code, text))
            size = resp.headers.get('Content-Length')
            left = f'{max_bytes / 1e6:.1f} MB'
            if size and size.isdigit() and int(size) > max_bytes:
                err = TooLarge(f'file is {int(size) / 1e6:.1f} MB, only {left} left in window')
                err.received = 0
                raise err
            first = b''
            with open(part, 'wb') as f:
                for chunk in resp.iter_bytes():
                    if len(first) < 5:
                        first += chunk[:5]
                    received += len(chunk)
                    if received > max_bytes:
                        err = TooLarge(f'stopped at {received / 1e6:.1f} MB, over the {left} left')
                        err.received = received
                        raise err
                    f.write(chunk)
            if accept == 'application/pdf' and not first.startswith(b'%PDF'):
                err = ApiError(resp.status_code, 'NOT_PDF', 'server did not return a PDF (login page?)')
                err.received = received
                raise err
        os.replace(part, path)
        return received
    except httpx.HTTPError as e:
        err = ApiError(0, 'NETWORK', f'network error: {e}')
        err.received = received
        raise err
    finally:
        if os.path.exists(part):
            os.remove(part)


# ---------------- free sources (openalex, semantic scholar) ----------------
def get_public_json(url, params=None, extra_headers=None):
    # returns None on 404
    hdrs = {'User-Agent': user_agent, 'Accept': 'application/json', **(extra_headers or {})}
    resp = _send(url, params, hdrs, elsevier=False)
    if resp.status_code == 404:
        return None
    if resp.status_code >= 400:
        host = urlparse(url).netloc
        raise ApiError(resp.status_code, 'HTTP', f'{host} HTTP {resp.status_code}: {resp.text[:150]}')
    return resp.json()

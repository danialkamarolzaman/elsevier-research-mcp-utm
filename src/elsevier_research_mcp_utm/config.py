import os

problems = []  # bad env values found while loading


def _text(name, default=''):
    return os.environ.get(name, default).strip()


def _int(name, default, lowest=0):
    raw = _text(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        problems.append(f'{name}={raw!r} is not a whole number, using {default}')
        return default
    if value < lowest:
        problems.append(f'{name}={value} is below {lowest}, using {default}')
        return default
    return value


def _default_cache_dir():
    if os.name == 'nt' and os.environ.get('LOCALAPPDATA'):
        return os.path.join(os.environ['LOCALAPPDATA'], 'elsevier-research-mcp-utm')
    base = os.environ.get('XDG_CACHE_HOME') or os.path.join(os.path.expanduser('~'), '.cache')
    return os.path.join(base, 'elsevier-research-mcp-utm')


# ---------------- api ----------------
api_key = _text('ELSEVIER_API_KEY')  # required, from dev.elsevier.com
insttoken = _text('ELSEVIER_INSTTOKEN')  # optional, from your library
openalex_mailto = _text('OPENALEX_MAILTO')  # optional, OpenAlex polite pool
base_url = 'https://api.elsevier.com'
timeout = 30  # seconds per request
retries = 3  # on 429 throttle / 5xx

# ---------------- files ----------------
cache_dir = _text('ERM_CACHE_DIR') or _default_cache_dir()
download_dir = _text('ERM_DOWNLOAD_DIR') or os.path.abspath('papers')
pdf_name = _text('ERM_PDF_NAME') or '{first_author} {year} - {title}'
cache_days = _int('ERM_CACHE_DAYS', 30)  # search / abstract cache lifetime

# ---------------- institution (UTM defaults) ----------------
proxy_host = _text('ERM_PROXY_HOST', 'ezproxy.utm.my')  # empty = no proxy links
max_articles_per_window = _int('ERM_MAX_ARTICLES_PER_WINDOW', 5, 1)
max_mb_per_window = _int('ERM_MAX_MB_PER_WINDOW', 100, 1)
window_minutes = _int('ERM_WINDOW_MINUTES', 15, 1)
max_articles_per_day = _int('ERM_MAX_ARTICLES_PER_DAY', 20, 1)
min_delay_seconds = _int('ERM_MIN_DELAY_SECONDS', 10, 0)

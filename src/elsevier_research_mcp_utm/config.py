import os
import re
import stat

problems = []  # bad settings found while loading (never contain secret values)
sources = {}  # setting name -> 'env' or 'file', for doctor


# ---------------- config file ----------------
# some hosts (e.g. the Claude desktop app on macOS) do not pass the user's shell
# environment to MCP servers, so settings can also live in a KEY=value file
def config_file_path():
    if os.environ.get('ERM_CONFIG_FILE'):
        return os.environ['ERM_CONFIG_FILE']
    if os.name == 'nt' and os.environ.get('APPDATA'):
        return os.path.join(os.environ['APPDATA'], 'elsevier-research-mcp-utm', '.env')
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
    return os.path.join(base, 'elsevier-research-mcp-utm', '.env')


def read_env_file(path):
    values = {}
    if not os.path.isfile(path):
        return values
    try:
        with open(path, encoding='utf-8-sig') as f:
            lines = f.read().splitlines()
    except OSError as e:
        problems.append(f'cannot read config file {path}: {e.strerror}')
        return values
    for n, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[len('export '):].strip()
        if '=' not in line:
            problems.append(f'config file line {n}: no "=", skipped')
            continue
        key, value = (part.strip() for part in line.split('=', 1))
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
            problems.append(f'config file line {n}: bad name, skipped')
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]  # quoted, keep as is
        else:
            value = re.split(r'\s+#', value, maxsplit=1)[0].strip()  # drop trailing comment
        values[key] = value
    if os.name != 'nt' and values:
        mode = os.stat(path).st_mode
        if mode & (stat.S_IRWXG | stat.S_IRWXO):
            problems.append(f'config file is readable by other users, run: chmod 600 "{path}"')
    return values


config_file = config_file_path()
file_values = read_env_file(config_file)


def _unexpanded(value):
    # a host that could not fill a placeholder may pass it through literally, e.g. '${user_config.x}'
    return bool(re.fullmatch(r'\$\{[^}]*\}', value.strip()))


# ---------------- readers: env var, then plugin setting, then config file, then default ----------------
# the claude code plugin passes its prompted values as ERM_PLUGIN_* (not the real names), so an
# empty plugin field never hides a key the user already set in the environment
def _text(name, default='', keep_empty=False, plugin=None):
    raw = os.environ.get(name)
    if raw is not None and not _unexpanded(raw) and (raw.strip() or keep_empty):
        sources[name] = 'env'
        return raw.strip()
    raw = os.environ.get(plugin) if plugin else None
    if raw and raw.strip() and not _unexpanded(raw):
        sources[name] = 'plugin'
        return raw.strip()
    if name in file_values:
        sources[name] = 'file'
        return file_values[name].strip()
    return default


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


def source(name):
    return sources.get(name, 'none')


def _default_cache_dir():
    if os.name == 'nt' and os.environ.get('LOCALAPPDATA'):
        return os.path.join(os.environ['LOCALAPPDATA'], 'elsevier-research-mcp-utm')
    base = os.environ.get('XDG_CACHE_HOME') or os.path.join(os.path.expanduser('~'), '.cache')
    return os.path.join(base, 'elsevier-research-mcp-utm')


# ---------------- api ----------------
api_key = _text('ELSEVIER_API_KEY', plugin='ERM_PLUGIN_API_KEY')  # required, from dev.elsevier.com
insttoken = _text('ELSEVIER_INSTTOKEN', plugin='ERM_PLUGIN_INSTTOKEN')  # optional, from your library
openalex_mailto = _text('OPENALEX_MAILTO', plugin='ERM_PLUGIN_OPENALEX_MAILTO')  # optional, OpenAlex
semantic_scholar_key = _text('SEMANTIC_SCHOLAR_API_KEY')  # optional, higher S2 rate limit
base_url = 'https://api.elsevier.com'
timeout = 30  # seconds per request
retries = 3  # on 429 throttle / 5xx

# ---------------- files ----------------
cache_dir = _text('ERM_CACHE_DIR') or _default_cache_dir()
download_dir = _text('ERM_DOWNLOAD_DIR') or os.path.abspath('papers')
pdf_name = _text('ERM_PDF_NAME') or '{first_author} {year} - {title}'
# where the user's browser saves downloads (browser-assisted fetch of closed papers)
browser_downloads_dir = _text('ERM_BROWSER_DOWNLOADS') or os.path.join(os.path.expanduser('~'), 'Downloads')
cache_days = _int('ERM_CACHE_DAYS', 30)  # search / abstract cache lifetime

# ---------------- institution (UTM defaults) ----------------
proxy_host = _text('ERM_PROXY_HOST', 'ezproxy.utm.my', keep_empty=True)  # empty = no proxy links
max_articles_per_window = _int('ERM_MAX_ARTICLES_PER_WINDOW', 5, 1)
max_mb_per_window = _int('ERM_MAX_MB_PER_WINDOW', 100, 1)
window_minutes = _int('ERM_WINDOW_MINUTES', 15, 1)
max_articles_per_day = _int('ERM_MAX_ARTICLES_PER_DAY', 20, 1)
min_delay_seconds = _int('ERM_MIN_DELAY_SECONDS', 10, 0)
recheck_minutes = _int('ERM_RECHECK_MINUTES', 30, 5)  # background worker: re-test access this often

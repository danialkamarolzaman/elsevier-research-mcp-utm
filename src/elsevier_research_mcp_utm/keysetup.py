import getpass
import os
import re
import sys
import webbrowser

from . import client, config, doctor
from .sources import scopus

key_page = 'https://dev.elsevier.com/apikey/manage'
max_tries = 3


def yes(answer, default=False):
    answer = answer.strip().lower()
    if not answer:
        return default
    return answer in ('y', 'yes')


# ---------------- key check: one scopus search (metadata, not counted in download limits) ----------------
def check_key(key, token=''):
    # returns (True, None) ok, (False, why) rejected, (None, why) could not tell (network etc.)
    old = config.api_key, config.insttoken
    config.api_key, config.insttoken = key, token
    try:
        scopus.search(doctor.test_query, count=1, use_cache=False)
        return True, None
    except client.ApiError as e:
        if e.status in (401, 403):
            return False, str(e)  # message is redacted, never contains the key
        return None, str(e)
    finally:
        config.api_key, config.insttoken = old


# ---------------- config file: replace or add lines, keep everything else ----------------
def write_settings(path, updates):
    lines = []
    if os.path.isfile(path):
        with open(path, encoding='utf-8-sig') as f:
            lines = f.read().splitlines()
    todo = dict(updates)
    for i, line in enumerate(lines):
        m = re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
        if m and m.group(1) in todo:
            lines[i] = f'{m.group(1)}={todo.pop(m.group(1))}'
    lines += [f'{k}={v}' for k, v in todo.items()]
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = path + '.tmp'
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)  # private from the start
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    os.replace(tmp, path)
    if os.name != 'nt':
        os.chmod(path, 0o600)


def ask_key(ask, ask_secret, say):
    # up to max_tries; returns the checked key or None
    for attempt in range(1, max_tries + 1):
        key = ask_secret('Elsevier API key (hidden, paste and press Enter): ').strip()
        if not key:
            say('No key entered.')
            return None
        say('Checking the key with one Scopus search ...')
        ok, why = check_key(key)
        if ok:
            say('Key works.')
            return key
        if ok is None:
            say(f'Could not check the key: {why}')
            return key if yes(ask('Save it anyway? [y/N] ')) else None
        say(f'Key rejected ({attempt}/{max_tries}): {why}')
    return None


def run(ask=None, ask_secret=None, say=print, browser=webbrowser.open, interactive=None):
    ask = ask or input
    ask_secret = ask_secret or getpass.getpass
    if interactive is None:
        interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if not interactive:
        say('setup needs a real terminal for hidden input. Open a terminal window and run:\n'
            '  uvx --from git+https://github.com/danialkamarolzaman/elsevier-research-mcp-utm '
            'elsevier-research-mcp-utm setup\n'
            'Never paste your key into a chat.')
        return 2
    path = config.config_file
    saved = config.read_env_file(path)
    say(f'elsevier-research-mcp-utm setup\nConfig file: {path}\n')
    for name in ('ELSEVIER_API_KEY', 'ELSEVIER_INSTTOKEN'):
        if config.source(name) in ('env', 'plugin'):
            say(f'Note: {name} is also set by the {config.source(name)} '
                f'({"environment variable" if config.source(name) == "env" else "plugin settings"}). '
                'That value wins over the config file; remove or update it there too.')

    updates = {}
    replace = 'A key is already saved in this file. Replace it? [y/N] '
    if saved.get('ELSEVIER_API_KEY') and not yes(ask(replace)):
        key = saved['ELSEVIER_API_KEY']
        say('Keeping the saved key.')
    else:
        say(f'Opening {key_page} - sign in, click "Create API Key", then copy the key.')
        try:
            browser(key_page)
        except Exception:
            pass  # no browser, the link is printed above
        key = ask_key(ask, ask_secret, say)
        if not key:
            say('Nothing saved.')
            return 1
        updates['ELSEVIER_API_KEY'] = key

    token = ask_secret('Insttoken from your library (hidden, Enter to skip): ').strip()
    if token:
        ok, why = check_key(key, token)
        if ok is False:
            say(f'Insttoken not accepted, not saved: {why}')
        else:
            updates['ELSEVIER_INSTTOKEN'] = token
    mailto = ask('Email for the OpenAlex polite pool (optional, Enter to skip): ').strip()
    if mailto:
        updates['OPENALEX_MAILTO'] = mailto

    if updates:
        write_settings(path, updates)
        say(f'Saved {", ".join(sorted(updates))} to {path}' + ('' if os.name == 'nt' else ' (chmod 600)'))
    else:
        say('Nothing changed.')
    # show the result with the new values, unless env / plugin values win anyway
    for name, attr in (('ELSEVIER_API_KEY', 'api_key'), ('ELSEVIER_INSTTOKEN', 'insttoken'),
                       ('OPENALEX_MAILTO', 'openalex_mailto')):
        if name in updates and config.source(name) not in ('env', 'plugin'):
            setattr(config, attr, updates[name])
            config.sources[name] = 'file'
    say('')
    say(doctor.text(doctor.run()))
    say('\nRestart Claude Code (or your MCP app) so the server picks up the change.')
    return 0

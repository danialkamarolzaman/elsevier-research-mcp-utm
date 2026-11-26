import os

from . import __version__, client, config, limits
from .sources import sciencedirect, scopus

# ---------------- setup check ----------------
test_query = 'SRCTITLE("Reliability Engineering and System Safety") AND TITLE(maintenance)'


def _abstract_allowed(scopus_id):
    try:
        client.get_json(f'{config.base_url}/content/abstract/scopus_id/{scopus_id}', {'view': 'META_ABS'})
        return True, None
    except client.ApiError as e:
        if e.status in (401, 403):
            return False, str(e)
        raise


def run(doi=None):
    report = {
        'version': __version__,
        'api_key_set': bool(config.api_key),
        'api_key_source': config.source('ELSEVIER_API_KEY') if config.api_key else 'none',
        'api_key_valid': None,
        'insttoken_set': bool(config.insttoken),
        'insttoken_source': config.source('ELSEVIER_INSTTOKEN') if config.insttoken else 'none',
        'config_file': config.config_file,
        'config_file_found': os.path.isfile(config.config_file),
        'tier': 'none',
        'abstracts': None,
        'fulltext': None,
        'checked_paper': None,
        'quota': {},
        'limits': limits.usage(),
        'cache_dir': config.cache_dir,
        'proxy_host': config.proxy_host or None,
        'config_problems': list(config.problems),
        'notes': [],
        'advice': [],
    }
    if not config.api_key:
        report['advice'].append(
            'No ELSEVIER_API_KEY found (get one at https://dev.elsevier.com). Easiest: run '
            '"elsevier-research-mcp-utm setup" in a terminal (hidden input, checks the key, saves it). '
            f'Or put the line ELSEVIER_API_KEY=<your key> in {config.config_file} (works in every app, '
            'including the Claude desktop app), or enter it in the Claude Code plugin settings, '
            'or set it as an environment variable. Then restart the app.')
        return report
    # 1 key works?
    try:
        res = scopus.search(test_query, count=1, use_cache=False)
    except client.ApiError as e:
        report['api_key_valid'] = False if e.status == 401 else None
        report['notes'].append(f'test search failed: {e}')
        if e.status == 401:
            report['advice'].append(
                f"The key from {report['api_key_source']} was rejected. Fix it there "
                '(env = environment variable, plugin = Claude Code plugin settings, file = config file), '
                'or run "elsevier-research-mcp-utm setup".')
        return report
    report['api_key_valid'] = True
    report['tier'] = 'metadata'
    sample = res['papers'][0] if res['papers'] else {}
    # 2 abstracts?
    if sample.get('scopus_id'):
        report['abstracts'], note = _abstract_allowed(sample['scopus_id'])
        if note:
            report['notes'].append(f'abstract check: {note}')
        if report['abstracts']:
            report['tier'] = 'abstracts'
    # 3 full text? (entitlement only, nothing downloaded, not counted in limits)
    target_doi = doi or sample.get('doi')
    target_pii = None if doi else sample.get('pii')
    if target_doi or target_pii:
        report['checked_paper'] = target_doi or target_pii
        report['fulltext'], note = sciencedirect.entitled(target_doi, target_pii)
        if note:
            report['notes'].append(f'full-text check: {note}')
        if report['fulltext']:
            report['tier'] = 'fulltext'
    report['quota'] = dict(client.last_rate)
    if report['tier'] != 'fulltext':
        report['advice'].append(
            'Full text needs a subscribed network: be on campus Wi-Fi, or ask your library for an '
            'Elsevier insttoken (set ELSEVIER_INSTTOKEN). A split-tunnel VPN may not help. '
            'UTM: neither works (no insttoken is issued, the API refuses full text on campus too); '
            'open proxy_url in your browser and download by hand, see docs/manual-full-text.md.')
    if not report['abstracts']:
        report['advice'].append(
            'Abstracts fall back to OpenAlex and Semantic Scholar: good for open-access and most '
            'non-Elsevier papers, but Elsevier abstracts need campus Wi-Fi or an insttoken.')
    return report


def text(report):
    yes = {True: 'yes', False: 'no', None: 'unknown'}
    u = report['limits']
    lines = [
        f"elsevier-research-mcp-utm {report['version']}",
        f"API key set      : {yes[report['api_key_set']]} (from {report['api_key_source']})",
        f"API key valid    : {yes[report['api_key_valid']]}",
        f"insttoken set    : {yes[report['insttoken_set']]} (from {report['insttoken_source']})",
        f"config file      : {report['config_file']} "
        f"({'found' if report['config_file_found'] else 'not found'})",
        f"access tier      : {report['tier']}",
        f"abstracts        : {yes[report['abstracts']]}",
        f"full text        : {yes[report['fulltext']]}" + (
            f" (checked {report['checked_paper']})" if report['checked_paper'] else ''),
        f"quota remaining  : {report['quota'].get('X-RateLimit-Remaining', 'unknown')}",
        f"limits           : {u['window_articles']}/{u['max_articles_per_window']} articles, "
        f"{u['window_mb']}/{u['max_mb_per_window']} MB in {u['window_minutes']} min, "
        f"{u['day_articles']}/{u['max_articles_per_day']} today",
        f"proxy host       : {report['proxy_host'] or 'off'}",
        f"cache dir        : {report['cache_dir']}",
    ]
    for p in report['config_problems']:
        lines.append(f'config problem   : {p}')
    for n in report['notes']:
        lines.append(f'note             : {n}')
    for a in report['advice']:
        lines.append(f'advice           : {a}')
    return '\n'.join(lines)

from . import __version__, client, config, limits
from .sources import scopus

# ---------------- setup check ----------------
test_query = 'SRCTITLE("Reliability Engineering and System Safety") AND TITLE(maintenance)'


def _entitlement(doi=None, pii=None):
    ident = f'pii/{pii}' if pii else f'doi/{doi}'
    try:
        data = client.get_json(f'{config.base_url}/content/article/entitlement/{ident}')
        ent = data.get('entitlement-response', {}).get('document-entitlement', {})
        return bool(ent.get('entitled')), None
    except client.ApiError as e:
        if e.status in (401, 403):
            return False, str(e)
        raise


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
        'api_key_valid': None,
        'insttoken_set': bool(config.insttoken),
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
        report['advice'].append('Set ELSEVIER_API_KEY (get one at https://dev.elsevier.com).')
        return report
    # 1 key works?
    try:
        res = scopus.search(test_query, count=1, use_cache=False)
    except client.ApiError as e:
        report['api_key_valid'] = False if e.status == 401 else None
        report['notes'].append(f'test search failed: {e}')
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
        report['fulltext'], note = _entitlement(target_doi, target_pii)
        if note:
            report['notes'].append(f'full-text check: {note}')
        if report['fulltext']:
            report['tier'] = 'fulltext'
    report['quota'] = dict(client.last_rate)
    if report['tier'] != 'fulltext':
        report['advice'].append(
            'Full text needs a subscribed network: be on campus Wi-Fi, or ask your library for an '
            'Elsevier insttoken (set ELSEVIER_INSTTOKEN). UTM: libsupport@utm.my. '
            'A split-tunnel VPN may not help.')
    if not report['abstracts']:
        report['advice'].append('Abstracts will come from OpenAlex instead (free, no key).')
    return report


def text(report):
    yes = {True: 'yes', False: 'no', None: 'unknown'}
    u = report['limits']
    lines = [
        f"elsevier-research-mcp-utm {report['version']}",
        f"API key set      : {yes[report['api_key_set']]}",
        f"API key valid    : {yes[report['api_key_valid']]}",
        f"insttoken set    : {yes[report['insttoken_set']]}",
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

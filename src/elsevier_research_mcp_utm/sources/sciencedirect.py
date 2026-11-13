from .. import client, config

article_path = '/content/article/'
entitlement_path = '/content/article/entitlement/'


def ident(doi=None, pii=None):
    # pii is exact for sciencedirect, doi works too
    return f'pii/{pii}' if pii else f'doi/{doi}'


def entitled(doi=None, pii=None):
    # (True/False, note). asks only, nothing is downloaded
    try:
        data = client.get_json(config.base_url + entitlement_path + ident(doi, pii))
        ent = data.get('entitlement-response', {}).get('document-entitlement', {})
        ok = ent.get('entitled')
        ok = ok if isinstance(ok, bool) else str(ok).lower() == 'true'
        return ok, None if ok else 'not entitled to this article'
    except client.ApiError as e:
        if e.status in (401, 403):
            return False, str(e)
        if e.status == 404:
            return False, 'not on ScienceDirect'
        raise


def fulltext(doi=None, pii=None):
    # plain text of the whole article, returns (text, nbytes)
    resp = client.get(config.base_url + article_path + ident(doi, pii), accept='text/plain')
    return resp.text, len(resp.content)


def pdf_to_file(path, max_bytes, doi=None, pii=None):
    url = config.base_url + article_path + ident(doi, pii)
    return client.stream_to_file(url, path, max_bytes, accept='application/pdf')

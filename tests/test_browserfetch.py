import os
import time

import pytest

from elsevier_research_mcp_utm import browserfetch, cache, config, fetch, fetchqueue, limits

pdf_bytes = b'%PDF-1.7\n' + b'x' * 2000


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    # invented metadata, no network; downloads go to a temp folder
    def get_abstract(doi):
        return {'paper': {'doi': doi, 'title': f'Paper {doi[-1]}', 'first_author': 'Tan A.', 'year': '2024',
                          'proxy_url': f'https://ezproxy.utm.my/login?url=https://doi.org/{doi}'}}
    monkeypatch.setattr(fetch.abstracts, 'get_abstract', get_abstract)
    monkeypatch.setattr(config, 'browser_downloads_dir', str(tmp_path / 'Downloads'))
    os.makedirs(config.browser_downloads_dir)


def drop(name, data=pdf_bytes):
    path = os.path.join(config.browser_downloads_dir, name)
    with open(path, 'wb') as f:
        f.write(data)
    return path


def test_start_counts_and_gives_link():
    r = browserfetch.start('10.1016/j.x.2024.1')
    assert r['ok'] and r['open_url'].startswith('https://ezproxy.utm.my/login?url=')
    assert r['save_as'].endswith('.pdf')
    assert limits.usage()['window_articles'] == 1


def test_start_twice_counts_once():
    browserfetch.start('10.1016/j.x.2024.1')
    browserfetch.start('10.1016/j.x.2024.1')
    assert limits.usage()['window_articles'] == 1


def test_start_refused_at_limit():
    for n in range(5):
        cache.log_fetch(f'10.1/{n}', 'pdf', 1000)
    r = browserfetch.start('10.1016/j.x.2024.1')
    assert not r['ok'] and 'limit' in r['reason'] and r['next_allowed']


def test_done_moves_newest_pdf_and_records_size():
    doi = '10.1016/j.x.2024.1'
    fetchqueue.add([doi])
    browserfetch.start(doi)
    src = drop('1-s2.0-S000-main.pdf')
    r = browserfetch.finish(doi, sleep=lambda s: None)
    assert r['ok'] and os.path.exists(r['path']) and not os.path.exists(src)
    assert os.path.dirname(r['path']) == config.download_dir
    assert cache.fetches_since(0)[-1][3] == len(pdf_bytes)
    assert fetchqueue.items('done')[0]['doi'] == doi
    assert browserfetch.start(doi)['already_saved'] == r['path']


def test_done_ignores_old_pdfs():
    old = drop('old.pdf')
    os.utime(old, (time.time() - 3600, time.time() - 3600))
    doi = '10.1016/j.x.2024.2'
    browserfetch.start(doi)
    r = browserfetch.finish(doi, wait_seconds=4, sleep=lambda s: None)
    assert not r['ok'] and 'no new PDF' in r['reason']


def test_done_refuses_non_pdf():
    doi = '10.1016/j.x.2024.3'
    browserfetch.start(doi)
    path = drop('login.pdf', b'<html>please log in</html>')
    r = browserfetch.finish(doi, path=path)
    assert not r['ok'] and 'NOT_PDF' in r['reason'] and os.path.exists(path)


def test_done_needs_start():
    with pytest.raises(ValueError):
        browserfetch.finish('10.1016/j.x.2024.4', sleep=lambda s: None)


def test_done_twice_needs_new_start():
    doi = '10.1016/j.x.2024.5'
    browserfetch.start(doi)
    drop('a.pdf')
    assert browserfetch.finish(doi, sleep=lambda s: None)['ok']
    drop('b.pdf')
    with pytest.raises(ValueError):
        browserfetch.finish(doi, sleep=lambda s: None)

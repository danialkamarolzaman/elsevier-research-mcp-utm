import os

import pytest

from elsevier_research_mcp_utm import config, doctor

# real Elsevier calls: run only on your own machine with
#   ERM_LIVE=1 and ELSEVIER_API_KEY set
live = pytest.mark.skipif(
    os.environ.get('ERM_LIVE') != '1' or not os.environ.get('ELSEVIER_API_KEY'),
    reason='set ERM_LIVE=1 and ELSEVIER_API_KEY to run live tests')


@live
def test_live_doctor(monkeypatch):
    monkeypatch.setattr(config, 'api_key', os.environ['ELSEVIER_API_KEY'])
    monkeypatch.setattr(config, 'insttoken', os.environ.get('ELSEVIER_INSTTOKEN', ''))
    r = doctor.run()
    assert r['api_key_valid'] is True
    assert r['tier'] in ('metadata', 'abstracts', 'fulltext')

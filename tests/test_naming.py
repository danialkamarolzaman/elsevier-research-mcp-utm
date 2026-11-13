from elsevier_research_mcp_utm import naming


def test_surname_forms():
    assert naming.surname('Xia L.') == 'Xia'
    assert naming.surname('Liqiao Xia') == 'Xia'
    assert naming.surname('Xia, Liqiao') == 'Xia'
    assert naming.surname('') == ''


def test_default_name():
    p = {'first_author': 'Liqiao Xia', 'year': 2022, 'title': 'Maintenance planning: a KG approach?'}
    assert naming.pdf_filename(p) == 'Xia 2022 - Maintenance planning a KG approach.pdf'


def test_missing_fields():
    assert naming.pdf_filename({'doi': '10.1/x'}) == 'Unknown n.d. - 10.1 x.pdf'


def test_custom_and_bad_template():
    p = {'first_author': 'A B', 'year': 2021, 'title': 'T', 'doi': '10.1/x'}
    assert naming.pdf_filename(p, '{doi}') == '10.1_x.pdf'
    assert naming.pdf_filename(p, '{nope}') == 'B 2021 - T.pdf'


def test_long_title_trimmed():
    name = naming.pdf_filename({'first_author': 'A', 'year': 2020, 'title': 'x' * 400})
    assert len(name) <= naming.max_len + 4

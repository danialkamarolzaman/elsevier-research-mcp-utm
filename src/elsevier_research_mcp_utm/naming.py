import re

from . import config

bad_chars = r'[<>:"/\\|?*\x00-\x1f]'  # not allowed in windows file names
max_len = 150


def surname(name):
    # 'Xia L.' (scopus) -> Xia, 'Liqiao Xia' (openalex) -> Xia
    name = (name or '').strip()
    if not name:
        return ''
    if ',' in name:
        return name.split(',')[0].strip()
    parts = name.split()
    if len(parts) > 1 and parts[-1].endswith('.'):
        return parts[0]
    return parts[-1]


def clean(text):
    text = re.sub(bad_chars, ' ', str(text))
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_len].rstrip(' .')


def pdf_filename(paper, template=None):
    template = template or config.pdf_name
    values = {
        'first_author': surname(paper.get('first_author')) or 'Unknown',
        'year': paper.get('year') or 'n.d.',
        'title': paper.get('title') or (paper.get('doi') or 'untitled'),
        'doi': (paper.get('doi') or '').replace('/', '_'),
        'journal': paper.get('journal') or '',
    }
    try:
        name = template.format(**values)
    except (KeyError, IndexError, ValueError):
        name = '{first_author} {year} - {title}'.format(**values)
    name = clean(name) or 'paper'
    return name if name.lower().endswith('.pdf') else name + '.pdf'

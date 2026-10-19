#!/usr/bin/env python3
"""Citation styles for the footnotes (on request only): Chicago, APA, Harvard, MLA.

The author's sources go into a JSON file (sources.json), each one under an id, with only the details the author wrote or
the user supplied — never invented ones. A footnote then cites a source by its id and the place in it as the author
wrote it:   {{مرجع|fatawa|٣/ ٤٥}}   and typeset.py writes the citation in the chosen style. The first citation of a source
is written in full where the style asks for that (Chicago), the later ones short; author-date styles (APA, Harvard)
and MLA write the short form every time. `@index مصدر` lists every source in the style's bibliography form.

A style leaves out what it does not use (APA names no place of publication): that is the style, not a loss. What the
style needs and the source lacks is reported, so the user can supply it:
    python3 cite.py sources.json --cite=chicago      prints one CITE line per source with missing details (Arabic, for the reply)

sources.json:
{ "fatawa": {"type": "book", "author": [{"name": "ابن تيمية", "full": "أحمد بن عبد الحليم ابن تيمية",
                                          "inverted": "ابن تيمية، أحمد بن عبد الحليم", "death": "٧٢٨هـ"}],
             "title": "مجموع الفتاوى", "short": "الفتاوى", "editor": "عبد الرحمن بن محمد بن قاسم",
             "place": "المدينة المنورة", "publisher": "مجمع الملك فهد", "year": "١٤١٦هـ"},
  "aune":   {"type": "article", "author": [{"family": "Aune", "given": "Kristin"}],
             "title": "Much Less Religious, A Little More Spiritual", "journal": "Feminist Review",
             "volume": "97", "issue": "1", "year": "2011", "pages": "32-55"} }
type: book | article | chapter | thesis | web | manuscript.  Fields: author (list), title, short, editor, translator,
edition, volumes, place, publisher, year, journal, volume, issue, pages, container (the book a chapter is in),
degree, university, site, url, accessed, date, library, number."""
import json, re, sys

STYLES = ('chicago', 'apa', 'harvard', 'mla')
NAMES = {'chicago': 'Chicago', 'apa': 'APA', 'harvard': 'Harvard', 'mla': 'MLA'}
FIELD_AR = {'author': 'المؤلف', 'title': 'العنوان', 'place': 'مكان النشر', 'publisher': 'الناشر', 'year': 'سنة النشر',
            'journal': 'اسم المجلة', 'volume': 'رقم المجلد', 'issue': 'رقم العدد', 'pages': 'الصفحات', 'degree': 'الدرجة العلمية',
            'university': 'الجامعة', 'url': 'الرابط', 'accessed': 'تاريخ الاطلاع', 'library': 'مكان المخطوط', 'container': 'الكتاب الجامع',
            'site': 'اسم الموقع'}
NEEDS = {   # (type, style) -> details the style cannot do without
    'book': {'chicago': 'author title place publisher year', 'apa': 'author year title publisher',
             'harvard': 'author year title place publisher', 'mla': 'author title publisher year'},
    'article': {s: 'author title journal year pages' for s in STYLES},
    'chapter': {'chicago': 'author title container place publisher year pages', 'apa': 'author year title container publisher pages',
                'harvard': 'author year title container place publisher pages', 'mla': 'author title container publisher year pages'},
    'thesis': {s: 'author title degree university year' for s in STYLES},
    'web': {'chicago': 'title site url accessed', 'apa': 'title site url', 'harvard': 'title url accessed', 'mla': 'title site url'},
    'manuscript': {s: 'author title library' for s in STYLES},
}

AR = re.compile(r'[؀-ۿ]')
def arabic(src): return bool(AR.search(src.get('title', '') + ''.join(a.get('name', '') for a in src.get('author', []))))

def person(a, ar):
    """-> (short, full, inverted) forms of a name."""
    if 'family' in a:   # a Latin name
        full = (a.get('given', '') + ' ' + a['family']).strip()
        return a['family'], full, (a['family'] + (', ' + a['given'] if a.get('given') else ''))
    short = a.get('name') or a.get('full', '')
    full = a.get('full') or short
    return short, full, a.get('inverted') or full

def names(src, form, ar, death=True):
    au = src.get('author') or []
    xs = [person(a, ar)[form] + (f' (ت: {a["death"]})' if death and ar and a.get('death') and form != 0 else '') for a in au]
    if not xs: return ''
    if len(xs) == 1: return xs[0]
    if ar: return '، '.join(xs[:-1]) + ' و' + xs[-1]
    return ', '.join(xs[:-1]) + ', and ' + xs[-1] if form == 1 else '; '.join(xs[:-1]) + ', and ' + xs[-1]

B, I = '**', ('⟨', '⟩')   # bold, and italic (typeset.py's own marks)
def work(t, ar): return f'{B}{t}{B}' if ar else f'{I[0]}{t}{I[1]}'   # titles of whole works: bold in Arabic, italic in Latin
def part(t, ar): return f'«{t}»' if ar else f'"{t}"'                  # titles of parts: articles, chapters, web pages

def paren(head, pub):   # Chicago: the publication details in brackets right after what they belong to, «… (Place: Publisher, Year)»
    return head + (f' ({pub})' if pub else '')

def join(bits, sep):
    return sep.join(b for b in bits if b)

def details(src, ar, style):
    """Editor, translator and edition, as the style writes them."""
    if ar:
        return [f'تحقيق: {src["editor"]}' if src.get('editor') else '', f'ترجمة: {src["translator"]}' if src.get('translator') else '',
                f'ط{src["edition"]}' if src.get('edition') else '']
    return [f'edited by {src["editor"]}' if src.get('editor') else '', f'translated by {src["translator"]}' if src.get('translator') else '',
            f'{src["edition"]} ed.' if src.get('edition') else '']

def pubinfo(src, ar, with_place=True):
    c, s = ('، ', ': ') if ar else (', ', ': ')
    pub = join([src.get('publisher', ''), src.get('year', '')], c)
    if with_place and src.get('place'): return src['place'] + (s + pub if pub else '')
    return pub

def note(src, loc, style, first):
    """The citation as it stands in a footnote, without its closing full stop (typeset.py adds one when the citation
    ends the note)."""
    ar = arabic(src); c = '، ' if ar else ', '; end = ''
    t = src.get('type', 'book'); title = src.get('title', ''); short = src.get('short') or title
    loc = loc.strip()
    if style in ('apa', 'harvard'):   # author-date
        who = names(src, 0, ar) or part(title, ar)
        if style == 'apa': return join([f'{who} ({src.get("year", "")})' if src.get('year') else who, loc], c) + end
        return join([f'{who} {src.get("year", "")}'.strip(), loc], c) + end
    if style == 'mla':
        return join([names(src, 0, ar) or part(title, ar), work(short, ar) if t != 'article' else part(short, ar), loc], c) + end
    # chicago: full the first time, short after
    if not first:
        return join([names(src, 0, ar), work(short, ar) if t not in ('article', 'chapter', 'web') else part(short, ar), loc], c) + end
    who = names(src, 1, ar)
    if t == 'article':
        vol = join([src.get('volume', ''), (('ع' if ar else 'no. ') + src['issue']) if src.get('issue') else ''], c)
        return join([who, part(title, ar), join([work(src.get('journal', ''), ar), vol], ' ') + (f' ({src["year"]})' if src.get('year') else '') + (': ' + loc if loc else '')], c) + end
    if t == 'chapter':
        inn = ('في: ' if ar else 'in ') + work(src.get('container', ''), ar)
        return join([paren(join([who, part(title, ar), inn] + details(src, ar, style), c), pubinfo(src, ar)), loc], c) + end
    if t == 'thesis':
        return join([who, work(title, ar), f'({join([src.get("degree", ""), src.get("university", ""), src.get("year", "")], c)})', loc], c) + end
    if t == 'web':
        acc = (('تاريخ الاطلاع: ' if ar else 'accessed ') + src['accessed']) if src.get('accessed') else ''
        return join([who, part(title, ar), src.get('site', ''), src.get('date', ''), acc, src.get('url', '')], c) + end
    if t == 'manuscript':
        return join([who, work(title, ar), join([src.get('library', ''), src.get('number', '')], ' '), loc], c) + end
    return join([paren(join([who, work(title, ar)] + details(src, ar, style), c), pubinfo(src, ar)), loc], c) + end

def bib(src, style):
    """The source as it stands in the list of sources (فهرس المصادر والمراجع)."""
    ar = arabic(src); c = '، ' if ar else ', '; d = '. '
    t = src.get('type', 'book'); title = src.get('title', '')
    who = names(src, 2, ar, death=style in ('chicago', 'mla')); year = src.get('year', '')
    if style == 'apa' and not ar:   # APA: family name and initials, «Aune, K.»
        au = [x for x in src.get('author') or [] if 'family' in x]
        if au: who = ', & '.join(x['family'] + (', ' + ' '.join(g[0] + '.' for g in x.get('given', '').split() if g) if x.get('given') else '') for x in au).rstrip('.')
    ttl = part(title, ar) if t in ('article', 'chapter', 'web') else work(title, ar)
    if t == 'article' and style == 'apa': ttl = title   # APA quotes no article title
    if t == 'article':
        j, v, n, pg = work(src.get('journal', ''), ar), src.get('volume', ''), src.get('issue', ''), src.get('pages', '')
        if style in ('apa', 'harvard'):
            cont = join([j, v + (f'({n})' if n else '') if v else (f'({n})' if n else ''), (('ص ' if ar else ('pp. ' if style == 'harvard' else '')) + pg) if pg else ''], c)
        elif style == 'mla':
            cont = join([j, (('مج ' if ar else 'vol. ') + v) if v else '', (('ع ' if ar else 'no. ') + n) if n else '', year, (('ص ' if ar else 'pp. ') + pg) if pg else ''], c)
            return join([who, ttl, cont], d) + '.'
        else:   # chicago: «Journal 97, no. 1 (2011): 32–55»
            cont = join([j + (' ' + v if v else ''), (('ع ' if ar else 'no. ') + n) if n else ''], c) + (f' ({year})' if year else '') + (': ' + pg if pg else '')
            return join([who, ttl, cont], d) + '.'
    elif t == 'chapter':
        cont = join([('في: ' if ar else 'In ') + work(src.get('container', ''), ar)] + details(src, ar, style) + [src.get('pages', '')], c)
    elif t == 'thesis':
        cont = join([src.get('degree', ''), src.get('university', '')], c)
    elif t == 'web':
        acc = (('تاريخ الاطلاع: ' if ar else 'Accessed ') + src['accessed']) if src.get('accessed') else ''
        cont = join([src.get('site', ''), src.get('date', ''), acc, src.get('url', '')], c)
    elif t == 'manuscript':
        cont = join([src.get('library', ''), src.get('number', '')], ' ')
    else:
        cont = join(details(src, ar, style), c)
    if style == 'apa':
        pub = src.get('publisher', '') if t in ('book', 'chapter') else ''
        return join([who, f'({year})' if year else '', ttl, cont, pub], d).replace('..', '.') + '.'
    if style == 'harvard':
        pub = pubinfo(src, ar) if t in ('book', 'chapter') else ''
        pub = pub[:-len(c + year)] if year and pub.endswith(c + year) else pub
        return join([f'{who} ({year})' if year else who, ttl, cont, pub], d) + '.'
    if style == 'mla':
        pub = join([src.get('publisher', ''), year], c) if t in ('book', 'chapter', 'thesis') else year
        return join([who, ttl, join([cont, pub], c)], d) + '.'
    pub = pubinfo(src, ar) if t in ('book', 'chapter') else year
    return join([who, ttl, cont, pub], d) + '.'

def sort_name(src):
    au = src.get('author') or []
    return person(au[0], arabic(src))[2] if au else src.get('title', '')

def missing(src, style):
    need = NEEDS.get(src.get('type', 'book'), NEEDS['book'])[style].split()
    out = []
    for f in need:
        if f == 'author': ok = bool(src.get('author'))
        elif f == 'pages' and src.get('type') == 'article': ok = bool(src.get('pages'))
        else: ok = bool(str(src.get(f, '')).strip())
        if not ok: out.append(f)
    return out

def report(sources, style):
    """One line per source that lacks what the style needs — in Arabic, for the reply."""
    out = []
    for sid, src in sources.items():
        m = missing(src, style)
        if m: out.append(f'CITE: ينقص «{src.get("title") or sid}» لنظام {NAMES[style]}: ' + '، '.join(FIELD_AR.get(f, f) for f in m))
    return out

def load(path):
    data = json.load(open(path, encoding='utf-8'))
    if not isinstance(data, dict): sys.exit('sources file: expected an object of id -> source')
    return data

if __name__ == '__main__':
    style = next((a.split('=', 1)[1].lower() for a in sys.argv if a.startswith('--cite=')), None)
    files = [a for a in sys.argv[1:] if not a.startswith('--')]
    if style not in STYLES or not files: sys.exit('usage: cite.py sources.json --cite=chicago|apa|harvard|mla')
    lines = report(load(files[0]), style)
    print('\n'.join(lines) if lines else 'CITE: complete')

"""Every answer of the assistant is checked here before it touches the document. What fails a check is dropped (and
counted), never repaired by guessing. The functions take the paragraphs as {number: text} and return what may be
applied plus the list of what was dropped and why."""
import os, re, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'skill', 'saffaf', 'scripts'))
import indexes
from assist.tasks import KINDS_MARKABLE, SOURCE_FIELDS

FORBIDDEN = re.compile(r'\[\^|\*\*|\{\{|\}\}|⟦|⟧|`')   # the engine's own markup: a mark may not cut through it

def labels(answer, paragraphs):
    """structure → {i: role} for known paragraphs and known roles."""
    out, dropped = {}, []
    for x in answer.get('labels', []):
        if x.get('i') not in paragraphs: dropped.append(('unknown paragraph', x)); continue
        if x.get('role') not in ('h1', 'h2', 'h3', 'center'): dropped.append(('unknown role', x)); continue
        out[x['i']] = x['role']
    return out, dropped

def spans(items, paragraphs):
    """Common checks for spans: inside the paragraph, not empty, not cutting the engine's markup, not overlapping."""
    ok, dropped, taken = [], [], {}
    for x in items:
        t = paragraphs.get(x.get('i'))
        s, e = x.get('start'), x.get('end')
        if t is None or not isinstance(s, int) or not isinstance(e, int) or not 0 <= s < e <= len(t):
            dropped.append(('outside the paragraph', x)); continue
        piece = t[s:e]
        if not piece.strip() or FORBIDDEN.search(piece) or piece != piece.strip():
            dropped.append(('not a clean span of words', x)); continue
        if any(not (e <= a or s >= b) for a, b in taken.get(x['i'], [])):
            dropped.append(('overlaps another', x)); continue
        taken.setdefault(x['i'], []).append((s, e)); ok.append(dict(x, words=piece))
    return ok, dropped

def marks(answer, paragraphs):
    """index marks → {i: new paragraph text with {{kind|words|entry}}}, guaranteed to give back the author's text when
    the marks are taken out (the engine's own strip_marks)."""
    whole = '\n'.join(paragraphs.values())
    cand = []
    dropped = []
    for x in answer.get('marks', []):
        if x.get('kind') not in KINDS_MARKABLE: dropped.append(('unknown kind', x)); continue
        cand.append(x)
    ok, d2 = spans(cand, paragraphs); dropped += d2
    out = {}
    for i in {x['i'] for x in ok}:
        t = paragraphs[i]
        for x in sorted((y for y in ok if y['i'] == i), key=lambda y: -y['start']):
            entry = (x.get('entry') or '').strip()
            if entry and entry != x['words'] and entry not in whole:   # another form only when the author uses it
                dropped.append(('entry not in the text', x)); entry = ''
            if '|' in x['words'] or '|' in entry: dropped.append(('a bar in the words', x)); continue
            mark = '{{' + x['kind'] + '|' + x['words'] + ('|' + entry if entry and entry != x['words'] else '') + '}}'
            t = t[:x['start']] + mark + t[x['end']:]
        if indexes.strip_marks(t) != paragraphs[i]:   # never: the marks must leave the author's words as they were
            dropped.append(('text changed', {'i': i})); continue
        out[i] = t
    return out, dropped

def sources(answer, notes, text, supplied=None):
    """citation style → (sources.json dict, {note: new note text}, missing details per source, dropped).
    A source keeps only the details that stand verbatim in the author's text or that the user supplied; a reference
    in a note is replaced by {{مرجع|id|place}} only when its place is written inside it."""
    supplied = supplied or {}
    src, dropped, missing = {}, [], {}
    for s in answer.get('sources', []):
        sid = re.sub(r'[^A-Za-z0-9_\-]', '', s.get('id') or '')
        if not sid or sid in src: dropped.append(('bad id', s)); continue
        entry = {'type': s.get('type') if s.get('type') in ('book', 'article', 'chapter', 'thesis', 'web', 'manuscript') else 'book'}
        for f in SOURCE_FIELDS:
            v = (supplied.get(sid, {}).get(f) or s.get(f) or '').strip() if f != 'type' else None
            if not v: continue
            if v in text or supplied.get(sid, {}).get(f): entry[f] = v
            else: missing.setdefault(sid, []).append(f)   # not in the author's text: asked of the user, never kept
        au = [a.strip() for a in s.get('authors') or [] if a.strip()]
        kept = [a for a in au if a in text or a in (supplied.get(sid, {}).get('authors') or [])]
        if len(kept) < len(au): missing.setdefault(sid, []).append('author')
        if kept: entry['author'] = [{'name': a} for a in kept]
        if 'title' not in entry: dropped.append(('title not in the text', s)); continue
        src[sid] = entry
    cites, d2 = spans([dict(c, i=c.get('note')) for c in answer.get('cites', []) if c.get('id') in src], notes)
    dropped += d2
    out = {}
    for n in {c['i'] for c in cites}:
        t = notes[n]
        for c in sorted((c for c in cites if c['i'] == n), key=lambda c: -c['start']):
            place = (c.get('place') or '').strip()
            if place and place not in c['words']: dropped.append(('place not in the reference', c)); continue
            t = t[:c['start']] + '{{مرجع|' + c['id'] + ('|' + place if place else '') + '}}' + t[c['end']:]
        out[n] = t
    return src, out, missing, dropped

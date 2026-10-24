"""The structure of a draft (to_md.py's output): which lines are headings, centred lines, cover details, footnotes and
tables. Rules suggest a role for each line, the user reviews them, and the in.md the engine reads is built from the
roles. Nothing here edits the author's words: a role only adds or removes the engine's own markup at the head of a line
(«# », «>> »), moves a line of the author's into the cover, links a footnote number to its note, or joins the cells
of a table. `verify` rebuilds the author's lines from the in.md and compares them with the draft, character by
character; the service refuses to typeset when they differ."""
import re

ROLES = ('p', 'h1', 'h2', 'h3', 'center')
PREFIX = {'p': '', 'h1': '# ', 'h2': '## ', 'h3': '### ', 'center': '>> '}
COVER = {'c_title': 'title', 'c_line': 'line', 'c_author': 'author', 'c_affil': 'affiliation', 'c_date': 'date'}
EDITABLE = ROLES + tuple(COVER)

NOTE_DEF = re.compile(r'^\[\^([^\]]+)\]:[ \t]?(.*)$')
TABLE_ROW = re.compile(r'^\|.*\|\s*$')
TABLE_SEP = re.compile(r'^\|(?:\s*:?-{3,}:?\s*\|)+\s*$')
LIST = re.compile(r'^(?:\* |- |-- )')
HEAD = re.compile(r'^(#{1,3}) (.*)$')
CENTER = re.compile(r'^>> ?(.*)$')
SEPARATOR = re.compile(r'^[\s_\-ـ*=~—–.·]{3,}$')   # a line with no letters that only separates the text from its notes

AR_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
END_PUNCT = re.compile(r'[.،؛,;!؟?…]\s*$')

def visible(line):
    """What the reader sees of a line of the draft or of the in.md: the engine's markup at its head and the bold marks
    taken out (to_md.py writes «**» only where the Word file had bold)."""
    m = HEAD.match(line)
    if m: line = m.group(2)
    else:
        m = CENTER.match(line)
        if m: line = m.group(1)
    return line.replace('**', '')

def words(t): return len(t.split())

# ---------------------------------------------------------------- the draft as items

def parse(draft):
    """-> items, one per line of the draft. Text lines (paragraphs, headings, centred lines) carry an editable role;
    the others (footnotes, tables, lists, the engine's own lines) are kept as they are."""
    lines = draft.split('\n')
    items = []; i = 0
    if lines and lines[0].strip() == '---' and '---' in [l.strip() for l in lines[1:]]:   # a front-matter block (.md input)
        end = [l.strip() for l in lines].index('---', 1)
        for k in range(end + 1): items.append(dict(i=k, kind='front', raw=lines[k]))
        i = end + 1
    for k in range(i, len(lines)):
        l = lines[k]
        if not l.strip(): kind = 'blank'
        elif NOTE_DEF.match(l): kind = 'note'
        elif TABLE_SEP.match(l) or TABLE_ROW.match(l): kind = 'table'
        elif l.startswith('@'): kind = 'directive'
        elif LIST.match(l): kind = 'list'
        else: kind = 'text'
        it = dict(i=k, kind=kind, raw=l)
        if kind == 'text':
            m = HEAD.match(l); c = CENTER.match(l)
            it['role'] = {1: 'h1', 2: 'h2', 3: 'h3'}[len(m.group(1))] if m else 'center' if c else 'p'
            it['orig_role'] = it['role']
            it['text'] = visible(l)
            it['bold'] = l.strip().startswith('**') and l.strip().endswith('**') and l.count('**') == 2
        items.append(it)
    return items

# ---------------------------------------------------------------- rules

H1_WORDS = re.compile(r'^(?:المقدمة|مقدمة|التمهيد|تمهيد|الخاتمة|خاتمة|المبحث|مبحث|الفصل|الباب|المصادر|المراجع|قائمة المصادر|'
                      r'قائمة المراجع|ثبت المصادر|فهرس المصادر|الملاحق|ملحق|النتائج|التوصيات|الإهداء|إهداء|الشكر والتقدير|'
                      r'شكر وتقدير|المستخلص|مستخلص|ملخص البحث|الملخص|Abstract)(?![ء-ي])')
H2_WORDS = re.compile(r'^(?:المطلب|مطلب|المسألة|الفرع)(?![ء-ي])')
BYLINE = re.compile(r'^(?:إعداد|اعداد|بقلم|تأليف|كتبه|الباحث|الباحثة|الدكتور|الدكتورة|د\.|أ\.\s*د\.)(?![ء-ي])')
SAYS = re.compile(r'^(?:قال|وقال|قوله|يقول)(?![ء-ي])')

def suggest(items, source):
    """Suggest roles for text lines that have none yet (paragraphs). source: 'text' (pasted text, .txt, .md) or 'word'
    (any document converted by to_md.py). Lines that already carry a heading from Word's styles are left alone.
    -> number of suggestions; each suggested item gets 'role', 'suggested' and 'why'."""
    texts = [it for it in items if it['kind'] == 'text']
    has_h = any(it['role'] != 'p' for it in texts)
    n = 0
    def put(it, role, why):
        nonlocal n
        if it['role'] == role: return
        it['role'] = role; it['suggested'] = True; it['why'] = why; n += 1
    for k, it in enumerate(texts):
        if it['role'] != 'p': continue
        t = it['text'].strip(); w = words(t)
        if not t: continue
        if w <= 12 and H1_WORDS.match(t) and not END_PUNCT.search(t): put(it, 'h1', 'يبدأ بكلمة عنوان رئيسي'); continue
        if w <= 14 and H2_WORDS.match(t) and not END_PUNCT.search(t): put(it, 'h2', 'يبدأ بكلمة عنوان فرعي'); continue
        if w <= 8 and re.search(r'[:：]\s*$', t) and not SAYS.match(t) and (it['bold'] or source == 'text'):
            put(it, 'h3', 'سطر قصير ينتهي بنقطتين'); continue
        if source == 'word' and it['bold'] and w <= 12 and not END_PUNCT.search(t): put(it, 'h2', 'سطر قصير كله عريض'); continue
    # the article's title: the first line, short, with no closing punctuation
    first = next((it for it in texts if it['text'].strip()), None)
    if first and first['role'] == 'p' and not has_h and words(first['text']) <= 15 and not END_PUNCT.search(first['text'].strip()) \
            and not re.search(r'[:：]\s*$', first['text']) and not front_matter(items):
        put(first, 'h1', 'السطر الأول قصير: عنوان المقالة')
    # the writer's line under the title
    if first and first['role'] == 'h1':
        k = texts.index(first)
        for it in texts[k + 1:k + 3]:
            t = it['text'].strip()
            if it['role'] == 'p' and words(t) <= 12 and (BYLINE.match(t) or (t.startswith('(') and t.endswith(')'))):
                put(it, 'center', 'سطر تحت العنوان: اسم الكاتب أو تعريف')
    return n

def front_matter(items): return any(it['kind'] == 'front' for it in items)

# ---------------------------------------------------------------- plain text: footnotes and tables

NOTE_LINE = re.compile(r'^(\s*\(\s*([0-9٠-٩]+)\s*\)\s*)(.+)$')

def pair_notes(items):
    """Pasted text often ends with its notes: «(١) …» lines after the text, numbered 1, 2, 3 … in the order their
    numbers «(١)» appear in it. When that is unambiguous — every number in the text once, in order, and nowhere else —
    each number becomes a footnote reference and its line the note. -> (count, problem in Arabic or '')."""
    body = [it for it in items if it['kind'] == 'text']
    # the notes: the run of numbered lines at the end (blank lines and a separator line may stand between them)
    run = []; sep = []
    for it in reversed(items):
        if it['kind'] == 'blank': continue
        if it['kind'] == 'text' and it['role'] == 'p' and NOTE_LINE.match(it['raw']): run.append(it); continue
        break
    run.reverse()
    if not run: return 0, ''
    first = items.index(run[0])
    for it in reversed(items[:first]):   # a separator line just above the notes
        if it['kind'] == 'blank': continue
        if it['kind'] == 'text' and SEPARATOR.match(it['raw']): sep.append(it)
        break
    nums = [int(NOTE_LINE.match(it['raw']).group(2).translate(AR_DIGITS)) for it in run]
    if nums != list(range(1, len(nums) + 1)):
        return 0, 'الحواشي في آخر نصك ليست مرقّمة ١، ٢، ٣… على التوالي (لعل ترقيمها يبدأ من جديد في كل صفحة)، فبقيت كما كتبتَها'
    text = [it for it in body if it not in run and it not in sep]
    places = []
    for n in nums:
        found = []
        for it in text:
            for m in re.finditer(r'\(\s*(?:%d|%s)\s*\)' % (n, str(n).translate(str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩'))), it['raw']):
                found.append((it, m))
        if len(found) != 1:
            return 0, f'الرقم ({n}) ورد في نصك {"أكثر من مرة" if found else "بلا موضع"}، فلم أربط الحواشي بمواضعها وبقيت كما كتبتَها'
        places.append(found[0])
    order = [(text.index(it), m.start()) for it, m in places]
    if order != sorted(order): return 0, 'أرقام الحواشي في نصك ليست على ترتيب ورودها، فبقيت كما كتبتَها'
    for n, ((it, m), note) in enumerate(zip(places, run), 1):
        it.setdefault('refs', []).append(dict(label=f'n{n}', start=m.start(), end=m.end(), marker=m.group(0)))
        nm = NOTE_LINE.match(note['raw'])
        note['kind'] = 'pnote'; note['label'] = f'n{n}'; note['prefix'] = nm.group(1); note['note'] = nm.group(3)
    for it in sep: it['kind'] = 'sep'
    return len(run), ''

def tables(items):
    """Lines separated by tabs, two or more in a row with the same number of cells, become a table."""
    out = 0; k = 0
    while k < len(items):
        grp = []
        while k + len(grp) < len(items):
            it = items[k + len(grp)]
            if it['kind'] == 'text' and it['role'] == 'p' and '\t' in it['raw'].strip('\t') and '|' not in it['raw'] \
                    and (not grp or it['raw'].count('\t') == grp[0]['raw'].count('\t')):
                grp.append(it)
            else: break
        if len(grp) >= 2:
            for j, it in enumerate(grp): it['kind'] = 'ttable'; it['head'] = j == 0
            out += 1; k += len(grp)
        else: k += 1
    return out

# ---------------------------------------------------------------- in.md

def render(items):
    """-> (body lines of in.md, cover {key: [values]}, cover item indexes). The front matter and the engine's own lines
    (@toc, @index …) are added by the caller."""
    body = []; cover = {}; moved = []
    for it in items:
        k = it['kind']
        if k == 'front':   # a front-matter block the author's .md file already has: its details go to the cover
            key, colon, v = it['raw'].partition(':')
            if colon and it['raw'].strip() != '---': cover.setdefault(key.strip(), []).append(v.strip())
            continue
        if k == 'sep': continue
        if k == 'text':
            r = it['role']
            if r in COVER:
                cover.setdefault(COVER[r], []).append(it['text'].strip()); moved.append(it['i']); continue
            line = it['raw']
            if it.get('refs'):
                for ref in sorted(it['refs'], key=lambda x: -x['start']):
                    line = line[:ref['start']] + f'[^{ref["label"]}]' + line[ref['end']:]
            t = visible(line)
            if r == 'p' and it['orig_role'] == 'p': body.append(line)   # untouched: bold marks and all
            elif r == 'p': body.append(t if not it['bold'] else '**' + t + '**')
            else: body.append(PREFIX[r] + (t.strip() if r != 'center' or not it['bold'] else t.strip()))
        elif k == 'pnote': body.append(f'[^{it["label"]}]: {it["note"]}')
        elif k == 'ttable':
            cells = it['raw'].split('\t')
            body.append('| ' + ' | '.join(c.strip() for c in cells) + ' |')
            if it['head']: body.append('|' + '---|' * len(cells))
        elif k == 'blank': body.append('')
        else: body.append(it['raw'])
    return body, cover, moved

def strip_engine(line):
    """A line of the in.md as the author's words: headings and centred lines without their markup, footnote
    definitions as they were, the engine's own lines dropped (None)."""
    if line.startswith('@'): return None
    if TABLE_SEP.match(line): return None
    return visible(line)

def verify(items, in_md_body, cover, typed=None):
    """Rebuild the author's lines from the in.md body and the cover, and compare them with the draft. -> list of
    differences (empty when nothing of the author's changed). typed: cover details the user typed in the form (allowed:
    they are the user's own words, not the document's)."""
    problems = []
    # what the draft says: its lines, in order, as the reader sees them (blank lines and separator lines aside)
    want = []
    for it in items:
        if it['kind'] in ('blank', 'front', 'sep') or it['kind'] == 'directive': continue
        if it['kind'] == 'text' and it['role'] in COVER: continue
        if it['kind'] == 'table' and TABLE_SEP.match(it['raw']): continue
        if it['kind'] == 'ttable': want.append('\t'.join(c.strip() for c in it['raw'].split('\t'))); continue
        want.append(it['raw'].replace('**', '') if it['kind'] == 'text' and it['orig_role'] == 'p' else visible(it['raw']))
    # what the in.md says, the links of pasted notes undone
    marker = {}; prefix = {}
    for it in items:
        for ref in it.get('refs', []): marker[ref['label']] = ref['marker']
        if it['kind'] == 'pnote': prefix[it['label']] = it['prefix']
    got = []
    for line in in_md_body:
        if not line.strip(): continue
        m = NOTE_DEF.match(line)
        if m and m.group(1) in prefix: got.append(prefix[m.group(1)] + m.group(2)); continue
        if TABLE_ROW.match(line) and not TABLE_SEP.match(line) and any(it['kind'] == 'ttable' for it in items) \
                and not any(it['kind'] == 'table' and it['raw'] == line for it in items):
            got.append('\t'.join(c.strip() for c in line.strip()[1:-1].split('|'))); continue
        s = strip_engine(line)
        if s is None: continue
        s = re.sub(r'\[\^(n\d+)\]', lambda mm: marker.get(mm.group(1), mm.group(0)), s)
        got.append(s)
    if len(want) != len(got): problems.append(f'عدد الأسطر تغيّر: {len(want)} ← {len(got)}')
    for a, b in zip(want, got):
        if a.strip() != b.strip(): problems.append(f'تغيّر سطر: «{a[:60]}» ← «{b[:60]}»'); break
    # the cover: every value is a line of the document (moved there by its role) or typed by the user
    lines = {it['text'].strip() for it in items if it['kind'] == 'text' and it['role'] in COVER}
    lines |= {it['raw'].partition(':')[2].strip() for it in items if it['kind'] == 'front'}
    typed = typed or {}
    for key, vals in cover.items():
        for v in vals:
            if v not in lines and v not in (typed.get(key) if isinstance(typed.get(key), list) else [typed.get(key)]):
                problems.append(f'بيان في الغلاف ليس من النص ولا مما أدخلتَه: «{v[:60]}»')
    return problems

def summary(items):
    t = [it for it in items if it['kind'] == 'text']
    return dict(h1=sum(it['role'] == 'h1' for it in t), h2=sum(it['role'] == 'h2' for it in t),
                h3=sum(it['role'] == 'h3' for it in t), center=sum(it['role'] == 'center' for it in t),
                paragraphs=sum(it['role'] == 'p' for it in t),
                notes=sum(it['kind'] in ('note', 'pnote') for it in items),
                tables=sum(1 for k, it in enumerate(items) if it['kind'] in ('table', 'ttable') and (k == 0 or items[k - 1]['kind'] not in ('table', 'ttable'))),
                suggested=sum(1 for it in t if it.get('suggested')))

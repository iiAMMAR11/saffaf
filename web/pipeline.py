"""The path of one document through the service: receive → convert (to_md.py) → structure → in.md → make.py →
check that the author's text is in the Word file unchanged → preview pages → files.

The engine (skill/saffaf/scripts) is used as it is, through its command lines."""
import os, re, json, glob, zipfile, subprocess
from xml.etree import ElementTree as ET
import structure, messages
from jobs import SCRIPTS, run
import sys; sys.path.insert(0, SCRIPTS)
import indexes   # the engine's own: index marks are taken out the way typeset.py takes them out

TEXT_EXT = ('.txt', '.md', '.markdown', '.text')
WORD_EXT = ('.docx', '.docm', '.dotx', '.dotm')
LO_EXT = ('.doc', '.odt', '.ott', '.rtf', '.html', '.htm', '.xhtml', '.wpd', '.fodt', '.epub')
REFUSED_EXT = ('.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.heic', '.heif', '.tif', '.tiff', '.bmp', '.svg')
MAGIC = (b'%PDF', b'\x89PNG', b'\xff\xd8\xff', b'GIF8', b'II*\x00', b'MM\x00*')
MAX_BYTES = int(os.environ.get('SAFFAF_MAX_UPLOAD', 15 * 1024 * 1024))
TRAD_ENABLED = os.environ.get('SAFFAF_ENABLE_MS_FONTS', '1') == '1'   # Traditional Arabic / the thesis profile (licence open)

class Refused(Exception):
    pass

def safe_name(name):
    base = os.path.splitext(os.path.basename(name or ''))[0]
    base = re.sub(r'[^\w؀-ۿ\- ]+', '', base).strip()[:60]
    return base or 'مستند'

# ---------------------------------------------------------------- receive and convert

def receive(job, filename=None, data=None, text=None):
    """Store the source; refuse PDF and images before anything else. -> path of the source."""
    if text is not None:
        if not text.strip(): raise Refused('الصق النص أولًا.')
        p = job.path('src', 'نص.txt')
        with open(p, 'w', encoding='utf-8') as f: f.write(text)
        job.data.update(source='text', name='نص', ext='.txt')
        return p
    ext = os.path.splitext(filename or '')[1].lower()
    if len(data) > MAX_BYTES: raise Refused('الملف أكبر من الحدّ المسموح في هذه النسخة (١٥ ميغابايت).')
    if ext in REFUSED_EXT or data[:4] in MAGIC or data[:3] == b'\xff\xd8\xff' or (data[:4] == b'RIFF' and data[8:12] == b'WEBP'):
        raise Refused(messages.REFUSE_PDF)
    if ext not in TEXT_EXT + WORD_EXT + LO_EXT: raise Refused(messages.unknown_format(ext))
    p = job.path('src', 'source' + ext)
    with open(p, 'wb') as f: f.write(data)
    job.data.update(source='text' if ext in TEXT_EXT else 'word', name=safe_name(filename), ext=ext)
    return p

def convert(job, src, symbols=False):
    """to_md.py → draft.md. -> dict(draft, report lines, warnings (Arabic), damaged examples, symbols line)."""
    draft = job.path('draft.md' if not symbols else 'draft-symbols.md')
    code, out, err = run(job, [os.path.join(SCRIPTS, 'to_md.py'), src, draft] + (['--symbols'] if symbols else []), timeout=360)
    if code is None: raise Refused('توقّف تحويل الملف لأنه طال أكثر من المعتاد. جرّب حفظه بصيغة DOCX ثم أرسله.')
    if code != 0:
        if 'PDF is not accepted' in (err or ''): raise Refused(messages.REFUSE_PDF)
        raise Refused('لم أستطع قراءة هذا الملف. احفظه بصيغة DOCX ثم أرسله، أو الصق النص نفسه.')
    lines = out.splitlines()
    warnings = messages.translate([l[len('WARNING: '):] for l in lines if l.startswith('WARNING: ')], messages.TO_MD)
    dmg = next((l for l in lines if l.startswith('DAMAGED')), None)
    examples = []
    if dmg:
        m = re.search(r'\(([^)]*)…?\)', dmg)
        examples = [w.strip(' …') for w in (m.group(1) if m else '').split('،') if w.strip(' …')][:2]
    sym = [l for l in lines if l.startswith('SYMBOLS: ')]
    notes = re.search(r'notes: (\d+)', out)
    with open(draft, encoding='utf-8') as f: text = f.read()
    return dict(draft=text, warnings=warnings, damaged=examples if dmg else None,
                symbols=sym, notes=int(notes.group(1)) if notes else 0)

def docx_checks(job):
    """What the Word file holds that the engine does not carry over: pictures, equations, merged table cells. Read
    from the Word file itself (or from LibreOffice's Word copy of another format, left in the job's temporary folder)."""
    cands = [job.path('src', 'source' + job.data['ext'])] if job.data.get('ext') in ('.docx', '.docm', '.dotx', '.dotm') else \
            glob.glob(job.path('tmp', '**', '*.docx'), recursive=True)
    out = []
    for p in cands[:1]:
        try: xml = zipfile.ZipFile(p).read('word/document.xml').decode('utf-8', 'replace')
        except Exception: continue
        pics = len(re.findall(r'<pic:pic\b|<v:imagedata\b', xml))
        maths = len(re.findall(r'<m:oMath\b', xml))
        merged = len(re.findall(r'<w:gridSpan w:val="[2-9]|<w:vMerge\b', xml))
        if pics: out.append(f'في ملفك صور أو أشكال ({messages.ar(pics)}) لا ينقلها صفّاف في هذه النسخة؛ أضفها إلى ملف Word الناتج بنفسك.')
        if maths: out.append(f'في ملفك معادلات ({messages.ar(maths)}) لا ينقلها صفّاف في هذه النسخة.')
        if merged: out.append('في أحد جداولك خلايا مدموجة؛ تخرج في الملف الناتج غير مدموجة، فراجع ذلك الجدول.')
    return out

def analyze(job, draft_path):
    code, out, err = run(job, [os.path.join(SCRIPTS, 'analyze.py'), draft_path, '--json'], timeout=60)
    try: return json.loads(out)
    except Exception: return {}

THESIS_HINT = re.compile(r'المستخلص|الإهداء|الشكر والتقدير|رسالة (?:ماجستير|دكتوراه)|درجة (?:الماجستير|الدكتوراه)|قائمة المحتويات')

def prepare(job, src):
    """Convert, read the structure, suggest roles. Fills job.data and returns what the page shows."""
    job.data['src'] = src
    c = convert(job, src)
    if c['damaged'] is not None:
        raise Refused(messages.damaged(c['damaged']))
    items = structure.parse(c['draft'])
    n = structure.suggest(items, job.data['source'])
    notes_paired, notes_problem = (0, '')
    tables = 0
    if job.data['source'] == 'text':
        notes_paired, notes_problem = structure.pair_notes(items)
        tables = structure.tables(items)
    a = analyze(job, job.path('draft.md'))
    texts = [it for it in items if it['kind'] == 'text']
    needs_review = job.data['source'] == 'text' or n > 0 or not any(it['role'] in ('h1', 'h2') for it in texts)
    warnings = c['warnings'] + docx_checks(job)
    if notes_problem: warnings.append(notes_problem)
    if '{{مرجع' in c['draft']: warnings.append(messages.CITE_MARKS)
    if c['symbols']: warnings.append('في ملفك رموز مكتوبة بخطٍّ رمزي (مثل ﷺ مكتوبةً «e» بخط AGA Arabesque)؛ تجد في الإعدادات خيار تحويلها إلى محارفها.')
    body = c['draft']
    kind = 'thesis' if THESIS_HINT.search(body) and re.search(r'^#+ (?:الفصل|الباب)', body, re.M) else \
           'paper' if a.get('cover') else 'article'
    job.data.update(items=items, analysis=a, warnings=warnings, symbols_found=bool(c['symbols']),
                    notes_paired=notes_paired, tables_made=tables, needs_review=needs_review, kind_hint=kind)
    return view(job)

def view(job):
    d = job.data
    items = [dict(i=it['i'], kind=it['kind'], role=it.get('role'), text=(it.get('text') or it.get('note') or it['raw'])[:400],
                  suggested=it.get('suggested', False), why=it.get('why', ''), refs=len(it.get('refs', [])))
             for it in d['items'] if it['kind'] not in ('blank',)]
    a = d.get('analysis', {})
    return dict(id=job.id, name=d['name'], source=d['source'], items=items, needs_review=d['needs_review'],
                summary=structure.summary(d['items']), warnings=d['warnings'], kind_hint=d['kind_hint'],
                analysis=a, symbols=d['symbols_found'], trad=TRAD_ENABLED, panel=messages.PANEL)

# ---------------------------------------------------------------- in.md

def apply_roles(items, roles):
    for it in items:
        r = roles.get(str(it['i']))
        if it['kind'] == 'text' and r in structure.EDITABLE: it['role'] = r

BASMALA_TEXT = re.compile(r'^\s*(?:﷽|بسم)')

def build(job, opts):
    """The in.md for make.py, from the roles and the options. -> (path, make.py options, problems)."""
    import copy
    items = copy.deepcopy(job.data['items'])
    if opts.get('symbols') and job.data.get('symbols_found'):   # the draft again, with the known signs as their characters
        c = convert(job, job.data['src'], symbols=True)
        new = structure.parse(c['draft'])
        if len(new) != len(items): return None, [], ['تغيّر عدد الأسطر بعد تحويل الرموز'], []
        for a, b in zip(items, new):
            for k in ('raw', 'text', 'note', 'bold'):
                if k in b: a[k] = b[k]
            if a['kind'] == 'pnote' and 'note' in a:   # re-read the note text after the conversion
                m = structure.NOTE_LINE.match(a['raw']); a['note'] = m.group(3) if m else a['note']
    apply_roles(items, opts.get('roles') or {})
    kind = opts.get('kind') or 'article'
    if kind == 'article':   # no cover: lines marked for the cover stay in the text, the title as the article's title
        for it in items:
            if it['kind'] == 'text' and it['role'] in structure.COVER: it['role'] = 'h1' if it['role'] == 'c_title' else 'center'
    typed = {}; front = []; args = []; notes = []
    c = opts.get('cover') or {}
    if kind == 'paper' and not any(it['kind'] == 'text' and it['role'] == 'c_title' for it in items) and not (c.get('title') or '').strip():
        # no title chosen for the cover: the text's own first line, when it is its title, and the lines under it
        texts = [it for it in items if it['kind'] == 'text' and it['text'].strip()]
        if texts and texts[0]['role'] == 'h1':
            texts[0]['role'] = 'c_title'
            for it in texts[1:4]:
                if it['role'] != 'center': break
                it['role'] = 'c_line'
            notes.append('أخذتُ عنوان الغلاف من أول سطر في نصك، والأسطر التي تحته.')
    body, cover, moved = structure.render(items)
    if kind == 'paper':
        for key in ('title', 'author', 'affiliation', 'date'):
            v = (c.get(key) or '').strip().replace('\n', ' ')
            if v and key not in cover: cover[key] = [v]; typed[key] = v
        cover = {k: v for k, v in cover.items() if k in ('title', 'line', 'author', 'affiliation', 'date')}
        lines = [l.strip() for l in (c.get('lines') or []) if l.strip()]
        if lines: cover.setdefault('line', []).extend(lines); typed['line'] = lines
        if not cover.get('title'): return None, [], ['البحث ذو الغلاف يحتاج عنوانًا: اختره من نصك في «راجع البنية» أو اكتبه في الإعدادات.'], []
        front = ['---'] + [f'title: {cover["title"][0]}'] + [f'line: {v}' for v in cover.get('line', [])] \
                + [f'{k}: {cover[k][0]}' for k in ('author', 'affiliation', 'date') if cover.get(k)] + ['---']
        for k, w in (('author', 'اسم المؤلف'), ('date', 'التاريخ')):
            if not cover.get(k): notes.append(messages.missing_cover(w))
        if typed.get('author') and any(structure.BYLINE.match(l) for l in cover.get('line', [])):
            notes.append('في الغلاف سطرٌ من نصك فيه اسم الكاتب، ومعه اسم المؤلف الذي كتبتَه في الإعدادات؛ '
                         'فإن تكرّر الاسم فامسح حقل المؤلف، أو اجعل ذلك السطر «فقرة» في «راجع البنية».')
    elif kind == 'thesis':
        if not TRAD_ENABLED: return None, [], ['نمط الرسائل العلمية غير مفعّل في هذا الخادم.'], []
        t = dict(opts.get('thesis') or {})
        for key in ('title', 'college', 'department', 'degree', 'field', 'author', 'supervisor', 'date'):   # the document's own first
            if cover.get(key) and not (t.get(key) or '').strip(): t[key] = cover[key][0]
        if not t.get('members') and cover.get('member'):
            t['members'] = [dict(name=m.partition('|')[0].strip(), role=m.partition('|')[2].strip()) for m in cover['member']]
        front = ['---']
        for key in ('title', 'college', 'department', 'degree', 'field', 'author', 'supervisor', 'date'):
            v = (t.get(key) or '').strip().replace('\n', ' ')
            if v: front.append(f'{key}: {v}'); typed[key] = v
        if job.data.get('logo'): front.append(f'logo: {job.data["logo"]}')
        for m in t.get('members') or []:
            name = (m.get('name') or '').strip(); role = (m.get('role') or '').strip()
            if name: front.append(f'member: {name} | {role}')
        front.append('---')
        args.append('--profile=kku')
        aw = [x for x in (t.get('as_written') or []) if x in ('refs', 'symbols', 'toc-numbers')]
        if aw: args.append('--as-written=' + ','.join(aw))
    # the engine's own lines
    text_lines = [k for k, l in enumerate(body) if l.strip() and not l.startswith('[^')]
    lead = []
    if text_lines and BASMALA_TEXT.match(body[text_lines[0]]):   # the opening basmala stays the first line of the text
        b = text_lines[0]; lead = body[:b + 1]; body = body[b + 1:]
    have = {l.strip() for l in body}   # the engine's lines an .md source may already carry
    if opts.get('header') and '@header' not in have: lead.append('@header')
    if kind == 'thesis':
        if (opts.get('thesis') or {}).get('approval') and '@approval' not in have: lead.append('@approval')
        if (opts.get('thesis') or {}).get('basmala_page') and '@basmala' not in have: lead.append('@basmala')
    toc = opts.get('toc') or 'none'
    notes_defs = [l for l in body if structure.NOTE_DEF.match(l)]
    body = [l for l in body if not structure.NOTE_DEF.match(l)]
    if '@toc' in have:   # the source has its own contents line (a Word contents, or an .md @toc): kept where it is
        if toc == 'front' or kind == 'thesis' and toc != 'none': toc = 'source'
        else: body = [l for l in body if l.strip() != '@toc']
    if toc == 'front' or (kind == 'thesis' and toc != 'none'):
        if kind == 'article':   # after the article's title and the lines under it
            k = next((n for n, l in enumerate(body) if l.startswith('# ')), None)
            if k is not None and all(not l.strip() for l in body[:k]):
                k += 1
                while k < len(body) and (body[k].startswith('>>') or not body[k].strip()): k += 1
                body = body[:k] + ['@toc'] + body[k:]
            else: body = ['@toc'] + body
        else: body = ['@toc'] + body
    if opts.get('sort_sources'):
        body = sort_block(body)
    tail = []
    if opts.get('verse_index') and not any(indexes.directive(l) == 'آية' for l in body): tail.append('@index آية')
    if toc == 'end' and kind != 'thesis': tail.append('@toc')
    md = front + lead + body + [''] + tail + [''] + notes_defs
    path = job.path('in.md')
    with open(path, 'w', encoding='utf-8') as f: f.write('\n'.join(md).strip('\n') + '\n')
    # the author's text must come back unchanged from the in.md body
    problems = structure.verify(items, [l for l in lead + body + notes_defs if l not in ('@header', '@approval', '@basmala')], cover, typed)
    if opts.get('uthmani'): args.append('--uthmani')
    if opts.get('font') == 'traditional' and kind != 'thesis':
        if not TRAD_ENABLED: return None, [], ['خط Traditional Arabic غير مفعّل في هذا الخادم.'], []
        args.append('--font=traditional')
    if opts.get('basmala') and 1 <= int(opts['basmala']) <= 7: args.append(f'--basmala={int(opts["basmala"])}')
    job.data['in_items'] = items
    return path, args, problems, notes

SOURCES_H = re.compile(r'^# .*(?:المصادر|المراجع)')

def sort_block(body):
    """The author's own list of sources, between @sort and @end (the engine sorts it, each line kept whole)."""
    k = next((n for n, l in enumerate(body) if SOURCES_H.match(l)), None)
    if k is None: return body
    e = k + 1
    while e < len(body) and not body[e].startswith('#') and not body[e].startswith('@'): e += 1
    block = body[k + 1:e]
    if not any(l.strip() for l in block): return body
    return body[:k + 1] + ['@sort'] + block + ['@end'] + body[e:]

# ---------------------------------------------------------------- typeset and check

def typeset(job, opts):
    job.data['results'] = None
    path, args, problems, notes = build(job, opts)
    if path is None or problems:
        return dict(ok=False, error=(problems or ['تعذّر تجهيز النص'])[0])
    with open(path, encoding='utf-8') as f:
        if '{{مرجع' in f.read(): return dict(ok=False, error=messages.CITE_MARKS)
    name = job.data['name']
    out = job.path('out', name)
    for f in glob.glob(job.path('out', '*')): os.remove(f) if os.path.isfile(f) else None
    code, stdout, err = run(job, [os.path.join(SCRIPTS, 'make.py'), path, out] + args)
    if code is None: return dict(ok=False, error='توقّف الصفّ لأنه طال أكثر من المعتاد. جرّب مرة أخرى، أو أرسل جزءًا من النص.')
    if code != 0 or not os.path.exists(out + '.pdf'):
        last = (err or '').strip().splitlines()[-1:] or ['']
        return dict(ok=False, error='لم يكتمل الصفّ.', detail=last[0][:300])
    lines = stdout.splitlines()
    msgs = messages.translate([l for l in lines if not l.startswith('done:')], messages.MAKE)
    diff = check_output(job, out + '.docx', opts)
    if diff:
        for f in glob.glob(job.path('out', '*')): os.remove(f)
        return dict(ok=False, error='أوقفتُ التسليم: نصٌّ من نصك لم أجده في الملف الناتج كما كتبتَه. هذا خلل في صفّاف، لا في نصك.', detail=diff[0])
    pages = previews(job, out + '.pdf')
    files = [dict(kind='pdf', name=name + '.pdf'), dict(kind='docx', name=name + '.docx'), dict(kind='fonts', name='خطوط-لملف-Word.zip')]
    always = [messages.FONTS_ZIP]
    with open(path, encoding='utf-8') as f: md = f.read()
    if any(l.startswith('@toc') or l.startswith('@index') for l in md.split('\n')): always.append(messages.FIELDS)
    res = dict(ok=True, files=files, pages=pages, messages=[dict(text=m, level=level(m)) for m in notes + msgs], always=always, word_notes=[messages.NUMERAL, messages.MAC_PDF, messages.SPLIT_REF])
    job.data['results'] = res
    return res

INFO = re.compile(r'^(?:عدد الآيات المحوَّلة|أخذتُ عنوان الغلاف)')
def level(m): return 'info' if INFO.match(m) and not re.search(r'بقي كما كتبه الكاتب: [١-٩]', m) else 'warn'

INVISIBLE = dict.fromkeys(map(ord, '⁠‏‎‍‌‪‫‬‭‮⁦⁧⁨⁩﻿'))
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def docx_text(path):
    """The visible text of the Word file: every paragraph of the body and the notes, a footnote reference as one mark."""
    z = zipfile.ZipFile(path); paras = []
    for part in ('word/document.xml', 'word/footnotes.xml'):
        if part not in z.namelist(): continue
        root = ET.fromstring(z.read(part))
        for p in root.iter(W + 'p'):
            s = ''
            for el in p.iter():
                if el.tag == W + 't': s += el.text or ''
                elif el.tag == W + 'tab': s += ' '
                elif el.tag == W + 'footnoteReference': s += ''
            paras.append(s)
    return [norm(p) for p in paras]

def norm(s):
    s = s.translate(INVISIBLE).replace(' ', ' ')
    s = re.sub(r'\(?\)?', '', s)   # the Word file writes its own brackets around a note's number
    return re.sub(r'\s+', ' ', s).strip()

def check_output(job, docx, opts):
    """Every line of the author's (as the in.md has it) must stand in the Word file, letter for letter. Spaces are
    compared as single spaces; the engine's invisible aids are not text. Skipped: the verses the user asked to set in
    Uthmani script, the opening basmala set in calligraphy, and the engine's own lines."""
    got = '\n'.join(docx_text(docx))
    want = []
    with open(job.path('in.md'), encoding='utf-8') as f: md = f.read()
    for l in md.split('\n'):
        if not l.strip() or l.startswith('@') or l.strip() == '---' or structure.TABLE_SEP.match(l): continue
        m = structure.NOTE_DEF.match(l)
        if m: l = m.group(2)
        if re.match(r'^(title|line|author|affiliation|date|college|department|degree|field|supervisor|logo|member):', l): continue
        l = indexes.strip_marks(l)
        if structure.TABLE_ROW.match(l):
            want += [c.strip().replace('**', '') for c in l.strip()[1:-1].split('|') if c.strip()]; continue
        l = re.sub(r'^(?:#{1,3} |>> ?|\* |-- |- )', '', l).replace('**', '')
        l = re.sub(r'\[\^[^\]]+\]', '', l)
        if opts.get('uthmani') and re.search(r'﴿|تعالى|سبحانه|قال الله|قوله', l): continue
        if opts.get('basmala') and BASMALA_TEXT.match(l): continue
        want.append(l)
    missing = []
    for l in want:
        n = norm(l)
        if n and n not in got: missing.append(n[:80])
    return missing

def previews(job, pdf):
    d = job.path('out', 'pages'); os.makedirs(d, exist_ok=True)
    info = subprocess.run(['pdfinfo', pdf], capture_output=True, text=True).stdout
    m = re.search(r'Pages:\s+(\d+)', info); n = int(m.group(1)) if m else 0
    subprocess.run(['pdftoppm', '-r', '40', '-png', '-l', str(min(n, 80)), pdf, os.path.join(d, 'p')], capture_output=True, timeout=180)
    return n

def page_image(job, n, big=False):
    d = job.path('out', 'pages')
    files = sorted(glob.glob(os.path.join(d, 'p-*.png')))
    if not big: return files[n - 1] if 0 < n <= len(files) else None
    p = os.path.join(d, f'big-{n}.png')
    if not os.path.exists(p):
        pdf = job.path('out', job.data['name'] + '.pdf')
        subprocess.run(['pdftoppm', '-r', '110', '-png', '-f', str(n), '-l', str(n), '-singlefile', pdf, p[:-4]], capture_output=True, timeout=60)
    return p if os.path.exists(p) else None

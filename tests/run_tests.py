#!/usr/bin/env python3
"""Regression tests for صفّاف. Run from the project root:  python3 tests/run_tests.py
Needs: python3 (fonttools, pdfplumber), LibreOffice (soffice), poppler-utils."""
import os, re, subprocess, sys, tempfile, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, 'skill', 'saffaf', 'scripts')
T = os.path.join(ROOT, 'tests')
OUT = tempfile.mkdtemp(prefix='saffaf_tests_')
results = []

def ok(name, cond, detail=''):
    results.append((name, bool(cond), detail))
    print(('PASS ' if cond else 'FAIL ') + name + (f'  — {detail}' if detail else ''))

def run(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True)

# 1. typesetting + TOC page numbers match the PDF
for name in ['basic', 'long_toc', 'sample_page']:
    out = os.path.join(OUT, name)
    r = run(os.path.join(SK, 'make.py'), os.path.join(T, 'inputs', name + '.md'), out)
    built = r.returncode == 0 and os.path.exists(out + '.pdf') and os.path.exists(out + '.docx')
    ok(f'build {name}', built, r.stderr[-200:] if not built else '')
    if built and name != 'sample_page':
        c = run(os.path.join(T, 'toc_check.py'), out).stdout
        m = re.search(r'(\d+) TOC entries, (\d+) wrong', c)
        # long_toc has 4 known false alarms: «المطلب ١ من المبحث ٢» vs «المطلب ٢ من المبحث ١» share letters+digits
        allowed = 4 if name == 'long_toc' else 0
        ok(f'TOC numbers {name}', m and int(m.group(2)) <= allowed, c.strip().splitlines()[-1] if c.strip() else '')

# 1b. the contents: level-2 entries begin 1 cm in from the text edge, level-1 entries at the edge, numbers at the far edge
import zipfile, pdfplumber
tocx = zipfile.ZipFile(os.path.join(OUT, 'long_toc.docx')).read('word/document.xml').decode()
ent = [p for p in re.findall(r'<w:p>.*?</w:p>', tocx) if 'w:leader="dot"' in p]
ok('contents (Word file): only level-2 entries are indented, 1 cm on the start side', sum('<w:ind w:left="567"/>' in p for p in ent) == 36
   and all(('<w:ind w:left="567"/>' in p) != ('<w:b/>' in p) for p in ent) and 'w:right="567"' not in tocx, f'{len(ent)} entries')
lv = {1: [], 2: []}; far = []
with pdfplumber.open(os.path.join(OUT, 'long_toc.pdf')) as d:
    for p in d.pages:
        if '..........' not in (p.extract_text() or ''): continue
        rows = {}
        for c in p.chars: rows.setdefault(round(c['top']), []).append(c)
        for top, cs in rows.items():
            if sum(c['text'] == '.' for c in cs) < 10: continue
            lv[1 if any('Bold' in c['fontname'] for c in cs) else 2].append(p.width - 70.87 - max(c['x1'] for c in cs if c['text'] not in '. '))
            far.append(min(c['x0'] for c in cs) - 70.87)
ok('contents (PDF): level 2 begins 1 cm in, level 1 at the text edge, page numbers at the far edge', len(lv[1]) == 12 and len(lv[2]) == 36
   and all(abs(x) < 1 for x in lv[1] + far) and all(abs(x - 28.35) < 1 for x in lv[2]), f'level 1: {len(lv[1])}, level 2: {len(lv[2])}')
ok('the contents do not list themselves', len(ent) == 48 and not any('فهرس الموضوعات' in ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p)) for p in ent)
   and tocx.count('فهرس الموضوعات') == 1)

# 2. input conversion
def to_md(src):
    out = os.path.join(OUT, os.path.basename(src) + '.md')
    r = run(os.path.join(SK, 'to_md.py'), src, out)
    return r, (open(out, encoding='utf-8').read() if os.path.exists(out) else '')

r, md = to_md(os.path.join(T, 'formats', 'sample.docx'))
ok('docx: 2 footnotes', 'notes: 2' in r.stdout, r.stdout.strip())
ok('docx: bold kept', '**عريض هنا**' in md)
ok('docx: auto-numbering', re.search(r'^1\. ', md, re.M) is not None)
ok('docx: table', '| المصطلح | المعنى |' in md)
r, md = to_md(os.path.join(T, 'formats', 'sample.odt'))
ok('odt: converted with notes', 'notes: 2' in r.stdout, r.stdout.strip())
r, md = to_md(os.path.join(T, 'formats', 'sample.epub'))
ok('epub: chapters in order', md.find('الفصل الأول') < md.find('الفصل الثاني') and '**عريض**' in md)
r, md = to_md(os.path.join(T, 'formats', 'utf8_bom.txt'))
ok('txt: BOM/CRLF cleaned', md.startswith('الحمد') and '\r' not in md)
r, md = to_md(os.path.join(T, 'formats', 'cp1256.txt'))
ok('txt: Windows-1256 decoded', 'بترميز ويندوز' in md)
r, md = to_md(os.path.join(T, 'formats', 'copied_from_pdf.txt'))
ok('PDF-copied text flagged DAMAGED', 'DAMAGED' in r.stdout)
r, md = to_md(os.path.join(T, 'inputs', 'sample_page.md'))
ok('clean text not flagged', 'DAMAGED' not in r.stdout)
r, _ = to_md(os.path.join(T, 'formats', 'reject.pdf'))
ok('PDF input refused', r.returncode != 0 and 'not accepted' in (r.stderr + r.stdout))

# 3. iron rule: invisible aids only — visible text unchanged
sys.path.insert(0, SK); sys.argv = ['x']
import importlib.util
spec = importlib.util.spec_from_file_location('typeset', os.path.join(SK, 'typeset.py'))
ts = importlib.util.module_from_spec(spec); spec.loader.exec_module(ts)
for s in ['(ت:٤٦٨)', '(ت: ٧٥١هـ)', '(٢/ ٦٥٣)', '(١٢/٢٨٣)', '[البقرة: ١٤٣]', 'نص.. عادي', 'المصدر: https://example.org/2017/a/']:
    v = ts.inline(s, {})
    vis = re.sub('[\u2060\u200f\u200e\u202a\u202c⟦⟧⟬⟭`]', '', v).replace('\u00a0', ' ')   # invisible aids and run markers only
    ok(f'visible text unchanged: {s}', vis == s)
ok('death date set small', '⟦' in ts.inline('(ت:٤٦٨)', {}))
ok('a link ending in a slash keeps the slash at its end', ts.inline('المصدر: https://example.org/2017/a/', {}).endswith('/a/\u200e\u202c`'))

# 4. short references in the PDF: never split at their space; a split at the edge of the number is a known
#    LibreOffice limit (see FEEDBACK.md), reported not failed
for name in ['refs_death_space', 'refs_volume']:
    out = os.path.join(OUT, name)
    run(os.path.join(SK, 'make.py'), os.path.join(T, 'inputs', name + '.md'), out)
    c = run(os.path.join(T, 'split_check.py'), out + '.pdf').stdout.strip()
    if name == 'refs_death_space':
        ok('refs never split at their space (PDF)', c.endswith(', 0 split at its space'), c)
    print('INFO ' + c + '  (known LibreOffice limit)')

# 5. first-line indent, Word numbering, Uthmani script — on one document built with --uthmani
import zipfile
out = os.path.join(OUT, 'quran')
r = run(os.path.join(SK, 'make.py'), os.path.join(T, 'inputs', 'quran.md'), out, '--uthmani')
ok('build quran (--uthmani)', r.returncode == 0 and os.path.exists(out + '.pdf'), r.stderr[-200:])
z = zipfile.ZipFile(out + '.docx'); parts = {n: z.read(n).decode('utf-8', 'ignore') for n in z.namelist() if n.endswith(('.xml', '.rels'))}
paras = re.findall(r'<w:p>.*?</w:p>', parts['word/document.xml'])
ind = [p for p in paras if 'w:firstLine="567"' in p]
ok('ordinary paragraphs only: 1 cm first-line indent, no space after', len(ind) == 18 and all('<w:spacing w:after="0"/>' in p for p in ind)
   and not any(re.search(r'w:pStyle|w:numPr|w:hanging|w:jc w:val="center"', p) for p in ind)
   and 'w:firstLine' not in parts['word/footnotes.xml'] and parts['word/document.xml'].count('w:firstLine') == 18, f'{len(ind)} indented')
alone = [p for p in paras if 'ٱلۡعُسۡرِ' in p and '﴿' in p]
ok('stand-alone verse: centred, no indent', len(alone) == 1 and 'w:firstLine' not in alone[0] and '<w:jc w:val="center"/>' in alone[0])
ok('stand-alone verse: closing bracket followed by a right-to-left mark', len(alone) == 1 and re.search(r'٦\u2060?\]\u200f</w:t></w:r></w:p>$', alone[0]))
ftr = parts['word/footer1.xml']; choice = ftr[ftr.index('<mc:Choice'):ftr.index('</mc:Choice>')]; fallback = ftr[ftr.index('<mc:Fallback>'):ftr.index('</mc:Fallback>')]
ok('Word: PAGE field in the footer of every page', ' PAGE </w:instrText>' in ftr and ftr.count('fldCharType="begin"') == ftr.count('fldCharType="end"')
   and '<w:footerReference w:type="default" r:id="rIdF1"/>' in parts['word/document.xml'] and 'Id="rIdF1"' in parts['word/_rels/document.xml.rels'] and 'Target="footer1.xml"' in parts['word/_rels/document.xml.rels']
   and '<w:titlePg/>' not in parts['word/document.xml'])
ok('Word: page number spelled out in Arabic-Indic digits by fields', all(f'= {d} "{"٠١٢٣٤٥٦٧٨٩"[d]}"' in choice for d in range(9)) and '"٩"' not in choice and '٩' in choice
   and choice.count('MOD(INT(') == 27 and all(f'/{n}),10)' in choice for n in (1, 10, 100)) and '> 99' in choice and '> 9 ' in choice)
ok('Word: plain PAGE fallback for programs that cannot evaluate fields', fallback.count(' PAGE ') == 1 and 'IF' not in fallback)
ok('page number stands alone, no brackets', not re.search(r'<w:t[^>]*>[^<]*[()][^<]*</w:t>', ftr))
import pdfplumber
with pdfplumber.open(out + '.pdf') as d:
    feet = [re.sub('[^0-9٠-٩()]', '', (p.extract_text() or '').strip().splitlines()[-1]).translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')) for p in d.pages]
ok('PDF: every page ends with its bare number, no brackets', feet == [str(i + 1) for i in range(len(feet))] and len(feet) >= 3, ' '.join(feet))
lo = os.path.join(OUT, 'quran_lo.docx'); run(os.path.join(SK, 'typeset.py'), os.path.join(T, 'inputs', 'quran.md'), lo, 'lo')
ok('PDF route keeps a single PAGE field', zipfile.ZipFile(lo).read('word/footer1.xml').decode().count('fldCharType="begin"') == 1)
doc, fnx = parts['word/document.xml'], parts['word/footnotes.xml']
ok('Quran text is marked noProof, with the marks around it', doc.count('<w:noProof/>') == 33 and fnx.count('<w:noProof/>') == 3
   and len(re.findall(r'<w:noProof/>(?:<w:sz[^>]*/><w:szCs[^>]*/>)?<w:rtl/></w:rPr><w:t xml:space="preserve">[﴿«]</w:t></w:r><w:r><w:rPr><w:rFonts w:ascii="KFGQPC', doc + fnx)) == 12
   and len(re.findall(r'</w:t></w:r><w:r><w:rPr><w:noProof/>(?:<w:sz[^>]*/><w:szCs[^>]*/>)?<w:rtl/></w:rPr><w:t xml:space="preserve">[﴾»]</w:t>', doc + fnx)) == 12)
ok('Word numbering: no hindiNumbers anywhere', not any('hindiNumbers' in x for x in parts.values())
   and 'hindiNumbers' not in open(os.path.join(SK, 'typeset.py'), encoding='utf-8').read()
   and '<w:pgNumType w:fmt="decimal"/>' in parts['word/document.xml'] and '<w:numFmt w:val="decimal"/>' in parts['word/settings.xml'])

import quran as q
src = q.source()
# the skill's compact Quran file against the two source files: every ayah, both texts, letter for letter
import hashlib; sys.path.insert(0, T); import build_quran_data as bq
orig = bq.load()
def differing(data):
    return [f'{s_}:{a_}' for s_, a_, imlaei, uthmani in orig
            if data.get(f'{s_}:{a_}') is None or data[f'{s_}:{a_}'][0] != imlaei or data[f'{s_}:{a_}'][1] + [str(a_).translate(bq.HINDI)] != uthmani]
bad = differing(src)
ok('Quran data: every ayah identical to the source files', not bad and len(orig) == len(src) == 6236 and [f'{s_}:{a_}' for s_, a_, _, _ in orig] == list(src), ' '.join(bad[:5]))
dropped = dict(src); dropped['2:255'] = (src['2:255'][0], src['2:255'][1][:-1] + [src['2:255'][1][-1][:-1]])   # one mark removed
ok('Quran data: the comparison catches a single changed mark', differing(dropped) == ['2:255'])
note = open(os.path.join(T, 'quran-source', 'SOURCE.md'), encoding='utf-8').read()
ok('Quran sources and font are the files recorded in SOURCE.md', all(hashlib.sha256(bq.raw(f)).hexdigest() in note for f in ('qpc-hafs-word-by-word.json', 'imlaei-script-ayah-by-ayah.json'))
   and hashlib.sha256(open(q.FONT_FILE, 'rb').read()).hexdigest() in open(os.path.join(q.QDIR, 'SOURCE.md'), encoding='utf-8').read())
ok('the skill ships only the compact Quran file and the font', sorted(os.listdir(q.QDIR)) == ['SOURCE.md', 'UthmanicHafs_V22.ttf', 'quran.txt.xz'])
ok('Quran: all 6236 ayahs line up word for word', len(src) == 6236 and all(q.align(k, i, u) for k, (i, u) in src.items()))
saved = dict(q.SPLITS); q.SPLITS.clear(); need = {k for k, (i, u) in src.items() if not q.align(k, i, u)}; q.SPLITS.update(saved)
ok('Quran: the exception table is exactly the ayahs that need it', need == set(saved), f'{len(need)} ayahs')
def uth(k, a=None, b=None): return ' '.join(w[2:] if w.startswith('۞ ') else w for w in src[k][1][a:b])
bare = lambda s: ''.join(c for c in s if not unicodedata.combining(c))
im = lambda k: src[k][0]
# The author's marks are ignored altogether: the letters alone recognise the verse, and the Mushaf's own marks are written.
sukun = im('2:151').replace('وَيُعَلِّمُكُم مَّا', 'وَيُعَلِّمُكُمْ مَا').replace('تَكُونُوا', 'تَكُونُواْ')   # sukun added, the shadda of assimilation dropped
vowels = im('1:2').replace('الْحَمْدُ', 'الْحَمْدَ').replace('رَبِّ', 'رَبُّ')
assert sukun != im('2:151') and bare(sukun) == bare(im('2:151')) and vowels != im('1:2') and bare(vowels) == bare(im('1:2'))
cases = [  # (name, verse, reference as (surah name, ayah numbers or None), expected Uthmani text or None)
    ('whole ayah with its reference', im('51:56'), ('الذاريات', '٥٦'), uth('51:56')),
    ('whole ayah with no vowel marks', bare(im('51:56')), ('الذاريات', '٥٦'), uth('51:56')),
    ('vowel marks that differ in sukun and shadda', sukun, ('البقرة', '١٥١'), uth('2:151')),
    ('vowel marks that differ in the vowels', vowels, ('الفاتحة', '٢'), uth('1:2')),
    ('part of an ayah: that part only', bare('شَهْرُ رَمَضَانَ الَّذِي أُنزِلَ فِيهِ الْقُرْآنُ'), ('البقرة', '١٨٥'), uth('2:185', 0, 6)),
    ('exception ayah 20:94', 'يَا ابْنَ أُمَّ لَا تَأْخُذْ بِلِحْيَتِي', ('طه', '٩٤'), uth('20:94', 1, 5)),
    ('exception ayah 2:181', im('2:181'), ('البقرة', '١٨١'), uth('2:181')),
    ('two ayahs with their numbers', im('112:1') + ' (١) ' + im('112:2') + ' (٢)', ('الإخلاص', '١-٢'), uth('112:1') + ' ١ ' + uth('112:2') + ' ٢'),
    ('hizb sign left out', im('2:26'), ('البقرة', '٢٦'), uth('2:26')),
    ('no reference, one place only', im('112:1'), None, uth('112:1')),
    ('no reference, many places, one Uthmani text: converted', bare(im('55:13')), None, uth('55:13')),
    ('no reference, several places whose Uthmani text differs: kept', 'ملة إبراهيم حنيفا', None, None),
    ('the same verse with its surah named: converted', 'ملة إبراهيم حنيفا', ('البقرة', None), uth('2:135', -7, -4)),
    ('the same verse with another reference: that place', 'ملة إبراهيم حنيفا', ('آل عمران', '٩٥'), uth('3:95', -7, -4)),
    ('near-alike verse whose reference disagrees with its letters: kept', 'لَا نُكَلِّفُ نَفْسًا إِلَّا وُسْعَهَا', ('البقرة', '٢٨٦'), None),
    ('a letter that differs: kept', im('1:2').replace('الْعَالَمِينَ', 'الْعَلَمِينَ'), ('الفاتحة', '٢'), None),
    ('half of a joined word: kept', 'أَيُّهَا النَّاسُ اعْبُدُوا رَبَّكُمُ', ('البقرة', '٢١'), None),
    ('unknown surah name: kept', im('51:56'), ('الذاريه', '٥٦'), None),
]
many = sum(bare(i).count(bare(im('55:13'))) for i, u in src.values())
assert '۞' in ' '.join(src['2:26'][1]) and many > 20 and uth('2:135', -7, -4) != uth('3:95', -7, -4) and 'إِبۡرَٰهِـۧمَ' in uth('2:135', -7, -4)
for name, verse, ref, want in cases:
    got = q.convert(verse, ref)
    ok('Quran: ' + name, got == want and (want is None or '۞' not in got), '' if got == want else f'got {got!r}')
why = {v: note for done, v, note in q.REPORT if not done}
ok('Quran: a disagreeing reference names both places for the reply', all(x in why['لَا نُكَلِّفُ نَفْسًا إِلَّا وُسْعَهَا'] for x in ('الأنعام: ١٥٢', 'الأعراف: ٤٢', 'البقرة: ٢٨٦')), why['لَا نُكَلِّفُ نَفْسًا إِلَّا وُسْعَهَا'])
ok('Quran: a verse whose places differ asks for its reference or surah', 'البقرة: ١٣٥' in why['ملة إبراهيم حنيفا'] and 'اسم سورتها' in why['ملة إبراهيم حنيفا'])
ok('Quran: every reason given for the reply is in Arabic', why and not re.search('[A-Za-z]', ''.join(why.values())))
ts.UTHMANI = True
clean = lambda x: re.sub('[\u2060\u200f⟦⟧⟬⟭]', '', x).replace('\u00a0', ' ')
def shown(t):   # what inline() makes of a line: the visible text with each converted verse replaced by ⟪⟫, and the verses
    v = ts.inline(t, {}); return re.sub('⟪[^⟫]*⟫', '⟪⟫', clean(v)), re.findall('⟪([^⟫]*)⟫', v)
line = 'قال تعالى: ﴿' + im('51:56') + '﴾ [الذاريات: ٥٦] ثم ﴿ملة إبراهيم حنيفا﴾ والحمد لله رب العالمين (٢/ ٦٥٣)'
ok('Uthmani on: only the matched verse changes', shown(line) == (line.replace(im('51:56'), '⟪⟫'), [uth('51:56')]))
usr = 'إن مع العسر يسرا'; yusr = uth('94:6')
ok('a verse between «» after «قال تعالى» is converted', shown(f'قال تعالى: «{usr}» ثم') == ('قال تعالى: «⟪⟫» ثم', [yusr]))
ok('the same after other explicit phrases and between "" or ()', all(shown(a + o + usr + c) == (a + o + '⟪⟫' + c, [yusr])
   for a in ('وَقَالَ سُبْحَانَهُ: ', 'كقوله تعالى ', 'قال الله عز وجل في كتابه: ', 'يقول الله: ') for o, c in ('«»', '""', '“”', '()')))
n = len(q.REPORT)
plain = ['وقد ورد «' + usr + '» في كلامه', 'ومن ذلك (' + usr + ') عنده', 'قال الشاعر: «' + usr + '»', usr + '، كما يقال', 'كما في [البقرة: ١٤٣] وفي سورة الشرح']
ok('a Quranic phrase the author did not mark as a verse is never looked at', all(shown(t) == (t, []) for t in plain) and len(q.REPORT) == n)
ok('a reference with no verse text adds nothing', shown('كما في [البقرة: ١٤٣].') == ('كما في [البقرة: ١٤٣].', []))
ok('the surah named before the verse, or alone after it, settles its place', shown('قال تعالى في سورة البقرة: ﴿ملة إبراهيم حنيفا﴾')[1] == [uth('2:135', -7, -4)]
   and shown('﴿ملة إبراهيم حنيفا﴾ (آل عمران)')[1] == [uth('3:95', -7, -4)] and shown('وفي سورة البقرة آيات كثيرة، وقال تعالى: ﴿ملة إبراهيم حنيفا﴾')[1] == [])
ts.UTHMANI = False
ok('Uthmani off by default: verses untouched', clean(ts.inline(line, {})) == line and clean(ts.inline(f'قال تعالى: «{usr}»', {})) == f'قال تعالى: «{usr}»')
ok('docx: verses set in the Quran font', parts['word/document.xml'].count(f'w:cs="{q.FONT}"') == 11 and parts['word/footnotes.xml'].count(f'w:cs="{q.FONT}"') == 1)
key = re.search(r'rIdFont1" w:fontKey="\{([^}]+)\}', parts['word/fontTable.xml'])
data = bytearray(z.read('word/fonts/font1.odttf')) if key else b''
if key:
    k = [int(key.group(1).replace('-', '')[i:i + 2], 16) for i in range(0, 32, 2)][::-1]
    for i in range(32): data[i] ^= k[i % 16]
ok('docx: Quran font embedded unmodified', bytes(data) == open(q.FONT_FILE, 'rb').read())
plain = zipfile.ZipFile(os.path.join(OUT, 'basic.docx'))
same = lambda a, b: os.path.exists(a) and open(a, 'rb').read() == open(b, 'rb').read()
AF = os.path.join(SK, '..', 'assets', 'fonts'); lotus = sorted(os.listdir(AF))
ok('docx: Lotus Lotfi is not embedded', [n for n in z.namelist() if n.endswith('.odttf')] == ['word/fonts/font1.odttf'] and parts['word/fontTable.xml'].count('w:embed') == 1
   and not any(n.endswith('.odttf') for n in plain.namelist()) and 'w:embed' not in plain.read('word/fontTable.xml').decode() and 'embedTrueTypeFonts' not in plain.read('word/settings.xml').decode())
ZIP = 'خطوط-لملف-Word.zip'
ok('the fonts are delivered as one zip beside the output, not as loose files', r.stdout.strip().endswith('| fonts: ' + os.path.join(OUT, ZIP))
   and os.path.exists(os.path.join(OUT, ZIP)) and not os.path.exists(os.path.join(OUT, 'fonts')) and not [f for f in os.listdir(OUT) if f.endswith('.ttf')])
ok('without --uthmani: no Quran font, verses as written', 'font1.odttf' not in plain.namelist() and 'KFGQPC' not in plain.read('word/document.xml').decode() and 'وَكَذَلِكَ جَعَلْنَاكُمْ' in plain.read('word/document.xml').decode())
rep = [l for l in r.stdout.splitlines() if l.startswith('QURAN')]
ok('the report for the reply: the count, then each verse left as written and why — in Arabic', len(rep) == 4 and rep[0] == 'QURAN: عدد الآيات المحوَّلة إلى الرسم العثماني: ١٢، وعدد ما بقي كما كتبه الكاتب: ٣'
   and all(l.startswith('QURAN بقيت كما كُتبت: ﴿') for l in rep[1:]) and not re.search('[A-Za-z]', ''.join(rep).replace('QURAN', '')), rep[0] if rep else '')

# 6. page set to the measures of a printed book — on an article with a title, a writer line and a Latin footnote
art = os.path.join(OUT, 'article')
ra = run(os.path.join(SK, 'make.py'), os.path.join(T, 'inputs', 'article.md'), art)
ok('build article', ra.returncode == 0 and os.path.exists(art + '.pdf'), ra.stderr[-200:])
za = zipfile.ZipFile(art + '.docx'); A = {n: za.read(n).decode('utf-8', 'ignore') for n in za.namelist() if n.endswith('.xml')}
ap = re.findall(r'<w:p>.*?</w:p>', A['word/document.xml']); st = A['word/styles.xml']; notes = re.findall(r'<w:footnote w:id="[1-9]\d*">.*?</w:footnote>', A['word/footnotes.xml'])
ok('article title: about 4 lines above, the writer line shares the 3 lines below', '<w:pStyle w:val="Heading1"/>' in ap[0] and '<w:spacing w:before="1920" w:after="480"/>' in ap[0]
   and '<w:jc w:val="center"/>' in ap[1] and '<w:b/><w:bCs/>' in ap[1] and '<w:spacing w:after="480"/>' in ap[1] and 'w:sz ' not in ap[1])
ok('article title with no writer line: 3 lines below', '<w:pStyle w:val="Heading1"/><w:bidi/><w:spacing w:before="1920" w:after="1440"/>' in paras[0])
ok('a cover keeps the first heading as an ordinary one', '<w:spacing w:before="1920"' not in zipfile.ZipFile(os.path.join(OUT, 'basic.docx')).read('word/document.xml').decode())
ok('heading 2: half a line above, nothing below', 'w:styleId="Heading2"' in st and re.search(r'w:styleId="Heading2".*?<w:spacing w:before="240" w:after="0"/>', st))
ok('footnotes: 13 pt, single spacing, text hangs clear of the number', re.search(r'w:styleId="FootnoteText".*?<w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="340" w:hanging="340"/>.*?<w:sz w:val="26"/><w:szCs w:val="26"/>', st)
   and all(re.search(r'<w:footnoteRef/></w:r>.*?<w:tab/></w:r>', n) for n in notes) and len(notes) == 4)
ok('footnote number on the line in the note, raised in the text', 'FootnoteReference' not in A['word/footnotes.xml'] and 'vertAlign' not in A['word/footnotes.xml']
   and A['word/document.xml'].count('<w:rStyle w:val="FootnoteReference"/><w:rtl/></w:rPr><w:footnoteReference') == 4 and 'w:val="superscript"' in st)
ltr = [n for n in notes if '<w:bidi w:val="0"/>' in n]
ok('Latin footnote: left to right, left aligned, Times, same hanging; Arabic ones unchanged', len(ltr) == 1 and 'Aune, Kristin' in ltr[0]
   and '<w:bidi w:val="0"/><w:jc w:val="left"/></w:pPr>' in ltr[0] and 'w:ascii="Times New Roman"' in ltr[0] and '<w:rtl/>' not in ltr[0]
   and ltr[0].count('<w:footnoteRef/>') == 1 and sum('<w:pStyle w:val="FootnoteText"/><w:bidi/></w:pPr>' in n for n in notes) == 2)
TNR = '<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:rtl w:val="0"/><w:lang w:val="en-US"/></w:rPr>'
ok('Word file: the number of a Latin footnote is set as its Latin text (Times, English), brackets included; Arabic notes keep theirs',
   f'<w:r>{TNR}<w:t>(</w:t></w:r><w:r>{TNR}<w:footnoteRef/></w:r><w:r>{TNR}<w:t>)</w:t></w:r>' in ltr[0]
   and sum('<w:r><w:rPr><w:sz w:val="26"/><w:szCs w:val="26"/><w:rtl/></w:rPr><w:footnoteRef/></w:r>' in n for n in notes) == 3)
ok('a footnote with a word that cannot break (a link) is not justified; the link is untouched', '<w:pStyle w:val="FootnoteText"/><w:bidi/><w:jc w:val="left"/></w:pPr>' in notes[0]
   and '>\u202ahttps://example.org/article/2017\u202c</w:t>' in notes[0] and sum('<w:jc' in n for n in notes) == 2 and not re.search('[\u200b\u00ad]', A['word/footnotes.xml']))
ok('Latin text keeps its own digits (not Arabic text)', A['word/footnotes.xml'].count('<w:lang w:val="en-US"/>') >= 2 and 'https://example.org/article/2017' in A['word/footnotes.xml'])
with pdfplumber.open(art + '.pdf') as d:
    chars = [c['text'] for p in d.pages for c in p.chars]; text = '\n'.join(p.extract_text() or '' for p in d.pages)
ok('justified without kashida (Word setting and LibreOffice PDF)', not re.search(r'w:val="(low|medium|high)Kashida"', ''.join(A.values()) + ''.join(parts.values()))
   and '<w:jc w:val="both"/>' in st and chars.count('\u0640') == 0, f'{chars.count(chr(0x640))} kashida glyphs in the PDF')
flat = ' '.join(text.split())   # where the note's line breaks falls differs from one LibreOffice version to another
ok('PDF: Latin footnote reads left to right', 'Aune, Kristin "Much Less Religious, A Little More Spiritual." Feminist Review, vol. 97, no. 1, Mar. 2011, pp. 32-55.' in flat)

# 7. the PDF engine really used the right fonts (a silent fallback font changes every line break)
pdfs = [os.path.join(OUT, n + '.pdf') for n in ['basic', 'long_toc', 'sample_page', 'refs_death_space', 'refs_volume']]
c = run(os.path.join(T, 'font_check.py'), *pdfs).stdout.strip().splitlines()
good = [l for l in c if re.search(r': [1-9]\d* Arabic letters, 0 not in Lotus Lotfi, 0 in the Quran font$', l)]
ok('PDF font is Lotus Lotfi', len(good) == len(pdfs), '; '.join(l.split('/')[-1] for l in c if l not in good) or f'{len(pdfs)} PDFs')
c = run(os.path.join(T, 'font_check.py'), out + '.pdf').stdout.strip()
ok('PDF: verses in the Quran font, the rest in Lotus Lotfi', re.search(r', 0 not in Lotus Lotfi, [1-9]\d* in the Quran font$', c), c.split('/')[-1])

# 8. a heading must not be left alone at the foot of a page (LibreOffice does that when the paragraph after it carries
#    a footnote that no longer fits). sample_page.md reproduces it with no manual page break.
spec = importlib.util.spec_from_file_location('make', os.path.join(SK, 'make.py')); mk = importlib.util.module_from_spec(spec); spec.loader.exec_module(mk)
mk.UTHMANI = []; mk.setup()
sp = os.path.join(T, 'inputs', 'sample_page.md'); hs = mk.keep_heads(sp); lone = os.path.join(OUT, 'lone')
run(os.path.join(SK, 'typeset.py'), sp, lone + '.docx', 'lo'); mk.to_pdf(lone + '.docx', lone + '.pdf')
left = [hs[n] for n in mk.lone_heads(lone + '.pdf', hs)]
if left:   # where a page ends depends on the LibreOffice version; the versions that lay this page out the same way reproduce it
    ok('the case reproduces a heading left alone at the foot of a page', '@pagebreak' not in open(sp, encoding='utf-8').read()
       and left == ['المطلب الأول: المعنى في اللغة والاصطلاح'])
    ok('make.py moves such a heading to the next page with its paragraph', mk.find_pages(os.path.join(OUT, 'sample_page.pdf'), [('المطلب الأول: المعنى في اللغة والاصطلاح', 2)]) == [2])
else: print('INFO this LibreOffice version lays the page out differently: no heading is left alone to begin with')
ok('no heading is left alone at the foot of a page', mk.lone_heads(os.path.join(OUT, 'sample_page.pdf'), hs) == [])
ok('a page break the PDF needs goes into the Word file too: it is the same file', "md, docx, 'word'] + args + ([f'--break-before=" in open(os.path.join(SK, 'make.py'), encoding='utf-8').read())

# 8b. the fonts zip: the two Lotus Lotfi files always; the Quran font whenever at least one verse was converted, and only then
def zipped(docx):
    zf = zipfile.ZipFile(mk.fonts_zip(docx)); return {n: zf.read(n) for n in zf.namelist()}
lot = {f: open(os.path.join(AF, f), 'rb').read() for f in lotus}; qf = {os.path.basename(q.FONT_FILE): open(q.FONT_FILE, 'rb').read()}
ok('fonts zip without verses: the two Lotus Lotfi files, unmodified', len(lot) == 2 and zipped(os.path.join(OUT, 'basic.docx')) == lot)
ok('fonts zip when a verse was converted: the Quran font too, unmodified', zipped(os.path.join(OUT, 'quran.docx')) == {**lot, **qf})
none = os.path.join(OUT, 'no_verse.docx'); rn = run(os.path.join(SK, 'typeset.py'), os.path.join(T, 'inputs', 'article.md'), none, 'word', '--uthmani')
ok('fonts zip when Uthmani script was asked for but no verse was converted: no Quran font', 'QURAN: عدد الآيات المحوَّلة إلى الرسم العثماني: ٠،' in rn.stdout and zipped(none) == lot, rn.stdout.strip()[:80])

# 9. hanging numbers begin exactly at the text edge — list items, bullets, footnotes — and the text hangs inward
bz = zipfile.ZipFile(os.path.join(OUT, 'basic.docx')); bx = {n: bz.read(n).decode('utf-8', 'ignore') for n in bz.namelist() if n.endswith('.xml')}
ok('hanging indents are on the start side (Word file)', '<w:ind w:left="425" w:hanging="425"/>' in bx['word/document.xml'] and '<w:ind w:left="397" w:hanging="397"/>' in bx['word/numbering.xml']
   and '<w:ind w:left="340" w:hanging="340"/>' in bx['word/styles.xml'] and not re.search(r'w:right="\d+" w:hanging', ''.join(bx.values()) + ''.join(A.values())))
def edges(pdf):
    """-> (how far any line runs past the right text edge, right ends of the lines that open with a hanging number, of the note lines after the first)"""
    past = 0; opens = []; follow = []
    with pdfplumber.open(pdf) as d:
        for p in d.pages:
            edge = p.width - 70.85; rows = {}
            for c in p.chars: rows.setdefault(round(c['top']), []).append(c)
            rows = sorted(rows.items())[:-1]
            for i, (top, cs) in enumerate(rows):
                x1 = max(c['x1'] for c in cs) - edge; past = max(past, x1)
                first = ''.join(c['text'] for c in sorted(cs, key=lambda c: -c['x0']))[:4]
                if len(cs) > 8 and re.match(r'[(][٠-٩0-9]+[)]|[٠-٩]+-', first): opens.append(x1)
                elif cs[0]['size'] < 13.5 and top > p.height / 2 and i and rows[i - 1][1][0]['size'] < 13.5 and min(c['x0'] for c in cs) > 200: follow.append(x1)
    return past, opens, follow
past, opens, _ = edges(os.path.join(OUT, 'sample_page.pdf'))
ok('PDF: list numbers and note numbers begin at the text edge, not in the margin', past < 1 and len(opens) == 6 and all(abs(x) < 1 for x in opens), f'{len(opens)} numbered lines, furthest {past:.1f} pt')
past, opens, follow = edges(art + '.pdf')
ok('PDF: the text of a note hangs inward from its number', past < 1 and any(abs(x + 17) < 1 for x in follow) and not any(x > -1 for x in follow), f'second lines end {sorted(set(round(x) for x in follow))} pt from the edge')
def note_starts(pdf):
    """-> where the text of each Arabic note's first line begins, in pt in from the text edge (the number «(n)» sits at the edge)"""
    out = []
    with pdfplumber.open(pdf) as d:
        for p in d.pages:
            edge = p.width - 70.85; rows = {}
            for c in p.chars: rows.setdefault(round(c['top']), []).append(c)
            for top, cs in rows.items():
                cs = sorted(cs, key=lambda c: -c['x0'])
                if len(cs) > 4 and cs[0]['size'] < 13.5 and cs[0]['text'] == '(' and edge - cs[0]['x1'] < 1 and cs[2]['text'] == ')':
                    out.append(edge - cs[3]['x1'])
    return out
starts = note_starts(art + '.pdf')
ok('PDF: the first line of a note starts where its other lines hang, clear of the number', len(starts) == 3 and all(abs(x - 17) < 1 for x in starts),
   f'first lines start {[round(x, 1) for x in starts]} pt in')

# 10. the reply: always in the user's language, and every ready-made line the skill hands to the user is Arabic
skill_md = open(os.path.join(SK, '..', 'SKILL.md'), encoding='utf-8').read()
reply = skill_md.split('## The reply')[1].split('\n## ')[0] if '## The reply' in skill_md else ''
ready = re.findall(r'^  - [^«\n]*: («.*»)$', reply, re.M)
ALLOWED = {'Word', 'PDF', 'Numeral', 'Context', 'Hindi', 'Print', 'Save', 'as', 'As', 'zip'}   # names of things on the user's screen
ok('SKILL.md: the reply is always in the user\'s language', "always the user's" in reply and 'Arabic' in reply and 'never paste them' in reply)
rules = open(os.path.join(ROOT, 'CLAUDE.md'), encoding='utf-8').read()
ok('the Uthmani exception is stated the same way in CLAUDE.md and SKILL.md', all(all(x in d for x in ("letters alone", "vowel marks are ignored", 'قال تعالى', "never searched", "Hafs")) for d in (rules, skill_md))
   and not any("any vowel mark the author wrote must be" in d or "exactly one place" in d for d in (rules, skill_md)))
ok('SKILL.md: every ready-made line for the reply is in Arabic', len(ready) >= 6 and all(len(re.findall('[ء-ي]', r)) > 20 and set(re.findall('[A-Za-z]+', r)) <= ALLOWED for r in ready),
   f'{len(ready)} lines; ' + ' '.join(sorted({w for r in ready for w in re.findall('[A-Za-z]+', r)} - ALLOWED)))
outside = [q for q in re.findall('«[^«»]*»', skill_md.replace(reply, '')) if len(re.findall('[ء-ي]', q)) > 30]
ok('SKILL.md: no ready-made line for the user is left outside the reply section', outside == [], ' | '.join(q[:40] for q in outside))

# 11. justified lines are filled by the spaces between the words only: no letter is stretched anywhere. The stretching
#     is drawn with glyphs that carry no character, so the words are measured (stretch_check.py): the same Word file is
#     set twice by the same engine, justified and unjustified, and no word may be wider in the first than in the second.
def unjustified(docx):
    out = docx[:-5] + '_ragged.docx'; zi = zipfile.ZipFile(docx); zo = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)
    for it in zi.infolist(): zo.writestr(it, zi.read(it.filename).replace(b'<w:jc w:val="both"/>', b'<w:jc w:val="left"/>'))
    zo.close(); return out
def stretch(md, name, *args, against=None):
    d = os.path.join(OUT, name + '_lo.docx'); run(os.path.join(SK, 'typeset.py'), md, d, 'lo', *args); mk.to_pdf(d, d[:-5] + '.pdf')
    rg = against or unjustified(d)
    if not against: mk.to_pdf(rg, rg[:-5] + '.pdf')
    c = run(os.path.join(T, 'stretch_check.py'), d[:-5] + '.pdf', rg[:-5] + '.pdf').stdout.strip()
    m = re.search(r'(\d+) justified lines, (\d+) words \((\d+) unjustified\), (\d+) stretched', c)
    n = [int(x) for x in m.groups()] if m else [0, 0, -1, -1]
    return [n[0], n[1], n[3] if n[1] == n[2] else -1], c, rg   # the two PDFs must hold the same number of words
mk.UTHMANI = ['--uthmani']; mk.setup()
# LibreOffice before 25 stretches letters to fill a line, and nothing short of altering the font stops it (CLAUDE.md,
# Known limits): there the count is shown, not failed. From 25 on, the line must be filled by spaces alone.
ver = re.search(r'(\d+)\.\d+', subprocess.run(mk.SOFFICE_CMD + ['--version'], capture_output=True, text=True).stdout); modern = bool(ver) and int(ver.group(1)) >= 25
lt = os.path.join(T, 'inputs', 'long_text.md'); long_src = open(lt, encoding='utf-8').read()
(lines, nwords, wide), c, rag = stretch(lt, 'long_text')
ok('long text: many justified lines to measure', lines >= 45 and nwords > 900, c)
if modern: ok('long text: not one word stretched', wide == 0, c)
else: print(f'INFO long text on LibreOffice {ver.group(0) if ver else "?"}: {c}  (known limit before version 25)')
with pdfplumber.open(os.path.join(OUT, 'long_text_lo.pdf')) as d: typed = [c_ for p in d.pages for c_ in p.chars if c_['text'] == '\u0640']
# (the older versions draw it too, but their PDF no longer says which glyph it is once they have inserted the same glyph themselves)
if modern: ok('a kashida the author typed is still there, as wide as the font draws it', len(typed) == long_src.count('\u0640') == 5 and all(3 < c_['width'] < 6 and 'LotusLotfi' in c_['fontname'] for c_ in typed), f'{len(typed)} in the PDF')
# the measuring itself: five words given a kashida must be reported, though the words are named without it
marked = os.path.join(OUT, 'marked.md'); grown = long_src
for a, b in [('الرصاص', 'الرصـاص'), ('القارئ العربي', 'القـارئ العربي'), ('الحاسوب', 'الحاسـوب'), ('أنهار', 'أنهـار'), ('الميزان', 'الميـزان'), ('ميزان صحيح', 'ميـزان صحيح')]: grown = grown.replace(a, b, 1)
open(marked, 'w', encoding='utf-8').write(grown)
(_, _, wide), c, _ = stretch(marked, 'marked', against=rag)
if modern: ok('the measuring catches a widened word', grown.count('\u0640') == 10 and wide == 5, c)
(lines, nwords, wide), c, _ = stretch(os.path.join(T, 'inputs', 'long_verses.md'), 'long_verses', '--uthmani')
with pdfplumber.open(os.path.join(OUT, 'long_verses_lo.pdf')) as d:
    rows = {}
    for c_ in d.pages[0].chars: rows.setdefault(round(c_['bottom'] / 4), []).append(c_)
    only = sum(len(r) > 40 and all('KFGQPC' in c_['fontname'] for c_ in r if c_['text'].strip()) for r in rows.values())
ok('verses in Uthmani script: the case has full lines of Quran text only', lines >= 6 and only >= 4, f'{only} lines of Quran text only')
# Verses in Uthmani script are left to the engine: the Mushaf itself is justified with kashida. Shown for information.
print(f'INFO lines of Quran text only: {c}')

# 12. an article with no title: every ordinary paragraph opens with the 1 cm indent — the first one too
nt = os.path.join(OUT, 'no_title.md'); body = [l for l in long_src.split('\n') if l and not l.startswith(('# ', '>> '))]
open(nt, 'w', encoding='utf-8').write('\n'.join(body) + '\n'); nbody = sum(not l.startswith('[^') for l in body)
run(os.path.join(SK, 'typeset.py'), nt, nt[:-3] + '.docx', 'word'); run(os.path.join(SK, 'typeset.py'), nt, nt[:-3] + '_lo.docx', 'lo'); mk.to_pdf(nt[:-3] + '_lo.docx', nt[:-3] + '.pdf')
np_ = re.findall(r'<w:p>.*?</w:p>', zipfile.ZipFile(nt[:-3] + '.docx').read('word/document.xml').decode())
ok('no title (Word file): the first paragraph is indented like every other', nbody == 14 and len(np_) == 14 and all('<w:ind w:firstLine="567"/>' in x for x in np_) and 'Heading1' not in np_[0])
opens = []; first = None
with pdfplumber.open(nt[:-3] + '.pdf') as d:
    for p in d.pages:
        rows = {}
        for c_ in p.chars:
            if c_['size'] > 15.9 and c_['width'] >= 0.5: rows.setdefault(round(c_['top'], 1), []).append(c_)
        for top, r in sorted(rows.items()):
            if len(r) < 20: continue
            x = p.width - 70.87 - max(c_['x1'] for c_ in r)
            if first is None: first = x
            if abs(x - 28.35) < 1: opens.append(x)
ok('no title (PDF): the first line of the article is indented 1 cm, and so is every paragraph', first is not None and abs(first - 28.35) < 1 and len(opens) == 14, f'first line {first:.1f} pt in; {len(opens)} indented lines')

# 13. digits the author typed as 123 are drawn as ١٢٣ in the PDF, so the reply has nothing to say about them. The PDF
#     still reports the character as typed; the glyph drawn is told by its width (Lotus draws 1 and ١ at different widths).
from fontTools.ttLib import TTFont
lf = TTFont(os.path.join(AF, lotus[1])); cm = lf.getBestCmap(); adv = lambda ch: lf['hmtx'][cm[ord(ch)]][0]
dg = os.path.join(OUT, 'digits.md')
open(dg, 'w', encoding='utf-8').write('قال تعالى: ﴿إن مع العسر يسرا﴾ [الشرح: 6]، وكما في [البقرة: 151]، وذلك في عام 2026 كما في (3/ 257) و(ت: 728هـ)[^1].\n[^1]: Aune, Kristin. Feminist Review, vol. 97, no. 1, 2011, pp. 32-55.\n')
run(os.path.join(SK, 'typeset.py'), dg, dg[:-3] + '.docx', 'lo'); mk.to_pdf(dg[:-3] + '.docx', dg[:-3] + '.pdf')
with pdfplumber.open(dg[:-3] + '.pdf') as d: digs = [c_ for c_ in d.pages[0].chars if c_['text'] in '0123456789' and c_['size'] > 9]
units = lambda c_: c_['width'] / c_['size'] * lf['head'].unitsPerEm
ar = [c_ for c_ in digs if 'LotusLotfi' in c_['fontname']]; la = [c_ for c_ in digs if 'LotusLotfi' not in c_['fontname']]
ok('PDF: digits typed as 123 in Arabic text are drawn as ١٢٣ (verse references too)', len(ar) == 17 and all(abs(adv(x) - adv(chr(0x660 + int(x)))) > 8 for x in '12356780')
   and all(abs(units(c_) - adv(chr(0x660 + int(c_['text'])))) < 4 for c_ in ar), f'{len(ar)} digits in Arabic text')
ok('PDF: digits inside Latin text stay 123', len(la) == 12, f'{len(la)} digits in Latin text')
own = [c_ for c_ in la if c_['x0'] < 85]   # the number of the Latin footnote itself, at the left text edge
ok('PDF: the number of a Latin footnote is Western, «(1)», in the note\'s own Latin font', len(own) == 1 and own[0]['text'] == '1' and abs(own[0]['size'] - 11) < 0.1
   and own[0]['fontname'] == la[-1]['fontname'] and abs(units(own[0]) - adv('1')) > 8, own[0]['fontname'].split('+')[-1] if own else 'not found')
ok('SKILL.md: the reply speaks of digits only when they look Western in the rendered pages', 'never suggest changing them' in reply and 'judge by the rendered pages' in reply)

# 14. the stress article (tests/formats/stress_article.docx, mapped into tests/inputs/stress_plain.md with no cover and
#     stress_cover.md with a cover and contents) — built once here, checked by the sections below
r, sd = to_md(os.path.join(T, 'formats', 'stress_article.docx'))
body = lambda md: [l for l in md.split('\n')[3:] if l.strip()]   # after the title and the two lines under it
plain_md, cover_md = (open(os.path.join(T, 'inputs', f'stress_{n}.md'), encoding='utf-8').read() for n in ('plain', 'cover'))
unmark = lambda ls: [re.sub(r'^### (.*)$', r'**\1**', l) for l in ls]
ok('stress article: the fixtures are the converted article, word for word', 'notes: 9' in r.stdout
   and unmark(body(plain_md)) == body(sd) and unmark([l for l in cover_md.split('\n')[6:] if l.strip()]) == body(sd))
ST = {n: os.path.join(OUT, 'stress_' + n) for n in ('plain', 'cover')}
st_run = {n: run(os.path.join(SK, 'make.py'), os.path.join(T, 'inputs', f'stress_{n}.md'), ST[n], *(['--uthmani'] if n == 'cover' else [])) for n in ST}
ok('stress article: both builds', all(x.returncode == 0 and os.path.exists(ST[n] + '.pdf') for n, x in st_run.items()), ' '.join(x.stderr[-120:] for x in st_run.values()))

# 15. an article with no cover runs on: a level-1 heading does not start a new page (with a cover, each one does).
#     No page may hold less than a quarter of what a full page holds, except the last. (Glyph boxes cover about 45%
#     of the text area on a full page, the rest being the space between lines; each page is set against the fullest.)
def covered(pdf):
    out = []
    with pdfplumber.open(pdf) as d:
        for p in d.pages:
            iv = sorted((c['top'], c['bottom']) for c in p.chars if c['width'] >= 0.5 and c['bottom'] < p.height - 70)
            tot = 0; cur = None
            for a, b in iv:
                if cur and a <= cur[1]: cur[1] = max(cur[1], b)
                else: tot += cur[1] - cur[0] if cur else 0; cur = [a, b]
            out.append(tot + (cur[1] - cur[0] if cur else 0))
    return [x / max(out) for x in out]
cov = covered(ST['plain'] + '.pdf')
ok('article with no cover: no page holds less than a quarter of a full page, except the last', len(cov) > 3 and all(x >= 0.25 for x in cov[:-1]), ' '.join(f'{x:.2f}' for x in cov))
spx = zipfile.ZipFile(ST['plain'] + '.docx').read('word/document.xml').decode(); scx = zipfile.ZipFile(ST['cover'] + '.docx').read('word/document.xml').decode()
h1p = [x for x in re.findall(r'<w:p>.*?</w:p>', spx) if 'Heading1' in x]; h1c = [x for x in re.findall(r'<w:p>.*?</w:p>', scx) if 'Heading1' in x]
ok('no cover: the title opens page 1, the later level-1 headings follow on with space above', len(h1p) == 8 and '<w:spacing w:before="1920"' in h1p[0]
   and all('<w:pageBreakBefore w:val="0"/>' in x and '<w:spacing w:before="720"/>' in x for x in h1p[1:]))
ok('with a cover: every level-1 heading starts a new page, as before', len(h1c) == 8 and 'pageBreakBefore w:val="0"' not in scx and 'w:before="1920"' not in scx)
ok('no cover: the text follows the title on the first page', cov[0] >= 0.5, f'{cov[0]:.2f} of a full page')

# 16. the honorific signs Lotus lacks (ﷻ ﷽ U+FD40–U+FD4F …) are set in Noto Naskh Arabic, character by character;
#     the author's characters stay as written, and the font goes into the fonts zip (with its licence) when it is used
SD = os.path.join(SK, '..', 'assets', 'symbols'); SF = os.path.join(SD, 'NotoNaskhArabic-Regular.ttf')
ok('symbols font: the file recorded in its SOURCE.md, unmodified, with its licence', hashlib.sha256(open(SF, 'rb').read()).hexdigest() in open(os.path.join(SD, 'SOURCE.md'), encoding='utf-8').read()
   and 'SIL Open Font License' in open(os.path.join(SD, 'OFL.txt'), encoding='utf-8').read() and sorted(os.listdir(SD)) == ['NotoNaskhArabic-Regular.ttf', 'OFL.txt', 'SOURCE.md'])
scm = TTFont(SF).getBestCmap(); want = [0xFDFB, 0xFDFD] + list(range(0xFD40, 0xFD50))
ok('symbols font: its own cmap covers ﷻ ﷽ and U+FD40–U+FD4F, which Lotus does not', all(c in scm for c in want) and not any(c in cm for c in want))
sym_line = 'والله ﷻ يحب العلماء، وعن أبي هريرة ﵁ قال، و﷽ في أول الكتاب، والنبي ﷺ، وهذا رمز ☀ ليس في خطوط المهارة.'
sym_md = os.path.join(OUT, 'symbols.md'); open(sym_md, 'w', encoding='utf-8').write('# رموز\n' + sym_line + '\n')
sym = os.path.join(OUT, 'symbols_out', 'symbols'); rs = run(os.path.join(SK, 'make.py'), sym_md, sym)
sx = zipfile.ZipFile(sym + '.docx').read('word/document.xml').decode()
runs_ = re.findall(r'<w:r><w:rPr>(.*?)</w:rPr><w:t[^>]*>([^<]*)</w:t></w:r>', sx)
in_noto = [t_ for rp, t_ in runs_ if 'w:cs="Noto Naskh Arabic"' in rp]
ok('Word file: ﷻ ﵁ ﷽ each in Noto Naskh Arabic, ﷺ (which Lotus has) left in Lotus, the text as written', in_noto == ['ﷻ', '\ufd41', '﷽']
   and any('ﷺ' in t_ and 'rFonts' not in rp for rp, t_ in runs_) and re.sub('[\u200f\u2060]', '', ''.join(t_ for _, t_ in runs_)).endswith(sym_line), str(in_noto))
with pdfplumber.open(sym + '.pdf') as d: pc = {c_['text']: c_['fontname'] for c_ in d.pages[0].chars}
ok('PDF: ﷻ ﵁ ﷽ drawn in Noto Naskh Arabic, ﷺ in Lotus Lotfi', all('NotoNaskhArabic' in pc.get(ch, '') for ch in 'ﷻ\ufd41﷽') and 'LotusLotfi' in pc.get('ﷺ', ''), str({k: v.split('+')[-1] for k, v in pc.items() if ord(k[0]) > 0x2000}))
szip = zipfile.ZipFile(os.path.join(OUT, 'symbols_out', 'خطوط-لملف-Word.zip'))
ok('fonts zip: the symbols font, unmodified, with its licence, when a character is set in it — and only then', szip.read('NotoNaskhArabic-Regular.ttf') == open(SF, 'rb').read()
   and szip.read('NotoNaskhArabic-OFL.txt') == open(os.path.join(SD, 'OFL.txt'), 'rb').read() and 'NotoNaskhArabic-Regular.ttf' not in zipfile.ZipFile(mk.fonts_zip(os.path.join(OUT, 'basic.docx'))).namelist())

# 17. a character drawn in a font outside the skill's own (a fallback like Unifont or DejaVu), or not drawn at all, is
#     reported by make.py in one Arabic line, with its pages, for the reply
fl = [l for l in rs.stdout.splitlines() if l.startswith('FONTS')]
ok('fallback fonts: make.py names the stray character and its page, in Arabic', len(fl) == 1 and '«☀» (ص ١)' in fl[0] and not any(ch in fl[0] for ch in 'ﷻ\ufd41﷽ﷺ')
   and not re.search('[A-Za-z]', fl[0].replace('FONTS', '').replace('PDF', '')), fl[0] if fl else 'no line')
ok('fallback fonts: none in the stress article, in either build', not any('FONTS' in x.stdout for x in st_run.values()), ' '.join(l for x in st_run.values() for l in x.stdout.splitlines() if l.startswith('FONTS')))
ok('SKILL.md: the reply passes the FONTS line on, with a ready-made sentence', 'FONTS' in reply and any('بخطٍّ آخر' in r_ for r_ in ready))

# 18. a Latin reference in an Arabic numbered list: the number stays at the start (the right), the Latin reads left to
#     right — a comma ending a line inside it, and the full stop that closes it, stay beside their words (Word and PDF)
li = os.path.join(OUT, 'latin_item.md')
open(li, 'w', encoding='utf-8').write('# عنوان\n\nنص تمهيدي.\n\n١- القرآن الكريم.\n٥- Bringhurst, Robert. The Elements of Typographic Style. Hartley & Marks, 1992.\n'
                                      '\nومن الكتب كتاب Bringhurst, Robert. The Elements of Typographic Style. Hartley & Marks, 1992. وهو من أشهر ما كُتب في أصول الصف والطباعة والنشر.\n')
run(os.path.join(SK, 'typeset.py'), li, li[:-3] + '_w.docx', 'word'); run(os.path.join(SK, 'typeset.py'), li, li[:-3] + '.docx', 'lo'); mk.to_pdf(li[:-3] + '.docx', li[:-3] + '.pdf')
lx = zipfile.ZipFile(li[:-3] + '_w.docx').read('word/document.xml').decode()
ok('Word file: each Latin run is held left to right (LRE…PDF); a Latin item\'s closing full stop is followed by a left-to-right mark',
   lx.count('>\u202aBringhurst, Robert. The Elements of Typographic Style. Hartley &amp; Marks, 1992\u202c</w:t>') == 2 and lx.count('>.\u200e</w:t>') == 1
   and '>. وهو' in lx)
with pdfplumber.open(li[:-3] + '.pdf') as d: cs = d.pages[0].chars
five = [c_ for c_ in cs if c_['text'] == '٥']; yr = [c_ for c_ in cs if five and c_['text'] == '2' and 'LotusLotfi' not in c_['fontname'] and 5 < c_['top'] - five[0]['top'] < 40]
dot = [c_ for c_ in cs if yr and c_['text'] == '.' and abs(c_['top'] - yr[0]['top']) < 8]
ok('PDF: a Latin item keeps its number at the right edge and its closing full stop after «1992»', len(five) == 1 and abs(five[0]['x1'] - (d.pages[0].width - 70.87)) < 1
   and len(dot) == 1 and dot[0]['x0'] >= max(c_['x1'] for c_ in cs if abs(c_['top'] - yr[0]['top']) < 8 and c_['text'] in '1992') - 0.5,
   f'number at {five[0]["x1"]:.1f}' if five else 'number not found')

# 19. footnotes start again at (1) on every page — also where LibreOffice moves a line to the next page because its
#     note no longer fits there: it keeps the number it gave on the page before, so make.py writes the numbers in.
#     One page per try: a short note, n one-line paragraphs, then a paragraph whose two-line note may no longer fit.
fp = os.path.join(OUT, 'note_pages'); paras, notes = [], []
for n in range(12, 26):
    k = len(notes)
    paras += ['@pagebreak'] * bool(k) + [f'فقرة فيها حاشية قصيرة[^{k + 1}].'] + ['هذه فقرة قصيرة تملأ سطرًا من الصفحة.'] * n + [f'وهذه فقرة فيها حاشية طويلة[^{k + 2}].', 'فقرة بعدها.']
    notes += [f'[^{k + 1}]: حاشية قصيرة.', f'[^{k + 2}]: حاشية طويلة بعض الطول حتى تأخذ سطرين في أسفل الصفحة، وهذه تتمة الكلام فيها لتطول قليلًا وتتجاوز السطر الواحد إلى ثانٍ.']
open(fp + '.md', 'w', encoding='utf-8').write('\n'.join(paras) + '\n\n' + '\n'.join(notes) + '\n')
run(os.path.join(SK, 'typeset.py'), fp + '.md', fp + '.docx', 'lo')
mk.lo(['--convert-to', 'pdf', '--outdir', OUT, fp + '.docx'])   # LibreOffice alone
raw = mk.note_refs(fp + '.pdf')
ok('the case reproduces LibreOffice numbering a moved note on from the page before', sum(map(len, raw)) == len(notes)
   and any(sorted(map(int, r)) != list(range(1, len(r) + 1)) for r in raw), str(raw))
mk.to_pdf(fp + '.docx', fp + '.pdf')
def note_numbers(pdf):
    """-> per page: (the numbers at the references in the text, the numbers that open the notes), as the PDF shows them"""
    out = []
    with pdfplumber.open(pdf) as d:
        for p in d.pages:
            rows, opens = {}, []
            for c_ in p.chars: rows.setdefault(round(c_['top']), []).append(c_)
            rows = [sorted(cs, key=lambda c_: -c_['x0']) for top, cs in sorted(rows.items())]
            # read across lines: LibreOffice may leave «)» of a reference at the head of the next line (CLAUDE.md, Known limits)
            refs = re.findall(r'\((\d+)\)', ''.join(c_['text'] for cs in rows for c_ in cs if c_['size'] < 10).translate(mk.DIG))
            for cs in rows:
                if not 10 < cs[0]['size'] < 13.5: continue
                if p.width - 70.85 - cs[0]['x1'] < 1: opens += re.findall(r'^\((\d+)\)', ''.join(c_['text'] for c_ in cs).translate(mk.DIG))
                elif cs[-1]['x0'] - 70.85 < 1 and 'Lotus' not in cs[-1]['fontname']:   # a Latin note: its number at the left edge
                    opens += re.findall(r'^\((\d+)\)', ''.join(c_['text'] for c_ in cs[::-1]))
            out.append((refs, opens))
    return out
for name, pdf, total in (('the case', fp + '.pdf', len(notes)), ('stress article, no cover', ST['plain'] + '.pdf', 9), ('stress article, cover', ST['cover'] + '.pdf', 9)):
    got = note_numbers(pdf)
    ok(f'PDF ({name}): footnotes are numbered 1, 2, 3… on every page, at the reference and in the note', sum(len(r) for r, _ in got) == total
       and all(r == [str(i + 1) for i in range(len(r))] for r, _ in got) and [x for r, _ in got for x in r] == [x for _, o in got for x in o],
       ' '.join(f'p{i + 1}:{",".join(r)}' for i, (r, _) in enumerate(got) if r))

import json
# 20. a contents page is never taken for the place of a heading: its level-1 entries are bold like the headings, and the
#     last one has nothing under it — it must not be read as a heading left alone at the foot of a page
para = 'هذه فقرة تجريبية في أدب الطلب، يُختبر بها توزيع العناوين على الصفحات حين يكون في المقالة فهرس للموضوعات بعد عنوانها.'
ca = os.path.join(OUT, 'toc_lone.md'); open(ca, 'w', encoding='utf-8').write('\n'.join(['# مقالة في أدب الطلب', para, '@toc']
    + [x for h in ('الباب في فضل النية', 'الباب في فضل الصبر', 'الباب في آداب المجالس', 'الخاتمة والتوصيات') for x in ['# ' + h] + [para] * 5]) + '\n')
tj = ca[:-3] + '.json'; json.dump([[h, '٥', l] for h, l in mk.headings(ca)], open(tj, 'w'), ensure_ascii=False)   # the contents, with their entries
run(os.path.join(SK, 'typeset.py'), ca, ca[:-3] + '.docx', 'lo', tj); mk.to_pdf(ca[:-3] + '.docx', ca[:-3] + '.pdf')
ok('a contents page is not read as a heading left alone at the foot of a page', mk.lone_heads(ca[:-3] + '.pdf', mk.keep_heads(ca)) == [], str(mk.lone_heads(ca[:-3] + '.pdf', mk.keep_heads(ca))))

# 21. with a cover, the text starts on the next page even when it does not open with a level-1 heading or the contents
cv = os.path.join(OUT, 'cover_h2.md'); open(cv, 'w', encoding='utf-8').write('---\ntitle: بحث تجريبي\nauthor: اسم المؤلف\n---\n## المطلب الأول\n' + '\n'.join([para] * 4) + '\n')
cvo = os.path.join(OUT, 'cover_h2_out', 'c'); run(os.path.join(SK, 'make.py'), cv, cvo)
with pdfplumber.open(cvo + '.pdf') as d: pg = [p.extract_text() or '' for p in d.pages]
ok('cover: the text after it starts a new page even without a level-1 heading', len(pg) == 2 and 'لولأا' not in pg[0].replace(' ', '') and 'الأول' not in pg[0]
   and ('لولأا' in pg[1].replace(' ', '') or 'الأول' in pg[1]), ' | '.join(x[:30] for x in pg))

# 22. what the review of these changes found
# a) a heading with ﷻ (drawn in the symbols font, which has no bold) still gets its page in the contents
hz = os.path.join(OUT, 'sign_heading.md'); open(hz, 'w', encoding='utf-8').write('---\ntitle: بحث\n---\n@toc\n# المبحث الأول: الله ﷻ\n' + para + '\n## مطلب ﷽\n' + para + '\n# المبحث الثاني\n' + para + '\n')
rz = run(os.path.join(SK, 'make.py'), hz, os.path.join(OUT, 'sign_heading_out', 'h'))
tz = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', zipfile.ZipFile(os.path.join(OUT, 'sign_heading_out', 'h.docx')).read('word/document.xml').decode()))
ok('contents: a heading with ﷻ or ﷽ gets its page number', 'page not found' not in rz.stdout and '؟' not in tz and tz.count('\t٣') == 2, rz.stdout.strip()[:120])
# b) a character no font has, drawn as an empty glyph in Times, is reported too
nz = os.path.join(OUT, 'no_glyph.md'); open(nz, 'w', encoding='utf-8').write('# عنوان\nنص فيه حرف جاوي ꦄ لا يحويه خط.\n')
rn_ = run(os.path.join(SK, 'make.py'), nz, os.path.join(OUT, 'no_glyph_out', 'n'))
ok('fallback fonts: a character that no font draws is reported as well', '«ꦄ» (ص ١)' in rn_.stdout, ' '.join(l for l in rn_.stdout.splitlines() if l.startswith('FONTS')) or 'no FONTS line')
# c) in a Latin footnote, ﷺ stays in Lotus and ﷻ goes to the symbols font — never Times, which has neither
lz = os.path.join(OUT, 'latin_signs.md'); open(lz, 'w', encoding='utf-8').write('# عنوان\nنص[^1].\n[^1]: Muslim, Sahih: the Prophet ﷺ said that Allah ﷻ loves knowledge, vol. 3, p. 12.\n')
run(os.path.join(SK, 'typeset.py'), lz, lz[:-3] + '.docx', 'word')
fz = re.findall(r'<w:r><w:rPr>(.*?)</w:rPr><w:t[^>]*>([^<]*)</w:t></w:r>', zipfile.ZipFile(lz[:-3] + '.docx').read('word/footnotes.xml').decode())
ok('Latin footnote: ﷺ in Lotus, ﷻ in Noto Naskh Arabic, neither in Times', [rp for rp, x in fz if 'ﷺ' in x] and all('rFonts' not in rp for rp, x in fz if 'ﷺ' in x)
   and [x for rp, x in fz if 'Noto Naskh Arabic' in rp] == ['ﷻ'] and not any('Times' in rp and re.search('[\ufd00-\ufdff]', x) for rp, x in fz))
# d) an article with no cover and a contents: the contents follow the title on page 1, the text starts on page 2,
#    and the contents' page numbers are right
az = os.path.join(OUT, 'article_toc.md'); open(az, 'w', encoding='utf-8').write('\n'.join(['# مقالة في أدب الطلب', '>> اسم الكاتب', '@toc']
    + [x for h in ('الباب في فضل النية', 'الباب في فضل الصبر', 'الخاتمة') for x in ['# ' + h] + [para] * 6]) + '\n')
ao = os.path.join(OUT, 'article_toc_out', 'a'); ra_ = run(os.path.join(SK, 'make.py'), az, ao)
ax = zipfile.ZipFile(ao + '.docx').read('word/document.xml').decode(); aps = re.findall(r'<w:p>.*?</w:p>', ax)
tc = run(os.path.join(T, 'toc_check.py'), ao).stdout
with pdfplumber.open(ao + '.pdf') as d: p1 = d.pages[0]; big = [c_ for c_ in p1.chars if c_['size'] > 17]; dots = sum(c_['text'] == '.' for c_ in p1.chars)
ok('article with contents: title and contents on page 1, the text from page 2, the page numbers right', '<w:spacing w:before="1920"' in aps[0] and dots > 30 and len(big) > 10
   and ', 0 wrong' in tc and 'page not found' not in ra_.stdout and any('pageBreakBefore w:val="0"' in x and 'فهرس الموضوعات' in x for x in aps), tc.strip()[-60:])

# 23. LibreOffice 24.2 looped for ever on a note like this one (a source reference whose first line holds the tab after
#     the note's number), with its Word-imitating space shrinking on: the PDF route turns it off, and every conversion
#     has a time limit
import time
t0 = time.time(); nh = os.path.join(OUT, 'note_hang'); rh = run(os.path.join(SK, 'make.py'), os.path.join(T, 'inputs', 'note_hang.md'), nh)
ok('a source reference in a note no longer hangs the PDF engine', rh.returncode == 0 and os.path.exists(nh + '.pdf') and time.time() - t0 < 600, f'{time.time() - t0:.0f} s')
mk_src = open(os.path.join(SK, 'make.py'), encoding='utf-8').read()
ok('the PDF route turns off space shrinking only for a document that stalls, and limits every conversion', 'JustifyLinesWithShrinking" config:type="boolean">false' in mk_src
   and "if it.filename == 'settings.xml' and NO_SHRINK" in mk_src and 'timeout=limit' in mk_src)

# 23b. one file: the Word file delivered is the very file the PDF is exported from
art_docx = os.path.join(OUT, 'article.docx'); again = os.path.join(OUT, 'article_again.pdf'); mk.to_pdf(art_docx, again)
def page_texts(pdf):
    with pdfplumber.open(pdf) as d: return [(pg.extract_text() or '') for pg in d.pages]
ok('the PDF is exported from the delivered Word file itself: exporting that file again gives the same pages', page_texts(again) == page_texts(os.path.join(OUT, 'article.pdf'))
   and len(page_texts(again)) >= 1)
ok('the Word file numbers its notes with its own brackets; the PDF route drops them only in its intermediate file', '<w:t>‏(‏</w:t></w:r><w:r><w:rPr><w:sz w:val="26"/><w:szCs w:val="26"/><w:rtl/></w:rPr><w:footnoteRef/>'
   in zipfile.ZipFile(art_docx).read('word/footnotes.xml').decode() and not re.search(r'\(\s*\)', ''.join(page_texts(again))))

# 24. index marks, «***» and citations leave the author's words as they are
import indexes as ixm, cite as ct
ts.IX.clear(); ts.IX_WANT.clear(); ts.UTHMANI = False
mkt = 'قال {{علم|ابن تيمية}} و{{علم|شيخ الإسلام|ابن تيمية}} ونزل {{مكان|مكة}}.'
vis = re.sub('[⁠‏‎‪‬⟦⟧⟬⟭`]|⟮\\d+⟯', '', ts.inline(mkt, {})).replace(' ', ' ')
ok('index marks: the words stay, only the braces, the kind and the extra fields go', vis == 'قال ابن تيمية وشيخ الإسلام ونزل مكة.' and len(ts.IX) == 3
   and [e['entry'] for e in ts.IX] == ['ابن تيمية', 'ابن تيمية', 'مكة'] and ixm.strip_marks(mkt) == 'قال ابن تيمية وشيخ الإسلام ونزل مكة.')
poem = ts.runs(ts.inline('العلم يرفع بيتًا *** والجهل يهدم بيت العز', {}))
ok('three asterisks between two halves of a verse are the author\'s text, not bold', '***' in ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', poem)) and '<w:b/>' not in poem)
ok('alphabetical order: hamza seats folded, «ال» left out for names, letters in their order', ixm.key('الأَنصار', True) == 'انصار' and ixm.key('إبراهيم') == 'ابراهيم'
   and sorted(['يحيى', 'البخاري', 'أحمد', 'عمر'], key=lambda x: ixm.order(ixm.key(x, True))) == ['أحمد', 'البخاري', 'عمر', 'يحيى'])
ok('rhyme letter of a verse: its last letter, past a final letter of prolongation', ixm.rhyme('والجهل يهدم بيت العز والشرفِ') == 'ف' and ixm.rhyme('قفا نبك من ذكرى حبيب ومنزلِي') == 'ل')
ok('the opening basmala is recognised with or without marks, and nothing else is', all(ixm.is_basmala(x) for x in ('بسم الله الرحمن الرحيم', 'بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ', '﷽', '>> بسم الله الرحمن الرحيم'))
   and not any(ixm.is_basmala(x) for x in ('بسم الله', 'بسم الله الرحمن الرحيم والحمد لله', 'باسم الله الرحمن الرحيم')))
hit, why = q.place(im('51:56'), ('الذاريات', '٥٦')); many_hit, many_why = q.place(bare(im('55:13')), None)
ok('verse index: a verse is placed by its letters; a wording found in many places needs its reference', hit and hit[:3] == (51, 56, 56) and not why and many_hit and 'أكثر من موضع' in many_why)
ts.IX_WANT.add('آية'); ts.IX.clear(); ts.IX_UNPLACED.clear()
ts.inline('قال تعالى: ﴿' + im('51:56') + '﴾ [الذاريات: ٥٦] و﴿' + bare(im('55:13')) + '﴾', {})
ok('verse index: entries for placed verses, the others reported in Arabic', [e['place'] for e in ts.IX] == [(51, 56, 56)] and len(ts.IX_UNPLACED) == 1
   and not re.search('[A-Za-z]', ts.IX_UNPLACED[0][1]))
ts.IX_WANT.clear(); ts.IX.clear(); ts.IX_UNPLACED.clear()
srcs = ct.load(os.path.join(T, 'inputs', 'sources.json'))
ok('citations: Chicago full the first time, short after; author-date for APA and Harvard; MLA author and short title',
   ct.note(srcs['fatawa'], '٣/ ٤٥', 'chicago', True).startswith('أحمد بن عبد الحليم ابن تيمية (ت: ٧٢٨هـ)، **مجموع الفتاوى**، تحقيق: عبد الرحمن بن محمد بن قاسم (المدينة المنورة: ')
   and ct.note(srcs['fatawa'], '٣/ ٤٥', 'chicago', False) == 'ابن تيمية، **الفتاوى**، ٣/ ٤٥' and ct.note(srcs['fatawa'], '٣/ ٤٥', 'apa', True) == 'ابن تيمية (١٤١٦هـ)، ٣/ ٤٥'
   and ct.note(srcs['fatawa'], '٣/ ٤٥', 'harvard', True) == 'ابن تيمية ١٤١٦هـ، ٣/ ٤٥' and ct.note(srcs['fatawa'], '٣/ ٤٥', 'mla', True) == 'ابن تيمية، **الفتاوى**، ٣/ ٤٥')
ok('citations: the list of sources in each style; a Latin title in italic, APA initials', ct.bib(srcs['aune'], 'apa') == 'Aune, K. (2011). Much Less Religious, A Little More Spiritual. ⟨Feminist Review⟩, 97(1), 32-55.'
   and ct.bib(srcs['aune'], 'chicago') == 'Aune, Kristin. "Much Less Religious, A Little More Spiritual". ⟨Feminist Review⟩ 97, no. 1 (2011): 32-55.'
   and ct.bib(srcs['lisan'], 'chicago') == 'ابن منظور، محمد بن مكرم (ت: ٧١١هـ). **لسان العرب**. ط٣. بيروت: دار صادر، ١٤١٤هـ.')
ok('citations: what a style needs and a source lacks is reported, in Arabic; what a style leaves out is not asked for',
   ct.report(srcs, 'chicago') == ['CITE: ينقص «صحيح البخاري» لنظام Chicago: مكان النشر'] and ct.report(srcs, 'apa') == [] and ct.report(srcs, 'mla') == [])
ts.CITES = srcs; ts.CITE_STYLE = 'chicago'; ts.CITED.clear()
c1 = ts.expand_cites('{{مرجع|bukhari|١/ ٦}}، رقم (١).'); c2 = ts.expand_cites('انظر: {{مرجع|bukhari|٢/ ٣}}')
ok('citations: a full stop only where the citation ends the note; the author\'s words around it untouched', c1.endswith('١/ ٦، رقم (١).') and '.،' not in c1 and c2 == 'انظر: البخاري، **الصحيح**، ٢/ ٣.')
try: ts.expand_cites('{{مرجع|nosuch|١}}'); unknown = False
except SystemExit as e: unknown = 'unknown source id' in str(e)
ok('citations: an unknown source stops the build instead of printing a mark', unknown)
ts.CITES = {}; ts.CITE_STYLE = None; ts.CITED.clear()
body = ['@sort', 'يحيى', 'البخاري', 'أحمد', '@end', '@sort', '١- ب', '٢- أ', '@end']
ok('@sort: the author\'s lines in alphabetical order, each unchanged; a numbered list keeps its order', ts.sort_blocks(body) == ['أحمد', 'البخاري', 'يحيى', '١- ب', '٢- أ'] and ts.SORT_KEPT == [2])
ts.SORT_KEPT.clear()

# 25. everything on request together: indexes, Chicago citations, a running header, the calligraphic basmala
ix = os.path.join(OUT, 'indexes'); rix = run(os.path.join(SK, 'make.py'), os.path.join(T, 'inputs', 'indexes.md'), ix, '--cite=chicago',
                                            f'--sources={os.path.join(T, "inputs", "sources.json")}', '--basmala=7')
ok('build: indexes, citations, header, basmala', rix.returncode == 0 and os.path.exists(ix + '.pdf'), rix.stderr[-300:])
X = {n: zipfile.ZipFile(ix + '.docx').read(n).decode() for n in ('word/document.xml', 'word/footnotes.xml', 'word/header1.xml', 'word/header2.xml', 'word/footer2.xml')}
dests = mk.dest_pages(ix + '.pdf')
ok('every index entry has a bookmark whose page the PDF names', len([k for k in dests if k.startswith('_ix')]) == X['word/document.xml'].count('w:name="_ix') and len(dests) >= 20, f'{len(dests)} pages read')
lines = [''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', p_)) for p_ in re.findall(r'<w:p>.*?</w:p>', X['word/document.xml']) if 'w:leader="dot"' in p_]
H2D = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
def pages_in(t): return [int(x.translate(H2D)) for x in re.findall(r'[٠-٩]+', t.rsplit('\t', 1)[-1])] if '\t' in t else []
first_index = min(int(x) for x in [p_.translate(H2D) for t_ in lines if 'فهرس الآيات القرآنية' in t_ for p_ in re.findall(r'[٠-٩]+$', t_)])
ok('the contents list every index with its page', all(any(k in t_ and t_.rsplit('\t', 1)[-1].strip() not in ('٠٠', '؟') for t_ in lines) for k in ixm.KINDS.values()) and first_index > 4)
ent = [t_ for t_ in lines if not any(k in t_ for k in list(ixm.KINDS.values()) + ['المقدمة', 'المبحث', 'المطلب', 'الخاتمة'])]
ok('every index entry has its page numbers, none left at ٠٠ or ؟', len(ent) >= 18 and all(pages_in(t_) and '٠٠' not in t_ and '؟' not in t_ for t_ in ent), ' | '.join(ent[:3]))
mark_pages = {e: p_ for e, p_ in dests.items()}
yahya = [t_ for t_ in ent if t_.startswith('يحيى بن سعيد الأنصاري')]; taym = [t_ for t_ in ent if t_.startswith('ابن تيمية')]
ok('people index: one entry for the different names given the same entry, the extra form not listed', len(taym) == 1 and not any(t_.startswith('شيخ الإسلام') or t_.startswith('الإمام أحمد') for t_ in ent)
   and any(t_.startswith('أحمد بن حنبل') for t_ in ent))
def reading(pg, cond=lambda c_: True):   # a page's text in reading order: line by line, each from the right
    rows = {}
    for c_ in pg.chars:
        if cond(c_): rows.setdefault(round(c_['top']), []).append(c_)
    return ''.join(c_['text'] for t_, cs_ in sorted(rows.items()) for c_ in sorted(cs_, key=lambda c_: -c_['x0']))
with pdfplumber.open(ix + '.pdf') as d:
    texts = [mk.norm(reading(pg)) for pg in d.pages]
    tops = [reading(pg, lambda c_: c_['top'] < 60) for pg in d.pages]
    basm = [(c_['fontname'], n_) for n_, pg in enumerate(d.pages, 1) for c_ in pg.chars if c_['text'] == chr(0x1EE06)]
ar = lambda s_: mk.norm(s_)
body_pages = range(1, first_index)
def on(word): return [n_ for n_ in body_pages if ar(word) in texts[n_ - 1]]
ok('index pages are the pages where the entries stand in the text', pages_in(yahya[0]) == on('يحيى بن سعيد الأنصاري')
   and pages_in([t_ for t_ in ent if 'لَّا لِيَعْبُدُون' in t_ or 'ليعبدون' in t_][0]) == on('الذاريات')[:1], f'{yahya} {on("يحيى بن سعيد الأنصاري")}')
quran_lines = [t_ for t_ in ent if t_.startswith('﴿')]
ok('verse index: by surah in the Mushaf\'s order, each verse with its ayah number', len(quran_lines) == 3 and '[١٤٣]' in quran_lines[0] and '[٥٦]' in quran_lines[1] and '[٦]' in quran_lines[2]
   and X['word/document.xml'].find('سورة البقرة') < X['word/document.xml'].find('سورة الذاريات') < X['word/document.xml'].find('سورة الشرح'))
ok('poetry index: grouped by rhyme letter, the author\'s «***» kept', 'قافية الفاء' in X['word/document.xml'] and any('***' in t_ for t_ in ent))
fx = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', X['word/footnotes.xml'])).replace('⁠', '').replace(' ', ' ')
ok('citations in the notes: Chicago full first, short after, the author\'s words kept', 'أحمد بن عبد الحليم ابن تيمية (ت: ٧٢٨هـ)، مجموع الفتاوى، تحقيق' in fx
   and 'انظر: ابن تيمية، الفتاوى، ١٠/ ١٢، وفيه ذكر الحسن البصري.' in fx and '١/ ٦، رقم (١).' in fx and '{{' not in fx)
ok('citations: make.py reports what the style still lacks, in Arabic', 'CITE: ينقص «صحيح البخاري» لنظام Chicago: مكان النشر' in rix.stdout)
src_list = X['word/document.xml'][X['word/document.xml'].rfind('فهرس المصادر والمراجع'):]
ok('list of sources: alphabetical, in the style, a Latin source left to right', src_list.find('ابن تيمية') < src_list.find('ابن منظور') < src_list.find('البخاري') < src_list.find('Aune')
   and '<w:bidi w:val="0"/>' in src_list and 'Feminist Review' in src_list)
with pdfplumber.open(ix + '.pdf') as d:   # the number at the head of the Latin note: on the line of its first word
    lat = [c_ for pg in d.pages for k_ in pg.chars if k_['text'] == 'K' and k_['top'] > 650 for c_ in pg.chars if abs(c_['top'] - k_['top']) < 2 and c_['text'] in '1١' and c_['x0'] < k_['x0']]
ok('PDF: a Latin note with an italic title keeps its Western number «(1)» in Times', lat and all(c_['text'] == '1' and 'Liberation' in c_['fontname'] or 'Times' in c_['fontname'] for c_ in lat), str([(c_['text'], c_['fontname']) for c_ in lat]))
ok('header: the title on every page but the first, over a rule; the first page keeps its number when it has no cover', 'أثر العلم في بناء الإنسان' in X['word/header1.xml']
   and 'w:pBdr' in open(os.path.join(SK, 'typeset.py'), encoding='utf-8').read() and 'أثر العلم' not in X['word/header2.xml'] and '<w:titlePg/>' in X['word/document.xml']
   and ar('أثر العلم في بناء الإنسان') not in ar(tops[0]) and all(ar('أثر العلم في بناء الإنسان') in ar(t_) for t_ in tops[1:]))
ok('basmala: the opening line set as Lotus Lotfi\'s basmala, the text untouched otherwise', chr(0x1EE06) in X['word/document.xml'] and 'بسم الله الرحمن الرحيم' not in X['word/document.xml']
   and basm and all('LotusLotfi' in f_ for f_, n_ in basm) and 'FONTS' not in rix.stdout)
rn_off = run(os.path.join(SK, 'typeset.py'), os.path.join(T, 'inputs', 'indexes.md'), os.path.join(OUT, 'ix_plain.docx'), 'word', '--cite=chicago', f'--sources={os.path.join(T, "inputs", "sources.json")}')
ok('without --basmala the opening basmala stays as written', 'بسم الله الرحمن الرحيم' in zipfile.ZipFile(os.path.join(OUT, 'ix_plain.docx')).read('word/document.xml').decode())

tl = os.path.join(OUT, 'toc_late.md'); open(tl, 'w', encoding='utf-8').write('# عنوان المقالة\nنص فيه {{علم|ابن تيمية}}.\n# المبحث الأول\nنص.\n@index علم\n@toc\n')
run(os.path.join(SK, 'typeset.py'), tl, os.path.join(OUT, 'toc_late.docx'), 'word')
tlx = [p_ for p_ in re.findall(r'<w:p>.*?</w:p>', zipfile.ZipFile(os.path.join(OUT, 'toc_late.docx')).read('word/document.xml').decode()) if 'فهرس الموضوعات' in p_ and 'Heading1' in p_]
ok('contents placed after the text start a page of their own, in an article too', len(tlx) == 1 and 'pageBreakBefore w:val="0"' not in tlx[0])

# 26. Traditional Arabic on request (a stand-in font here: the real files are added to assets/traditional)
import shutil as sh
tdir = os.path.join(OUT, 'trad_fonts'); os.makedirs(tdir, exist_ok=True)
for f_ in ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'): sh.copy(os.path.join('/usr/share/fonts/truetype/dejavu', f_), tdir)
ta = os.path.join(OUT, 'trad.md'); open(ta, 'w', encoding='utf-8').write('بسم الله الرحمن الرحيم\n# عنوان المقالة\n@header\n@toc\n# المقدمة\nنص المقدمة[^1].\n## المطلب الأول\nنص.\n[^1]: حاشية.\n')
to_ = os.path.join(OUT, 'trad_out', 'a')
rt = subprocess.run([sys.executable, os.path.join(SK, 'make.py'), ta, to_, '--font=traditional', '--basmala=1'], capture_output=True, text=True, env={**os.environ, 'SAFFAF_TRADITIONAL_DIR': tdir})
tz = sorted(zipfile.ZipFile(os.path.join(OUT, 'trad_out', 'خطوط-لملف-Word.zip')).namelist()) if rt.returncode == 0 else []
td = zipfile.ZipFile(to_ + '.docx').read('word/document.xml').decode() if rt.returncode == 0 else ''
ok('Traditional Arabic: the body in it, the basmala in Lotus Lotfi, both in the fonts zip', rt.returncode == 0 and tz == ['DejaVuSans-Bold.ttf', 'DejaVuSans.ttf', '_LotusLotfi-Bold.ttf', '_LotusLotfi-Regular.ttf']
   and 'w:cs="_Lotus Lotfi"' in td and 'DejaVu Sans' in zipfile.ZipFile(to_ + '.docx').read('word/styles.xml').decode() and 'FONTS' not in rt.stdout, rt.stderr[-200:])
with pdfplumber.open(to_ + '.pdf') as d: tf = {c_['fontname'].split('+')[-1] for pg in d.pages for c_ in pg.chars}; t1 = mk.norm(reading(d.pages[0]))
ok('Traditional Arabic (PDF): only its two faces and Lotus for the basmala; the title and the contents on page 1', tf == {'DejaVuSans', 'DejaVuSans-Bold', '_LotusLotfi'} and mk.norm('عنوان المقالة') in t1 and mk.norm('فهرس الموضوعات') in t1, str(tf))
rt2 = subprocess.run([sys.executable, os.path.join(SK, 'typeset.py'), ta, os.path.join(OUT, 'x.docx'), 'word', '--font=traditional'], capture_output=True, text=True, env={**os.environ, 'SAFFAF_TRADITIONAL_DIR': os.path.join(OUT, 'no_such_dir')})
ok('Traditional Arabic asked for without its files: a clear stop', rt2.returncode != 0 and 'assets/traditional' in rt2.stderr)

# 26b. the real Traditional Arabic pair in assets/traditional: its bold face is used (fontconfig is told its old-scale
#      weight), and the contents find every heading
if os.path.exists(os.path.join(SK, '..', 'assets', 'traditional', 'trado.ttf')):
    tr2 = os.path.join(OUT, 'trad_real', 'a'); env2 = {k_: v_ for k_, v_ in os.environ.items() if k_ != 'SAFFAF_TRADITIONAL_DIR'}
    rr = subprocess.run([sys.executable, os.path.join(SK, 'make.py'), os.path.join(T, 'inputs', 'indexes.md'), tr2, '--font=traditional', '--cite=chicago',
                         f'--sources={os.path.join(T, "inputs", "sources.json")}'], capture_output=True, text=True, env=env2)
    with pdfplumber.open(tr2 + '.pdf') as d: rf = {c_['fontname'].split('+')[-1] for pg in d.pages for c_ in pg.chars}
    ok('Traditional Arabic (real files): regular and bold faces both drawn, every heading found, no stray font', rr.returncode == 0 and any('Bold' in f_ and 'Traditional' in f_ for f_ in rf)
       and any(f_ == 'TraditionalArabic' for f_ in rf) and 'page not found' not in rr.stdout and 'FONTS' not in rr.stdout, f'{sorted(rf)} {rr.stdout[-200:]}')

# 26c. page numbers each program computes for itself: every number in the contents and the indexes is a PAGEREF field
#      to a bookmark; the file asks Word to update its fields; LibreOffice computes them as it lays the PDF out
ixd = zipfile.ZipFile(ix + '.docx').read('word/document.xml').decode(); ixs = zipfile.ZipFile(ix + '.docx').read('word/settings.xml').decode()
refs_ = re.findall(r'PAGEREF (_(?:toc|ix|fn)\d+) ', ixd)
ok('contents and indexes: their page numbers are fields to bookmarks in the text, and Word is asked to update them', len(refs_) >= 30 and all(f'w:name="{r_}"' in ixd for r_ in set(refs_))
   and '<w:updateFields w:val="true"/>' in ixs and len([r_ for r_ in refs_ if r_.startswith('_toc')]) == 15)
fk = os.path.join(OUT, 'fake_pages.json'); open(fk, 'w').write('{"_toc1": 77, "_toc2": 77}')
run(os.path.join(SK, 'typeset.py'), os.path.join(T, 'inputs', 'long_toc.md'), os.path.join(OUT, 'fake.docx'), 'word', f'--pages={fk}')
mk.to_pdf(os.path.join(OUT, 'fake.docx'), os.path.join(OUT, 'fake.pdf'))
with pdfplumber.open(os.path.join(OUT, 'fake.pdf')) as d: ftxt = ''.join(pg.extract_text() or '' for pg in d.pages[:3])
ok('the PDF engine computes the page numbers itself, whatever value the file stores', '77' not in ftxt and '٧٧' not in ftxt and '٧٧' in zipfile.ZipFile(os.path.join(OUT, 'fake.docx')).read('word/document.xml').decode())

# 27. symbol fonts (AGA Arabesque stores ﷺ as «e»; the table is read from the font itself): reported always, converted
#     only with --symbols, and only the signs that have a standard character
ag0 = run(os.path.join(SK, 'to_md.py'), os.path.join(T, 'formats', 'aga_symbols.docx'), os.path.join(OUT, 'aga0.md')); a0 = open(os.path.join(OUT, 'aga0.md'), encoding='utf-8').read()
ag1 = run(os.path.join(SK, 'to_md.py'), os.path.join(T, 'formats', 'aga_symbols.docx'), os.path.join(OUT, 'aga1.md'), '--symbols'); a1 = open(os.path.join(OUT, 'aga1.md'), encoding='utf-8').read()
ok('symbol fonts: reported, and the text left as written without --symbols', '«e»×1 = ﷺ' in ag0.stdout and '«a»×1 (meaning unknown' in ag0.stdout and 'قال النبي e:' in a0)
ok('symbol fonts: with --symbols the known signs become their standard characters; an ornament stays', a1 == a0.replace('النبي e', 'النبي ﷺ').replace('عمر t', 'عمر ﵁').replace('وموسى u', 'وموسى ﵇')
   .replace('والله U', 'والله ﷿').replace('ورسوله r', 'ورسوله ﷺ') and 'وزخرفة a' in a1)
r0, m0 = to_md(os.path.join(T, 'formats', 'stress_article.docx'))
r1 = run(os.path.join(SK, 'to_md.py'), os.path.join(T, 'formats', 'stress_article.docx'), os.path.join(OUT, 'sym.md'), '--symbols'); m1 = open(os.path.join(OUT, 'sym.md'), encoding='utf-8').read()
ok('symbol fonts: a letter the font draws as an ornament («a») is never taken for ﷺ', '«a»×1 (meaning unknown' in r0.stdout and m1 == m0 and 'وقال النبي a:' in m1)

# 28. the settings panel: analyze.py reads the draft; SKILL.md tells Claude to ask before typesetting
ra2 = run(os.path.join(SK, 'analyze.py'), os.path.join(T, 'inputs', 'indexes.md')).stdout
ok('analyze.py: what the text holds, for the panel', 'opens with the basmala: True' in ra2 and 'verses marked by the author: 3' in ra2 and 'citation style' in ra2)
ok('SKILL.md: the panel comes before typesetting, and every option is documented', '## The settings panel' in skill_md and 'wait for the answer' in skill_md
   and all(x in skill_md for x in ('--font=traditional', '--basmala=N', '--cite=', '--symbols', '@header', '@index', '@sort', 'basmala-shapes.png'))
   and os.path.exists(os.path.join(SK, '..', 'assets', 'basmala-shapes.png')))
ok('the bounded exceptions are stated in CLAUDE.md and SKILL.md alike', all(all(x in d_ for x in ('Citation style', 'basmala', 'Symbol fonts')) for d_ in (rules, skill_md)))

failed = [n for n, p, _ in results if not p]
print(f'\n{len(results) - len(failed)}/{len(results)} passed. Outputs: {OUT}')
sys.exit(1 if failed else 0)

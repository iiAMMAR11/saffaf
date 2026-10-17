#!/usr/bin/env python3
"""One-shot pipeline: input.md -> OUT.docx (for Word) + OUT.pdf (via LibreOffice), with auto TOC.
usage: python3 make.py input.md OUTPUT_DIR/NAME [--uthmani]   (writes NAME.docx, NAME.pdf and the fonts zip)
--uthmani: set the verses between ﴿ ﴾ in Uthmani script — only when the user asked for it."""
import os, sys, re, json, shutil, subprocess, tempfile, zipfile, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__))
# claude.ai ships a sandbox-safe LibreOffice wrapper with its docx skill; elsewhere call soffice directly
SOFFICE = '/mnt/skills/public/docx/scripts/office/soffice.py'
SOFFICE_CMD = ['python3', SOFFICE] if os.path.exists(SOFFICE) else [shutil.which('soffice') or shutil.which('libreoffice') or 'soffice']
PROFILE = '/tmp/ar_typeset_lo'

def setup():
    # Linux: fontconfig reads ~/.fonts. Elsewhere (macOS): headless LibreOffice ignores the system font
    # folders and only sees its bundled fonts plus <profile>/user/fonts, so the fonts go there.
    fd = os.path.expanduser('~/.fonts') if sys.platform.startswith('linux') else PROFILE + '/user/fonts'
    os.makedirs(fd, exist_ok=True)
    for f in os.listdir(os.path.join(HERE, '..', 'assets', 'fonts')):
        shutil.copy(os.path.join(HERE, '..', 'assets', 'fonts', f), fd)
    shutil.copy(os.path.join(HERE, '..', 'assets', 'symbols', 'NotoNaskhArabic-Regular.ttf'), fd)
    if UTHMANI: shutil.copy(os.path.join(HERE, '..', 'assets', 'quran', 'UthmanicHafs_V22.ttf'), fd)
    if shutil.which('fc-cache'): subprocess.run(['fc-cache', '-f'], capture_output=True)
    os.makedirs(PROFILE + '/user', exist_ok=True)
    open(PROFILE + '/user/registrymodifications.xcu', 'w').write(
        '<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<item oor:path="/org.openoffice.Office.Common/I18N/CTL"><prop oor:name="CTLTextNumerals" oor:op="fuse"><value>3</value></prop></item>'
        '<item oor:path="/org.openoffice.Office.Common/I18N/CTL"><prop oor:name="CTLFont" oor:op="fuse"><value>true</value></prop></item></oor:items>')

def lo(args):
    subprocess.run(SOFFICE_CMD + [f'-env:UserInstallation=file://{PROFILE}', '--headless'] + args, capture_output=True)

def patch_odt(src, dst, labels=None):
    """LibreOffice's ODT of the Word file, with our note settings; labels: each footnote's number, when written in by hand."""
    zin = zipfile.ZipFile(src); zout = zipfile.ZipFile(dst, 'w')
    for it in zin.infolist():
        data = zin.read(it.filename)
        if it.filename in ('styles.xml', 'content.xml'):
            t = data.decode()
            def fix(m):
                tag = m.group(0)
                if 'endnote' in tag: return tag
                tag = re.sub(r'\s(style:num-prefix|style:num-suffix)="[^"]*"', '', tag)
                # the number inside the note sits on the line, not raised
                tag = re.sub(r'text:citation-style-name="[^"]*"', 'text:citation-style-name="Note_20_Label"', tag)
                return tag.replace('<text:notes-configuration', '<text:notes-configuration style:num-prefix="(" style:num-suffix=")"', 1)
            t = re.sub(r'<text:notes-configuration[^>]*>', fix, t)
            # LibreOffice drops the tab after the note's own number when it reads the Word file, so the text of the
            # first line runs straight on from «(1)»; give it back (once) so the text starts where its later lines hang.
            # The tab goes inside the first span: the number takes the look of what begins the note (a Latin note's
            # number stays Western, in its Latin font).
            t = re.sub(r'<text:note-body><text:p\b[^>]*>(?:<text:span\b[^>]*>)?(?:<text:tab/>)?',
                       lambda m: m.group(0) if m.group(0).endswith('<text:tab/>') else m.group(0) + '<text:tab/>', t)
            if it.filename == 'content.xml' and labels:
                # LibreOffice's own count went wrong: write each number in by hand. The note's own label becomes one word
                # joiner (no width, no break: the lines are set as before; a bidi mark there shifts the note's first line
                # in LibreOffice 7.3); the number goes into the text after the bracket typeset.py puts before the
                # reference, and before the tab at the head of the note, «(n)», in the look of what begins the note.
                n = iter(labels)
                pat = ('(\u200f\\(\u200f)(</text:span><text:note\\b[^>]*text:note-class="footnote"[^>]*>)<text:note-citation>'
                       '(.*?</text:note-citation><text:note-body><text:p\\b[^>]*>(?:<text:span\\b[^>]*>)?)<text:tab/>')
                if len(labels) == len(re.findall(pat, t)) == t.count('text:note-class="footnote"'):
                    t = re.sub(pat, lambda m: (lambda x: f'{m.group(1)}{x}{m.group(2)}<text:note-citation text:label="\u2060">'
                                                         f'{m.group(3)}({x})<text:tab/>')(next(n)), t)
            if it.filename == 'styles.xml':
                t = t.replace('</office:styles>', '<style:style style:name="Note_20_Label" style:display-name="Note Label" style:family="text"/></office:styles>', 1)
            data = t.encode()
        zout.writestr(it, data, compress_type=zipfile.ZIP_STORED if it.filename == 'mimetype' else zipfile.ZIP_DEFLATED)
    zout.close()

def note_refs(pdf):
    """Per page, the number printed at each footnote reference: the reference is a link down to its note, further down
    the page or, when the note did not fit, on the next one (the note's own link back up is not counted)."""
    import pdfplumber
    out = []
    with pdfplumber.open(pdf) as doc:
        at = {p.page_obj.pageid: i for i, p in enumerate(doc.pages)}
        for i, p in enumerate(doc.pages):
            refs = []
            for a in p.annots:
                d = a['data'].get('Dest') or a['data'].get('A')
                if hasattr(d, 'resolve'): d = d.resolve()
                if isinstance(d, dict): d = d.get('D')
                if not isinstance(d, list) or len(d) < 4 or not isinstance(d[3], (int, float)): continue
                j = at.get(getattr(d[0], 'objid', None), -1)
                if j < i or j == i and p.height - d[3] <= a['bottom']: continue
                refs.append(''.join(c['text'] for c in p.chars if a['x0'] - 1 <= (c['x0'] + c['x1']) / 2 <= a['x1'] + 1
                                    and a['top'] - 1 <= (c['top'] + c['bottom']) / 2 <= a['bottom'] + 1 and c['text'].translate(DIG).isdigit()).translate(DIG))
            out.append(refs)
    return out

def to_pdf(docx, pdf):
    d = tempfile.mkdtemp()
    lo(['--convert-to', 'odt', '--outdir', d, docx])
    odt = os.path.join(d, os.path.basename(docx)[:-5] + '.odt')
    shutil.move(odt, odt + '.lo')
    # Footnotes restart at (1) on each page. LibreOffice numbers a footnote by the page where it first lays it out, and
    # keeps that number when the line then moves to the next page because its note no longer fits there: the note shows
    # (2) or (3) on its new page. Every layout pass does it again (no setting or reload helps), so when a page's numbers
    # are not 1, 2, 3… every footnote gets its number written in by hand, counted from where the notes really fell.
    labels = None
    for _ in range(3):
        patch_odt(odt + '.lo', odt, labels)
        lo(['--convert-to', 'pdf', '--outdir', d, odt])
        refs = note_refs(odt[:-4] + '.pdf')
        want = [i + 1 for r in refs for i in range(len(r))]
        if labels is None and all(sorted(r, key=lambda x: int(x or 0)) == [str(i + 1) for i in range(len(r))] for r in refs): break
        if labels == want: break
        labels = want
    shutil.copy(odt[:-4] + '.pdf', pdf); shutil.rmtree(d)

DIG = str.maketrans('\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669\u06F0\u06F1\u06F2\u06F3\u06F4\u06F5\u06F6\u06F7\u06F8\u06F9', '01234567890123456789')
def norm(s):
    # letters + digits (so headings that differ only by number stay distinct); digit runs sorted because RTL extraction may reverse them.
    # The ligature words of U+FD00–U+FDFF (ﷻ ﷺ …) are left out on both sides: some are drawn in the symbols font, which
    # has no bold, so they are missing from a heading's bold text in the PDF (and NFKC would spell them out in letters)
    s = unicodedata.normalize('NFKC', re.sub('[\ufd00-\ufdff]', '', s)).translate(DIG)
    s = re.sub(r'[^\u0621-\u064A0-9]', '', s)
    return re.sub(r'[0-9]+', lambda m: ''.join(sorted(m.group(0))), s)

def headings(md):
    """The entries of the contents: the # and ## headings (the contents do not list themselves, and an article with no
    cover does not list its own title, its first line)."""
    out = []
    lines = open(md, encoding='utf-8').read().split('\n'); text = [l for l in lines if l.strip()]
    title = text[0] if text and text[0].startswith('# ') else None   # no front matter: the first line is the article's title
    for ln in lines:
        if ln == title: title = None; continue
        if ln.startswith('## '): out.append((ln[3:], 2))
        elif ln.startswith('# '): out.append((ln[2:], 1))
    return [(re.sub(r'\*\*|\[\^[^\]]+\]', '', t).strip(), l) for t, l in out]

def heading_rows(pdf):
    """Per page, its lines as [(top, chars)] — without the contents: their level-1 entries are bold like the headings
    themselves. The contents start at their own heading (on the page of an article's title they follow the title) and
    fill whole pages after it; the text after them starts a new page."""
    import pdfplumber
    out = []; inside = False
    with pdfplumber.open(pdf) as doc:
        for p in doc.pages:
            rows = {}
            for c in p.chars: rows.setdefault(round(c['top']), []).append(c)
            rows = sorted(rows.items())
            bold = lambda cs: norm(''.join(c['text'] for c in sorted(cs, key=lambda c: -c['x0']) if 'Bold' in c['fontname']))
            cut = next((k for k, (top, cs) in enumerate(rows) if bold(cs) == norm('فهرس الموضوعات')), None)
            leaders = any(sum(c['text'] == '.' for c in cs) >= 10 for top, cs in rows)
            if cut is not None: rows = rows[:cut]; inside = True
            elif inside and leaders: rows = []
            else: inside = False
            out.append(rows)
    return out

def find_pages(pdf, heads):
    pages = []
    texts = [norm(''.join(c['text'] for top, cs in rows for c in sorted(cs, key=lambda c: -c['x0']) if 'Bold' in c['fontname'])) for rows in heading_rows(pdf)]
    start = 0
    for t, l in heads:
        key = norm(t)[:30]; pg = None
        for i in range(start, len(texts)):
            if key and key in texts[i]: pg = i + 1; start = i; break
        pages.append(pg)
    return pages

def keep_heads(md):
    """The # / ## / ### headings in order — the ones that must stay with the paragraph after them (typeset.py counts
    them the same way for --break-before). A # heading starts a new page anyway when the document has a cover."""
    return [re.sub(r'\*\*|\[\^[^\]]+\]', '', ln.split(' ', 1)[1]).strip() for ln in open(md, encoding='utf-8').read().split('\n') if ln.startswith(('# ', '## ', '### '))]

def lone_heads(pdf, heads):
    """Indexes of the headings left alone at the foot of a page. LibreOffice keeps a heading with the next paragraph,
    except when that paragraph carries a footnote that no longer fits: it then moves the paragraph and leaves the heading.
    The contents are left out (heading_rows): their level-1 entries are bold too, and the last one has nothing under it."""
    out = []
    pages = heading_rows(pdf)
    start = 0
    for n, t in enumerate(heads):
        key = norm(t)[:30]
        for i in range(start, len(pages)):
            at = next((top for top, cs in pages[i] if key and key in norm(''.join(c['text'] for c in sorted(cs, key=lambda c: -c['x0']) if 'Bold' in c['fontname']))), None)
            if at is None: continue
            start = i
            # body lines under the heading: footnotes are set smaller, and the last line of the page is its number
            if not any(top > at + 2 and max(c['size'] for c in cs) >= 13.9 for top, cs in pages[i][:-1]): out.append(n)
            break
    return out

BREAKS = []
def lo_pdf(ts, md, docx, pdf, args):
    """The PDF route: build, then give every heading left alone at the foot of a page a page break before it and rebuild."""
    heads = keep_heads(md)
    for _ in range(6):
        subprocess.run(['python3', ts, md, docx, 'lo'] + args + ([f'--break-before={",".join(map(str, BREAKS))}'] if BREAKS else []), check=True)
        to_pdf(docx, pdf)
        new = [n for n in lone_heads(pdf, heads) if n not in BREAKS]
        if not new: break
        BREAKS.extend(new)

FONTS_ZIP = 'خطوط-لملف-Word.zip'
def fonts_zip(docx):
    """One zip beside the Word file with the fonts it needs: the two Lotus Lotfi files always; the Quran font whenever
    the document has at least one verse set in Uthmani script (typeset.py embeds that font only then); and the symbols
    font, with its licence, whenever a character is set in it."""
    adir = os.path.join(HERE, '..', 'assets')
    files = [(os.path.join(adir, 'fonts', n), n) for n in sorted(os.listdir(os.path.join(adir, 'fonts')))]
    z = zipfile.ZipFile(docx)
    if 'word/fonts/font1.odttf' in z.namelist(): files.append((os.path.join(adir, 'quran', 'UthmanicHafs_V22.ttf'), 'UthmanicHafs_V22.ttf'))
    if any('w:cs="Noto Naskh Arabic"' in z.read(n).decode() for n in ('word/document.xml', 'word/footnotes.xml')):
        files += [(os.path.join(adir, 'symbols', 'NotoNaskhArabic-Regular.ttf'), 'NotoNaskhArabic-Regular.ttf'), (os.path.join(adir, 'symbols', 'OFL.txt'), 'NotoNaskhArabic-OFL.txt')]
    path = os.path.join(os.path.dirname(os.path.abspath(docx)), FONTS_ZIP)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as out:
        for f, name in files: out.write(f, name)
    return path

HINDI = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
# The fonts the PDF may use: Lotus Lotfi, the Quran font, the symbols font, and Times (Liberation Serif where Times is
# not installed) for Latin text and the few signs Lotus lacks; Courier draws the second-level bullet «o».
OWN = ('LotusLotfi', 'KFGQPC', 'NotoNaskhArabic', 'Times', 'LiberationSerif', 'Courier', 'LiberationMono')
ARABIC = re.compile('[\u0600-\u06FF\u0750-\u077F\u0870-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
def font_files():
    """PostScript name -> file of the fonts LibreOffice can use besides the skill's own: fontconfig's list where there is
    one (Linux), otherwise the fonts LibreOffice carries itself (macOS, Windows)."""
    from fontTools.ttLib import TTFont
    import glob
    files = {}
    exe = os.path.realpath(shutil.which(SOFFICE_CMD[-1]) or SOFFICE_CMD[-1])
    for f in glob.glob(os.path.join(os.path.dirname(exe), '..', '**', 'fonts', '**', '*.ttf'), recursive=True):
        try: files[TTFont(f, lazy=True)['name'].getDebugName(6)] = f
        except Exception: pass
    if shutil.which('fc-list'):
        out = subprocess.run(['fc-list', '-f', '%{postscriptname}\t%{file}\n'], capture_output=True, text=True).stdout
        files.update(l.split('\t', 1) for l in out.splitlines() if '\t' in l)
    return files

def stray_fonts(pdf):
    """Characters the PDF engine had to draw in some other font (a fallback such as Unifont or DejaVu), or could not
    draw at all: drawn in one of the skill's fonts, or in Times or Courier, that does not have them (an empty glyph).
    -> {character: [page numbers]}"""
    import pdfplumber
    from fontTools.ttLib import TTFont
    a = os.path.join(HERE, '..', 'assets')
    has = {k: set(TTFont(os.path.join(a, f)).getBestCmap()) for k, f in
           (('LotusLotfi', 'fonts/_LotusLotfi-Regular.ttf'), ('NotoNaskhArabic', 'symbols/NotoNaskhArabic-Regular.ttf'), ('KFGQPC', 'quran/UthmanicHafs_V22.ttf'))}
    files = None; other = {}
    def cmap(font):   # Times / Courier, as installed: None when the file cannot be found (then nothing is reported)
        nonlocal files
        if font not in other:
            files = font_files() if files is None else files
            f = files.get(font); other[font] = set(TTFont(f, fontNumber=0).getBestCmap()) if f and os.path.exists(f) else None
        return other[font]
    out = {}
    with pdfplumber.open(pdf) as d:
        for n, p in enumerate(d.pages, 1):
            for c in p.chars:
                ch, font = c['text'], c['fontname'].split('+')[-1]
                if len(ch) != 1 or ch.isspace() or ch in '\u200e\u200f\u2060\u202a\u202c': continue   # glyphs the PDF names by number belong to the fonts' own ligatures
                own = next((k for k in OWN if k in font), None)
                if own is None: bad = True
                elif own in has: bad = ARABIC.match(ch) and ord(ch) not in has[own]
                else: bad = ARABIC.match(ch) or (cmap(font) is not None and ord(ch) not in cmap(font))
                if bad and n not in out.setdefault(ch, []): out[ch].append(n)
    return {ch: pages for ch, pages in out.items() if pages}

if __name__ == '__main__':
    UTHMANI = ['--uthmani'] if '--uthmani' in sys.argv else []
    md, out = [a for a in sys.argv[1:] if a != '--uthmani'][:2]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    setup()
    w = tempfile.mkdtemp(); ts = os.path.join(HERE, 'typeset.py')
    has_toc = any(l.strip() == '@toc' for l in open(md, encoding='utf-8'))
    toc_path = os.path.join(w, 'toc.json')
    if has_toc:
        heads = headings(md)
        json.dump([[t, '٠٠', l] for t, l in heads], open(toc_path, 'w'), ensure_ascii=False)
        for _ in range(2):  # converge page numbers
            lo_pdf(ts, md, w + '/p.docx', w + '/p.pdf', [toc_path] + UTHMANI)
            pg = find_pages(w + '/p.pdf', heads)
            json.dump([[t, str(p).translate(HINDI) if p else '؟', l] for (t, l), p in zip(heads, pg)], open(toc_path, 'w'), ensure_ascii=False)
        missing = [t for (t, l), p in zip(heads, pg) if not p]
        if missing: print('TOC: page not found for:', missing)
    args = ([toc_path] if has_toc else []) + UTHMANI
    subprocess.run(['python3', ts, md, out + '.docx', 'word'] + args, check=True)
    lo_pdf(ts, md, w + '/f.docx', out + '.pdf', args)
    stray = stray_fonts(out + '.pdf')
    if stray:   # in Arabic: it goes into the reply to the user
        print('FONTS: حروف ليست في خطوط المهارة فرُسمت في PDF بخطٍّ آخر أو لم تُرسم: '
              + '، '.join(f'«{ch}» (ص {"، ".join(str(n) for n in pages)})' for ch, pages in stray.items()).translate(HINDI))
    # the fonts go beside the output in one zip: Word shows the document in them only where they are installed
    print('done:', out + '.docx', out + '.pdf', '| fonts:', fonts_zip(out + '.docx'))

#!/usr/bin/env python3
"""One-shot pipeline: input.md -> OUT.docx (for Word) + OUT.pdf (via LibreOffice), with the contents and the indexes
paged automatically.
usage: python3 make.py input.md OUTPUT_DIR/NAME [options]   (writes NAME.docx, NAME.pdf and the fonts zip)
Every option is on request only — the user chose it:
  --uthmani              verses in Uthmani script
  --font=traditional     the body in Traditional Arabic instead of Lotus Lotfi
  --basmala=N            the opening basmala set as Lotus Lotfi's basmala number N (1-7)
  --cite=STYLE --sources=FILE   citations in chicago | apa | harvard | mla | ieee, from the sources file (see cite.py)
  --profile=kku          a thesis set by the King Khalid University guide (Traditional Arabic, its pages and measures)"""
import os, sys, re, json, shutil, subprocess, tempfile, zipfile, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import indexes
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
    if TRAD:
        shutil.copy(TRAD[1], fd); TRAD[2] and shutil.copy(TRAD[2], fd)
        # Older font files give their weight on the old 1-9 scale (Traditional Arabic Bold says 7, meaning 700), which
        # fontconfig reads as the thinnest weight, so the bold face is never chosen and bold is faked. fontconfig is told
        # the weight its own style name already gives; the font file itself is not touched.
        if sys.platform.startswith('linux'):
            cd = os.path.expanduser('~/.config/fontconfig/conf.d'); os.makedirs(cd, exist_ok=True)
            open(os.path.join(cd, '99-saffaf-weight.conf'), 'w').write(
                '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><match target="scan">'
                f'<test name="family"><string>{TRAD[0]}</string></test><test name="style"><string>Bold</string></test>'
                '<edit name="weight" mode="assign"><const>bold</const></edit></match></fontconfig>')
    if TITLE: shutil.copy(TITLE[1], fd)   # a thesis title in the guide's font
    shutil.copy(os.path.join(HERE, '..', 'assets', 'symbols', 'NotoNaskhArabic-Regular.ttf'), fd)
    if UTHMANI: shutil.copy(os.path.join(HERE, '..', 'assets', 'quran', 'UthmanicHafs_V22.ttf'), fd)
    if shutil.which('fc-cache'): subprocess.run(['fc-cache', '-f'], capture_output=True)
    os.makedirs(PROFILE + '/user', exist_ok=True)
    open(PROFILE + '/user/registrymodifications.xcu', 'w').write(
        '<?xml version="1.0" encoding="UTF-8"?><oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<item oor:path="/org.openoffice.Office.Common/I18N/CTL"><prop oor:name="CTLTextNumerals" oor:op="fuse"><value>3</value></prop></item>'
        '<item oor:path="/org.openoffice.Office.Common/I18N/CTL"><prop oor:name="CTLFont" oor:op="fuse"><value>true</value></prop></item>'
        # bookmarks become named destinations in the PDF: that is how the page of each index entry is read
        '<item oor:path="/org.openoffice.Office.Common/Filter/PDF/Export"><prop oor:name="ExportBookmarksToPDFDestination" oor:op="fuse"><value>true</value></prop></item></oor:items>')

def lo(args, limit=600):
    """Run LibreOffice. A conversion takes seconds; one that runs on past the limit is a LibreOffice loop: it is stopped
    and False returned (after the full ten minutes the build stops with a message rather than wait for ever)."""
    try: subprocess.run(SOFFICE_CMD + [f'-env:UserInstallation=file://{PROFILE}', '--headless'] + args, capture_output=True, timeout=limit)
    except subprocess.TimeoutExpired:
        subprocess.run(['pkill', '-9', '-x', 'soffice.bin'], capture_output=True)
        if limit >= 600: sys.exit('LibreOffice did not finish converting ' + os.path.basename(args[-1]) + ' (stopped after 10 minutes)')
        return False
    return True

def patch_odt(src, dst, labels=None):
    """LibreOffice's ODT of the Word file, with our note settings; labels: each footnote's number, when written in by hand."""
    zin = zipfile.ZipFile(src); zout = zipfile.ZipFile(dst, 'w')
    for it in zin.infolist():
        data = zin.read(it.filename)
        if it.filename == 'settings.xml' and NO_SHRINK:
            # LibreOffice 24.2 imitates Word by shrinking the spaces of a justified line (JustifyLinesWithShrinking, set
            # for Word files). Together with its own letter stretching in Arabic lines it can loop for ever on a note
            # whose first line holds the tab after the note's number (a common source reference was enough). It stays
            # on (lines set with it need less stretching), and is turned off only for a document whose conversion stalls.
            data = data.decode().replace('config:name="JustifyLinesWithShrinking" config:type="boolean">true',
                                         'config:name="JustifyLinesWithShrinking" config:type="boolean">false').encode()
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
            # The Word file writes the note's number between brackets of its own, «(» number «)»; LibreOffice reads them
            # as text at the head of the note (and drops the number), and draws its own «(1)» from the settings above:
            # those brackets go, here in the intermediate file only.
            t = re.sub(r'(<text:note-body><text:p\b[^>]*>(?:<text:span\b[^>]*>)?)\u200f?\(\u200f?\u200f?\)\u200f?', r'\1', t)
            t = re.sub(r'<text:note-body><text:p\b[^>]*>(?:<text:span\b[^>]*>)?(?:<text:tab/>)?',
                       lambda m: m.group(0) if m.group(0).endswith('<text:tab/>') else m.group(0) + '<text:tab/>', t)
            if it.filename == 'content.xml':
                # LibreOffice draws a note's own number in the look of the note's paragraph. A note that is one run of
                # Latin text gets that look from it; one with an italic title (a citation style) is several runs and
                # its number would fall back to the Arabic note style, «(١)». So a left-to-right note paragraph takes
                # the look of its first run (not its italic or bold).
                for ps, ts in set(re.findall(r'<text:note-body><text:p text:style-name="([^"]+)"><text:span text:style-name="([^"]+)">', t)):
                    pm = re.search(r'<style:style style:name="' + re.escape(ps) + r'" style:family="paragraph"[^>]*>(.*?)</style:style>', t)
                    tm = re.search(r'<style:style style:name="' + re.escape(ts) + r'" style:family="text"[^>]*><style:text-properties([^>]*)/>', t)
                    if not pm or not tm or 'style:writing-mode="lr-tb"' not in pm.group(1) or '<style:text-properties' in pm.group(1): continue
                    props = re.sub(r'\s(fo:font-style|style:font-style-asian|style:font-style-complex|fo:font-weight|style:font-weight-asian|style:font-weight-complex)="[^"]*"', '', tm.group(1))
                    t = t[:pm.end(1)] + f'<style:text-properties{props}/>' + t[pm.end(1):]
            if it.filename == 'content.xml':
                # LibreOffice gives a page reference the page's number, not its letter: the prelims of a thesis are numbered
                # in letters, so their references keep the letter the file stores (read from the PDF of the pass before)
                # (LibreOffice's letters write the fifth as a bare «ه», Word's as «هـ»: each program's contents match its own footer)
                t = re.sub(r'<text:bookmark-ref\b[^>]*text:ref-name="_pre\d+"[^>]*>(.*?)</text:bookmark-ref>', lambda m: m.group(1).replace('هـ', 'ه'), t)
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
                # a reference is a small raised number; the contents and the indexes link their full-size page numbers
                # to their headings and entries too (LibreOffice makes a link of every page reference)
                digits = [c for c in p.chars if a['x0'] - 1 <= (c['x0'] + c['x1']) / 2 <= a['x1'] + 1
                          and a['top'] - 1 <= (c['top'] + c['bottom']) / 2 <= a['bottom'] + 1 and c['text'].translate(DIG).isdigit()]
                if digits and all(c['size'] >= 12.5 for c in digits): continue
                refs.append(''.join(c['text'] for c in digits if c['size'] < 12.5).translate(DIG))
            out.append(refs)
    return out

def word14(docx, d):
    """A copy of the Word file marked Word 2010 (compatibility mode 14): LibreOffice then reads it without its
    Word-imitating space shrinking. Only the mode differs; the content is the same."""
    out = os.path.join(d, os.path.basename(docx))
    zin = zipfile.ZipFile(docx); z = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)
    for it in zin.infolist():
        data = zin.read(it.filename)
        if it.filename == 'word/settings.xml':
            data = data.decode().replace('w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"',
                                         'w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="14"').encode()
        z.writestr(it, data)
    z.close(); return out

def to_pdf(docx, pdf):
    """Export the PDF from the Word file, through LibreOffice's ODT (patched for the notes, see patch_odt)."""
    global NO_SHRINK
    d = tempfile.mkdtemp()
    # LibreOffice lays the document out while reading it, and can loop there (see patch_odt): a stall switches the rest
    # of the build to a copy it reads without space shrinking
    if NO_SHRINK or not lo(['--convert-to', 'odt', '--outdir', d, docx], limit=60):
        NO_SHRINK = True
        lo(['--convert-to', 'odt', '--outdir', d, word14(docx, tempfile.mkdtemp())])
    odt = os.path.join(d, os.path.basename(docx)[:-5] + '.odt')
    shutil.move(odt, odt + '.lo')
    # Footnotes restart at (1) on each page. LibreOffice numbers a footnote by the page where it first lays it out, and
    # keeps that number when the line then moves to the next page because its note no longer fits there: the note shows
    # (2) or (3) on its new page. Every layout pass does it again (no setting or reload helps), so when a page's numbers
    # are not 1, 2, 3… every footnote gets its number written in by hand, counted from where the notes really fell.
    labels = None
    for _ in range(3):
        patch_odt(odt + '.lo', odt, labels)
        if not lo(['--convert-to', 'pdf', '--outdir', d, odt], limit=600 if NO_SHRINK else 60):
            NO_SHRINK = True   # it stalled: once more without space shrinking, for the rest of this build
            patch_odt(odt + '.lo', odt, labels); lo(['--convert-to', 'pdf', '--outdir', d, odt])
        refs = note_refs(odt[:-4] + '.pdf')
        want = [i + 1 for r in refs for i in range(len(r))]
        if labels is None and all(sorted(r, key=lambda x: int(x or 0)) == [str(i + 1) for i in range(len(r))] for r in refs): break
        if labels == want: break
        labels = want
    shutil.copy(odt[:-4] + '.pdf', pdf); shutil.rmtree(d)

def dest_pages(pdf):
    """The page of every bookmark the skill set (index entries «_ix…», footnote references «_fn…»), from the PDF's
    named destinations."""
    import pdfplumber
    from pdfminer.pdftypes import resolve1
    out = {}
    with pdfplumber.open(pdf) as doc:
        at = {p.page_obj.pageid: i + 1 for i, p in enumerate(doc.pages)}
        cat = doc.doc.catalog
        dests = resolve1(cat['Dests']) if 'Dests' in cat else {}
        if not dests and 'Names' in cat:   # a name tree
            def walk(node):
                node = resolve1(node)
                for i in range(0, len(resolve1(node.get('Names', []))), 2):
                    n = resolve1(node['Names']); dests[n[i].decode() if isinstance(n[i], bytes) else n[i]] = n[i + 1]
                for k in resolve1(node.get('Kids', [])): walk(k)
            dests = {}; walk(resolve1(cat['Names']).get('Dests', {}))
        for name, d in dests.items():
            name = name.decode() if isinstance(name, bytes) else str(name)
            name = re.sub(r'^5F', '_', name)   # LibreOffice writes the «_» of a bookmark's name as its hex code
            if not re.match(r'^_(ix|fn|toc|pre|sec|cap)\d+$', name): continue
            d = resolve1(d); d = resolve1(d['D']) if isinstance(d, dict) else d
            pg = at.get(getattr(d[0], 'objid', None)) if isinstance(d, list) and d else None
            if pg: out[name] = pg
    return out

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
    lines = open(md, encoding='utf-8').read().split('\n')
    text = [l for l in lines if l.strip() and not l.startswith('@header')]
    if text and indexes.is_basmala(text[0]): text = text[1:]   # an opening basmala stands above the title
    title = text[0] if text and text[0].startswith('# ') else None   # no front matter: the first line is the article's title
    for ln in lines:
        if ln == title: title = None; continue
        if ln.startswith('## '): out.append((ln[3:], 2))
        elif ln.startswith('# '): out.append((ln[2:], 1))
        elif indexes.directive(ln): out.append((indexes.KINDS[indexes.directive(ln)], 1))
    return [(re.sub(r'\*\*|\[\^[^\]]+\]', '', indexes.strip_marks(t)).strip(), l) for t, l in out]

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
            cut = next((k for k, (top, cs) in enumerate(rows) if bold(cs) in (norm('فهرس الموضوعات'), norm('قائمة المحتويات'))), None)
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
    return [indexes.KINDS[indexes.directive(ln)] if indexes.directive(ln) else re.sub(r'\*\*|\[\^[^\]]+\]', '', indexes.strip_marks(ln.split(' ', 1)[1])).strip()
            for ln in open(md, encoding='utf-8').read().split('\n') if ln.startswith(('# ', '## ', '### ')) or indexes.directive(ln)]

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
NO_SHRINK = False   # set when LibreOffice stalled on this document (see patch_odt)
def lo_pdf(ts, md, docx, pdf, args):
    """Build the Word file, then export the PDF from that same file. A heading the PDF engine left alone at the foot of
    a page gets a page break before it, in the Word file, which is then built and exported again. -> typeset's report."""
    heads = keep_heads(md)
    for _ in range(6):
        r = subprocess.run(['python3', ts, md, docx, 'word'] + args + ([f'--break-before={",".join(map(str, BREAKS))}'] if BREAKS else []), capture_output=True, text=True)
        if r.returncode: sys.exit(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'typeset.py failed')
        to_pdf(docx, pdf)
        new = [n for n in lone_heads(pdf, heads) if n not in BREAKS]
        if not new: break
        BREAKS.extend(new)
    return r.stdout

FONTS_ZIP = 'خطوط-لملف-Word.zip'
def fonts_zip(docx):
    """One zip beside the Word file with the fonts it needs: the two Lotus Lotfi files always; the Quran font whenever
    the document has at least one verse set in Uthmani script (typeset.py embeds that font only then); and the symbols
    font, with its licence, whenever a character is set in it. With Traditional Arabic (on request) its files replace the
    Lotus ones, which come along only when the opening basmala was set in Lotus Lotfi."""
    adir = os.path.join(HERE, '..', 'assets')
    z = zipfile.ZipFile(docx)
    lotus = [(os.path.join(adir, 'fonts', n), n) for n in sorted(os.listdir(os.path.join(adir, 'fonts')))]
    if TRAD:
        files = [(f, os.path.basename(f)) for f in TRAD[1:] if f]
        if 'w:cs="_Lotus Lotfi"' in z.read('word/document.xml').decode(): files += lotus
    else: files = lotus
    if TITLE and f'w:cs="{TITLE[0]}"' in z.read('word/document.xml').decode(): files.append((TITLE[1], os.path.basename(TITLE[1])))
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
OWN = ['LotusLotfi', 'KFGQPC', 'NotoNaskhArabic', 'Times', 'LiberationSerif', 'Courier', 'LiberationMono']
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
    if TRAD:   # the body font asked for: its own files (bold too) decide what it has
        for f in TRAD[1:]:
            if f: k = TTFont(f, lazy=True)['name'].getDebugName(6); OWN.insert(0, k); has[k] = set(TTFont(f).getBestCmap())
    if TITLE: k = TTFont(TITLE[1], lazy=True)['name'].getDebugName(6); OWN.insert(0, k); has[k] = set(TTFont(TITLE[1]).getBestCmap())
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

TRAD = None
TITLE = None   # the thesis-title font (PT Bold Heading), in the thesis profile when its file is there
if __name__ == '__main__':
    flags = [a for a in sys.argv[1:] if a.startswith('--')]
    UTHMANI = ['--uthmani'] if '--uthmani' in flags else []
    md, out = [a for a in sys.argv[1:] if not a.startswith('--')][:2]
    opt = lambda name: next((a.split('=', 1)[1] for a in flags if a.startswith(f'--{name}=')), None)
    if opt('sources'): flags = [f'--sources={os.path.abspath(opt("sources"))}' if a.startswith('--sources=') else a for a in flags]
    if opt('profile') == 'kku' and not opt('font'): flags.append('--font=traditional')   # the guide's font
    if opt('font') == 'traditional' or opt('profile') == 'kku':
        from fonts import traditional_files
        TRAD = traditional_files()
        if not TRAD: sys.exit('Traditional Arabic was asked for, but its font files are not in assets/traditional')
    if opt('profile') == 'kku':
        from fonts import title_font
        TITLE = title_font()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    setup()
    w = tempfile.mkdtemp(); ts = os.path.join(HERE, 'typeset.py')
    src = open(md, encoding='utf-8').read().split('\n')
    has_toc = any(l.strip() == '@toc' for l in src)
    has_index = any(indexes.directive(l) for l in src)
    pages_path = os.path.join(w, 'pages.json')
    paged = has_toc or has_index   # the contents and the indexes take their stored page numbers from the PDF
    def args(): return flags + ([f'--pages={pages_path}'] if paged else [])
    def measure(pdf):
        """Read where the headings and the index entries fell in the PDF; True when the file already says so."""
        old = open(pages_path).read()
        json.dump(dest_pages(pdf), open(pages_path, 'w'), sort_keys=True)
        return old == open(pages_path).read()
    if paged:
        json.dump({}, open(pages_path, 'w'))
        for _ in range(2):  # converge page numbers
            lo_pdf(ts, md, w + '/p.docx', w + '/p.pdf', args())
            measure(w + '/p.pdf')
    for _ in range(2):   # the final build: the Word file delivered is the very file the PDF is exported from
        report = lo_pdf(ts, md, out + '.docx', out + '.pdf', args())
        if not paged or measure(out + '.pdf'): break
    print(report, end='')
    stray = stray_fonts(out + '.pdf')
    if stray:   # in Arabic: it goes into the reply to the user
        print('FONTS: حروف ليست في خطوط المهارة فرُسمت في PDF بخطٍّ آخر أو لم تُرسم: '
              + '، '.join(f'«{ch}» (ص {"، ".join(str(n) for n in pages)})' for ch, pages in stray.items()).translate(HINDI))
    # the fonts go beside the output in one zip: Word shows the document in them only where they are installed
    print('done:', out + '.docx', out + '.pdf', '| fonts:', fonts_zip(out + '.docx'))

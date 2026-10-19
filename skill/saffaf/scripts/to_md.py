#!/usr/bin/env python3
"""Convert any text document into a draft in.md for make.py — the text itself is never edited.
usage: python3 to_md.py INPUT OUTPUT.md
  .txt .md .markdown .text      -> copied as-is (BOM / line endings normalised)
  .docx .docm .dotx .dotm       -> parsed directly: headings, bold, lists, tables, footnotes, endnotes
  .doc .odt .ott .rtf .html .htm .xhtml .wpd .fodt  -> LibreOffice -> .docx -> as above
  .epub                         -> chapters in reading order -> LibreOffice -> .docx -> as above
  .pdf                          -> refused: text extracted from PDF is damaged; ask for the original
Every result is checked for PDF-copy damage (reversed lam-alef); the report says DAMAGED when found.
Prints a short report (format, footnotes found, warnings) to stdout.
Word files that draw signs with a symbol font (AGA Arabesque and the like: the file stores «a» and the font draws ﷺ)
are reported on a SYMBOLS line. Only with --symbols (the user asked for it) are the signs whose meaning is known
written as their standard character; the others stay as they are and are named on the line."""
import os, re, sys, shutil, subprocess, tempfile, zipfile, posixpath
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
MC_FALLBACK = '{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback'
BIDI_CTRL = dict.fromkeys(map(ord, '‪‫‬‭‮⁦⁧⁨⁩﻿'))
SOFFICE = '/mnt/skills/public/docx/scripts/office/soffice.py'
SOFFICE_CMD = ['python3', SOFFICE] if os.path.exists(SOFFICE) else [shutil.which('soffice') or shutil.which('libreoffice') or 'soffice']
warnings = []
# Symbol fonts: font name -> {character stored in the file: the standard character the font draws for it}. Only
# mappings that were checked go here; a character with no entry is left as it is and reported.
SYMBOL_FONTS = {
    'aga arabesque': {'a': '\ufdfa'},           # «a» -> ﷺ (seen in a real file: «وقال النبي a»)
    'aga arabesque desktop': {'a': '\ufdfa'},
}
SYMBOLS_FOUND = {}    # font -> {character: count}
CONVERT_SYMBOLS = False
def symbol_font(name):
    return (name or '').strip().lower() if (name or '').strip().lower() in SYMBOL_FONTS else None

# ---------------- LibreOffice bridge ----------------
def to_docx(path):
    d = tempfile.mkdtemp()
    subprocess.run(SOFFICE_CMD + ['-env:UserInstallation=file:///tmp/ar_typeset_conv', '--headless',
                    '--convert-to', 'docx:MS Word 2007 XML', '--outdir', d, path], capture_output=True)
    out = os.path.join(d, os.path.splitext(os.path.basename(path))[0] + '.docx')
    if not os.path.exists(out):
        sys.exit(f'LibreOffice could not convert {path}')
    return out

# ---------------- DOCX ----------------
def wval(el, tag, attr='val'):
    x = el.find(W + tag) if el is not None else None
    return None if x is None else x.get(W + attr, 'true')

def is_on(v): return v is not None and v not in ('0', 'false', 'off', 'none')

def is_bold(rpr, explicit=False):
    # Arabic bold is often stored only as complex-script bold (bCs)
    vals = [wval(rpr, 'b'), wval(rpr, 'bCs')]
    set_ = [v for v in vals if v is not None]
    if not set_: return None if explicit else False
    return any(is_on(v) for v in set_)

class Docx:
    def __init__(self, path):
        z = zipfile.ZipFile(path)
        names = set(z.namelist())
        rd = lambda n: ET.fromstring(z.read(n)) if n in names else None
        self.doc = rd('word/document.xml')
        self.styles = {}       # styleId -> (name, outline level, bold, numPr)
        st = rd('word/styles.xml')
        if st is not None:
            for s in st.findall(W + 'style'):
                sid = s.get(W + 'styleId'); name = (wval(s, 'name') or sid or '').lower()
                ppr = s.find(W + 'pPr'); rpr = s.find(W + 'rPr')
                lvl = wval(ppr, 'outlineLvl')
                based = wval(s, 'basedOn')
                num = None
                if ppr is not None and ppr.find(W + 'numPr') is not None:
                    np_ = ppr.find(W + 'numPr'); num = (wval(np_, 'numId'), wval(np_, 'ilvl') or '0')
                self.styles[sid] = dict(name=name, lvl=lvl, bold=is_bold(rpr), num=num, based=based)
        self.numfmt = {}       # (numId, ilvl) -> (fmt, lvlText, start)
        nb = rd('word/numbering.xml')
        if nb is not None:
            absmap = {}
            for a in nb.findall(W + 'abstractNum'):
                absmap[a.get(W + 'abstractNumId')] = {l.get(W + 'ilvl'): (wval(l, 'numFmt'), wval(l, 'lvlText'), int(wval(l, 'start') or 1)) for l in a.findall(W + 'lvl')}
            for n in nb.findall(W + 'num'):
                for il, v in absmap.get(wval(n, 'abstractNumId'), {}).items():
                    self.numfmt[(n.get(W + 'numId'), il)] = v
        self.counters = {}
        self.used = []
        self.notes = {}        # ('f'|'e', id) -> text
        for kind, part in (('f', 'word/footnotes.xml'), ('e', 'word/endnotes.xml')):
            root = rd(part)
            if root is None: continue
            for n in root:
                if n.get(W + 'type') in ('separator', 'continuationSeparator', 'continuationNotice'): continue
                paras = [self.inline(p) for p in n.iter(W + 'p')]
                self.notes[(kind, n.get(W + 'id'))] = ' '.join(t.strip() for t in paras if t.strip())

    def style(self, sid, key):
        seen = set()
        while sid and sid not in seen:
            seen.add(sid); s = self.styles.get(sid)
            if not s: return None
            if s.get(key) not in (None, False): return s[key]
            sid = s.get('based')
        return None

    def inline(self, p):
        """Paragraph text with **bold** and [^label] note refs; deleted text skipped."""
        out = []; pstyle = wval(p.find(W + 'pPr'), 'pStyle')
        pbold = bool(self.style(pstyle, 'bold'))
        def walk(el):
            for c in el:
                if c.tag in (W + 'del', W + 'pPr', W + 'rPr', MC_FALLBACK, W + 'instrText'): continue
                if c.tag == W + 'r':
                    rpr = c.find(W + 'rPr')
                    explicit = is_bold(rpr, explicit=True)
                    bold = explicit if explicit is not None else (pbold or bool(self.style(wval(rpr, 'rStyle'), 'bold')))
                    rf = rpr.find(W + 'rFonts') if rpr is not None else None
                    sf = symbol_font(rf.get(W + 'ascii') or rf.get(W + 'hAnsi') or rf.get(W + 'cs')) if rf is not None else None
                    for x in c:
                        if x.tag == W + 't' and sf:
                            txt = ''
                            for ch in x.text or '':
                                if ch.isspace(): txt += ch; continue
                                SYMBOLS_FOUND.setdefault(sf, {}).setdefault(ch, 0); SYMBOLS_FOUND[sf][ch] += 1
                                txt += SYMBOL_FONTS[sf].get(ch, ch) if CONVERT_SYMBOLS else ch
                            out.append((txt, bold))
                        elif x.tag == W + 't': out.append((x.text or '', bold))
                        elif x.tag == W + 'tab': out.append(('\t', False))
                        elif x.tag in (W + 'br', W + 'cr'): out.append((' ', False))
                        elif x.tag == W + 'noBreakHyphen': out.append(('-', bold))
                        elif x.tag == W + 'footnoteReference':
                            lab = 'f' + x.get(W + 'id'); self.used.append(('f', x.get(W + 'id'), lab)); out.append((f'[^{lab}]', False))
                        elif x.tag == W + 'endnoteReference':
                            lab = 'e' + x.get(W + 'id'); self.used.append(('e', x.get(W + 'id'), lab)); out.append((f'[^{lab}]', False))
                        elif x.tag == W + 'sym':
                            ch = chr(int(x.get(W + 'char'), 16)) if x.get(W + 'char') else ''
                            sf = symbol_font(x.get(W + 'font'))
                            if sf and ch:   # Word stores a symbol as F000 + its code in the font
                                c0 = chr(ord(ch) - 0xF000) if 0xF000 <= ord(ch) <= 0xF0FF else ch
                                SYMBOLS_FOUND.setdefault(sf, {}).setdefault(c0, 0); SYMBOLS_FOUND[sf][c0] += 1
                                ch = SYMBOL_FONTS[sf].get(c0, ch) if CONVERT_SYMBOLS else ch
                            out.append((ch, bold))
                        elif x.tag not in (W + 'rPr', W + 'footnoteRef', W + 'endnoteRef'):
                            walk(x)   # drawings / text boxes inside runs
                elif c.tag == W + 'txbxContent':
                    for p2 in c.iter(W + 'p'): out.append((' ' + self.inline(p2) + ' ', False))
                else:
                    walk(c)
        walk(p)
        # merge into markdown; bold only around visible text, never around spaces
        s = ''; cur = False; buf = ''
        def flush():
            nonlocal s, buf
            if not buf: return
            if cur and buf.strip():
                lead = buf[:len(buf) - len(buf.lstrip())]; trail = buf[len(buf.rstrip()):]
                s += lead + '**' + buf.strip() + '**' + trail
            else: s += buf
            buf = ''
        for txt, b in out:
            if b != cur and txt.strip(): flush(); cur = b
            buf += txt
        flush()
        s = s.replace('****', '')
        s = re.sub(r'(?<=\S) {2,}(?=\S)', ' ', s)   # stray double spaces from conversion
        return s.translate(BIDI_CTRL)

    def numbering(self, p, sid):
        ppr = p.find(W + 'pPr'); np_ = ppr.find(W + 'numPr') if ppr is not None else None
        if np_ is not None: num = (wval(np_, 'numId'), wval(np_, 'ilvl') or '0')
        else: num = self.style(sid, 'num')
        if not num or num[0] in (None, '0'): return None
        fmt, text, start = self.numfmt.get(num, ('bullet', '•', 1))
        ilvl = int(num[1])
        if fmt in ('bullet', 'none', None): return ('bullet', ilvl, None)
        key = num[0]
        c = self.counters.setdefault(key, {})
        c[ilvl] = c.get(ilvl, start - 1) + 1
        for deeper in [k for k in c if k > ilvl]: del c[deeper]
        label = re.sub(r'%(\d)', lambda m: str(c.get(int(m.group(1)) - 1, 1)), text or '%1.')
        return ('number', ilvl, label)

    def convert(self):
        lines = []; toc_done = False
        body = self.doc.find(W + 'body')
        for el in body:
            if el.tag == W + 'tbl':
                rows = []
                for tr in el.findall(W + 'tr'):
                    cells = [' '.join(self.inline(p).strip() for p in tc.iter(W + 'p')).strip() for tc in tr.findall(W + 'tc')]
                    rows.append(cells)
                if rows:
                    if any('|' in c for r in rows for c in r): warnings.append('a table cell contains "|" — check that table by hand')
                    lines.append('')
                    for i, r in enumerate(rows):
                        lines.append('| ' + ' | '.join(r) + ' |')
                        if i == 0: lines.append('|' + '---|' * len(r))
                    lines.append('')
                continue
            if el.tag != W + 'p': continue
            ppr = el.find(W + 'pPr'); sid = wval(ppr, 'pStyle')
            name = (self.styles.get(sid, {}).get('name') or '')
            if name.startswith('toc') or name == 'table of contents':   # existing TOC -> regenerate
                if not toc_done: lines.append('@toc'); toc_done = True
                continue
            text = self.inline(el).strip()
            if not text: continue
            lvl = wval(ppr, 'outlineLvl') or self.style(sid, 'lvl')
            if name == 'title': lines.append('# ' + text.replace('**', '')); continue
            m = re.match(r'heading (\d)', name)
            hl = int(m.group(1)) if m else (int(lvl) + 1 if lvl is not None and lvl.isdigit() and int(lvl) < 9 else None)
            if hl:
                lines.append(('#' * min(hl, 3)) + ' ' + text.replace('**', '')); continue
            n = self.numbering(el, sid)
            if n and n[0] == 'bullet':
                lines.append(('-- ' if n[1] else '- ') + text); continue
            if n and n[0] == 'number':
                lab = n[2].strip()
                mm = re.match(r'^(\S*?\d+)\s*([-–.)])$', lab)
                lines.append((f'{mm.group(1)}{mm.group(2)} ' if mm else lab + ' ') + text); continue
            lines.append(text)
        # note definitions, in reference order
        lines.append('')
        seen = set()
        for kind, nid, lab in self.used:
            if lab in seen: continue
            seen.add(lab)
            lines.append(f'[^{lab}]: ' + self.notes.get((kind, nid), ''))
            if (kind, nid) not in self.notes: warnings.append(f'note {lab} is referenced but has no text')
        orphan = [k for k in self.notes if (k[0], k[1], k[0] + k[1]) not in self.used]
        if orphan: warnings.append(f'{len(orphan)} note(s) exist but are never referenced in the text')
        return '\n'.join(lines).strip() + '\n', len(seen)

# ---------------- EPUB ----------------
def epub_to_html(path):
    z = zipfile.ZipFile(path)
    cont = ET.fromstring(z.read('META-INF/container.xml'))
    opf = next(e.get('full-path') for e in cont.iter() if e.tag.endswith('rootfile'))
    o = ET.fromstring(z.read(opf)); base = posixpath.dirname(opf)
    items = {e.get('id'): e.get('href') for e in o.iter() if e.tag.endswith('}item')}
    spine = [e.get('idref') for e in o.iter() if e.tag.endswith('}itemref')]
    bodies = []
    for idref in spine:
        href = items.get(idref)
        if not href: continue
        html = z.read(posixpath.normpath(posixpath.join(base, href))).decode('utf-8', 'replace')
        m = re.search(r'<body[^>]*>(.*)</body>', html, re.S | re.I)
        bodies.append(m.group(1) if m else html)
    out = tempfile.mktemp(suffix='.html')
    open(out, 'w', encoding='utf-8').write('<html dir="rtl"><head><meta charset="utf-8"></head><body>' + '\n'.join(bodies) + '</body></html>')
    warnings.append('EPUB: footnotes stay where the book put them (often as links/asides) — turn them into [^n] by hand')
    return out

# ---------------- damage check ----------------
# Text copied out of a PDF reverses lam-alef: «الإنسان» -> «اإلنسان», «الأول» -> «األول», «الاصطلاح» -> «االصطالح».
# No Arabic word starts like that, so two or more hits mean the text came from a PDF and is damaged.
PDF_DAMAGE = re.compile(r'(?<![\u0621-\u064A])[وفبكل]?(?:اإل|األ|اآل|اال)[\u0621-\u064A]')
def damage_check(md):
    hits = PDF_DAMAGE.findall(md)
    if len(hits) >= 2:
        print('DAMAGED: this text looks copied from a PDF (' + '، '.join(dict.fromkeys(hits[:5])) + ' …). '
              'Do not typeset it — ask the user for the Word/text original.')
        return True
    return False

# ---------------- main ----------------
if __name__ == '__main__':
    CONVERT_SYMBOLS = '--symbols' in sys.argv
    src, dst = [a for a in sys.argv[1:] if not a.startswith('--')][:2]
    ext = os.path.splitext(src)[1].lower(); notes = 0
    if ext in ('.txt', '.md', '.markdown', '.text', ''):
        raw = open(src, 'rb').read()
        for enc in ('utf-8-sig', 'utf-16', 'cp1256'):
            try: md = raw.decode(enc); break
            except UnicodeDecodeError: continue
        md = md.replace('\r\n', '\n').replace('\r', '\n').translate(BIDI_CTRL)
        if enc == 'cp1256': warnings.append('file was Windows-1256 encoded; converted to UTF-8')
    elif ext == '.pdf':
        sys.exit('PDF is not accepted: ask the user for the Word or text original of the document.')
    else:
        if ext == '.epub': src = to_docx(epub_to_html(src))
        elif ext not in ('.docx', '.docm', '.dotx', '.dotm'): src = to_docx(src)
        md, notes = Docx(src).convert()
    open(dst, 'w', encoding='utf-8').write(md)
    print(f'format: {ext or "plain"} | notes: {notes} | lines: {md.count(chr(10))} -> {dst}')
    for w in warnings: print('WARNING:', w)
    for font, chars in SYMBOLS_FOUND.items():
        known = {c: SYMBOL_FONTS[font][c] for c in chars if c in SYMBOL_FONTS[font]}
        print(f'SYMBOLS: {font}: ' + ', '.join(f'«{c}»×{n}' + (f' = {known[c]}' if c in known else ' (meaning unknown, left as is)') for c, n in chars.items())
              + (' — converted' if CONVERT_SYMBOLS else ' — left as written; with --symbols the known ones become their standard character'))
    damage_check(md)

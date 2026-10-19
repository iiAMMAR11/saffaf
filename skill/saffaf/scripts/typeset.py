import re, os, zipfile, uuid, unicodedata
import quran, indexes, cite
from fonts import traditional_files, title_font
from xml.sax.saxutils import escape

LOTUS = "_Lotus Lotfi"
FONT = LOTUS
import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__))
REG = _os.path.join(HERE,"..","assets","fonts","_LotusLotfi-Regular.ttf")
BOLD = _os.path.join(HERE,"..","assets","fonts","_LotusLotfi-Bold.ttf")

RLM = "\u200f"
TEXTW = 9072  # A4 width 11906 - 2*1417

W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"')
MARGIN_RIGHT = 1417   # the thesis profile: 3.5 cm on the right (the binding side of an Arabic thesis)

# ---------- inline markup ----------
# **bold**   ⟦small⟧ (verse refs, death dates)   ⟪verse in Uthmani script⟫   ^N footnote   `latin`
# ⟨italic⟩ (titles of Latin works in a citation style)   ⟮N⟯ a bookmark where an index entry stands (invisible)
from fontTools.ttLib import TTFont
CMAP = set(TTFont(REG).getBestCmap())
FALLBACK = "Times New Roman"
# Honorific signs and ligature words (U+FD00–U+FDFF: ﷻ ﷽ ﵁ …) that Lotus does not have at their standard code points
# are set in Noto Naskh Arabic (assets/symbols, SIL OFL), each character as the author wrote it.
SYMBOL_FONT = "Noto Naskh Arabic"
SYMBOL_FILE = _os.path.join(HERE,"..","assets","symbols","NotoNaskhArabic-Regular.ttf")
SYMBOL_CMAP = {c for c in TTFont(SYMBOL_FILE).getBestCmap() if 0xFD00 <= c <= 0xFDFF}
SYMBOLS = SYMBOL_CMAP - CMAP
def use_font(kind):
    """Set the body font: 'lotus' (the default) or 'traditional' (on request)."""
    global FONT, REG, BOLD, CMAP, SYMBOLS
    if kind != 'traditional': return
    t = traditional_files()
    if not t: raise SystemExit('Traditional Arabic was asked for, but its font files are not in assets/traditional')
    FONT, REG, BOLD = t[0], t[1], t[2] or t[1]
    CMAP = set(TTFont(REG).getBestCmap()); SYMBOLS = SYMBOL_CMAP - CMAP
INVISIBLE = '\t\u200f\u200e\u200d\u200c\u2060\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069'
def seg(part):
    # split into (text, font) segments: None = Lotus, SYMBOL_FONT, or FALLBACK for any other glyph Lotus lacks;
    # zero-width/format characters and spaces stay with the text around them in Lotus
    out=[]; cur=''; curf=0
    for ch in part:
        o = ord(ch)
        f = SYMBOL_FONT if o in SYMBOLS else FALLBACK if (o not in CMAP and ch not in INVISIBLE and not ch.isspace()) else None
        if curf == 0 or f == curf: cur+=ch; curf=f
        else: out.append((cur,curf)); cur=ch; curf=f
    if cur: out.append((cur,curf))
    return out
# «**» marks bold only as a pair of asterisks on its own: a run of three or more (the «***» an author puts between the
# two halves of a verse of poetry) is the author's text and stays as it is
TOK = re.compile(r'((?<!\*)\*\*(?!\*)|⟦|⟧|⟪|⟫|⟬|⟭|⟨|⟩|⟮\d+⟯|\^\d+|`[^`]*`)')
def bookmark(name, n):   # an empty, hidden bookmark (Word hides names that begin with «_»); the PDF names its place
    return f'<w:bookmarkStart w:id="{n}" w:name="{name}"/><w:bookmarkEnd w:id="{n}"/>'
footnotes = {}
LTR_NOTES = set()   # footnotes written mostly in Latin letters: set left-to-right in Times
RAGGED_NOTES = set()   # footnotes holding a word that cannot break (a link…): not justified, or the line before it is stretched
UNBREAKABLE = re.compile(r'\S*://\S+|\bwww\.\S+|\S{30,}')

def runs(text, base_bold=False, size=None, ltr_para=False):
    out = []; bold = base_bold; small = False; verse = False; noproof = False; italic = False
    for part in TOK.split(text):
        if not part: continue
        if part == '**': bold = not bold; continue
        if part == '⟨': italic = True; continue
        if part == '⟩': italic = False; continue
        if part.startswith('⟮'): out.append(bookmark(f'_ix{part[1:-1]}', 1000 + int(part[1:-1]))); continue
        if part == '⟦': small = True; continue
        if part == '⟧': small = False; continue
        if part == '⟪': verse = True; continue
        if part == '⟫': verse = False; continue
        if part == '⟬': noproof = True; continue
        if part == '⟭': noproof = False; continue
        if verse:   # Quran text: its own font, never bold, never split into fallback runs, no spelling marks under it
            sz = 21 if small else size
            rp = f'<w:rFonts w:ascii="{quran.FONT}" w:hAnsi="{quran.FONT}" w:cs="{quran.FONT}"/><w:noProof/>' + (f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>' if sz else '') + '<w:rtl/>'
            out.append(f'<w:r><w:rPr>{rp}</w:rPr><w:t xml:space="preserve">{escape(part)}</w:t></w:r>')
            continue
        if part.startswith('^'):
            n = int(part[1:])
            sup = '<w:rStyle w:val="FootnoteReference"/><w:rtl/>'
            out.append(bookmark(f'_fn{n}', 500000 + n))   # the page of the note: index entries inside the note take it
            out.append(f'<w:r><w:rPr>{sup}</w:rPr><w:t>\u200f(\u200f</w:t></w:r>')
            out.append(f'<w:r><w:rPr>{sup}</w:rPr><w:footnoteReference w:id="{n}"/></w:r>')
            out.append(f'<w:r><w:rPr>{sup}</w:rPr><w:t>\u200f)\u200f</w:t></w:r>')
            continue
        ltr = part.startswith('`')
        if ltr: part = part[1:-1]
        rp = ''
        if bold: rp += '<w:b/><w:bCs/>'
        if italic: rp += '<w:i/><w:iCs/>'
        if noproof: rp += '<w:noProof/>'
        sz = 21 if small else size
        if ltr: sz = (size or 32) - 4  # Latin a touch smaller, as in source
        if sz: rp += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
        # Latin runs are not Arabic text (their digits stay 123 in the PDF); in a left-to-right paragraph they must also
        # drop the right-to-left flag every run inherits, or the punctuation at their edges jumps to the wrong side
        rp += (('<w:rtl w:val="0"/>' if ltr_para else '') + '<w:lang w:val="en-US"/>') if ltr else '<w:rtl/>'
        for txt, f in seg(part):
            f = f if f == SYMBOL_FONT else FALLBACK if (f or ltr) else None   # Latin runs in Times (Lotus Latin spacing is Arabic-style)
            fb = f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}"/>' if f else ''
            out.append(f'<w:r><w:rPr>{fb}{rp}</w:rPr><w:t xml:space="preserve">{escape(txt)}</w:t></w:r>')
    return ''.join(out)

def P(text='', style=None, jc=None, before=None, after=None, ind=None, numid=None, lvl=0, bold=False, size=None, extra='', line=None):
    pp = ''
    if style: pp += f'<w:pStyle w:val="{style}"/>'
    if numid: pp += f'<w:numPr><w:ilvl w:val="{lvl}"/><w:numId w:val="{numid}"/></w:numPr>'
    pp += extra
    pp += '<w:bidi/>'
    if before is not None or after is not None or line:
        pp += ('<w:spacing' + (f' w:before="{before}"' if before is not None else '') + (f' w:after="{after}"' if after is not None else '')
               + (f' w:line="{line}" w:lineRule="auto"' if line else '') + '/>')
    if ind: pp += ind
    if jc: pp += f'<w:jc w:val="{jc}"/>'
    return f'<w:p><w:pPr>{pp}</w:pPr>{runs(text, bold, size)}</w:p>'

def H1(t): return P(t, 'Heading1')
def H2(t): return P(t, 'Heading2')
def bullet(t, lvl=0, bold=True): return P(t, numid=1, lvl=lvl, bold=(bold and lvl==0))
# Hanging indents: in a right-to-left paragraph the start side is «left» in WordprocessingML, so the number of an item,
# a bullet or a footnote begins exactly at the text edge and the text hangs inward from it.
def item(num, t, sep='-'):  # "١-" / "١." / "١)" hanging item, number as the author wrote it
    return P(f'{num}{sep}\t{t}', ind='<w:ind w:left="425" w:hanging="425"/>')
def fn(n, t): footnotes[n] = t

# ---------- tables ----------
def cell(t, w, head=False, jc='center', shade=None):
    sh = f'<w:shd w:val="clear" w:color="auto" w:fill="{shade}"/>' if shade else ''
    para = P(t, 'TableText', jc=jc, bold=head, size=28)
    return f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{sh}<w:vAlign w:val="center"/></w:tcPr>{para}</w:tc>'
def table(rows, widths, head_rows=1, first_col_head=False, body_jc='center'):
    b = ''.join(f'<w:{s} w:val="single" w:sz="6" w:space="0" w:color="000000"/>' for s in ['top','left','bottom','right','insideH','insideV'])
    grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    out = [f'<w:tbl><w:tblPr><w:bidiVisual/><w:tblW w:w="{sum(widths)}" w:type="dxa"/><w:jc w:val="center"/><w:tblBorders>{b}</w:tblBorders><w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="100" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    for i, r in enumerate(rows):
        head = i < head_rows
        trpr = '<w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>' if head else '<w:trPr><w:cantSplit/></w:trPr>'
        cells = ''
        for j, (t, w) in enumerate(zip(r, widths)):
            h = head or (first_col_head and j == 0)
            jc = 'center' if (head or j < len(r)-1 or body_jc=='center') else body_jc
            cells += cell(t, w, head=h, jc=jc, shade='D9D9D9' if head else ('F2F2F2' if (first_col_head and j==0) else None))
        out.append(f'<w:tr>{trpr}{cells}</w:tr>')
    out.append('</w:tbl>')
    return ''.join(out)

# ---------- page numbers that each program computes for itself ----------
# Every number in the contents and the indexes is a PAGEREF field to a bookmark where the heading or the entry stands.
# Its stored value is the page in the PDF (make.py reads it from the PDF's named destinations); LibreOffice computes
# the field again as it lays the PDF out, and Word computes it from its own layout when the reader lets it update the
# fields (the file asks for that when it opens), so each file's numbers are its own pages.
# The fields are not links: make.py counts the PDF's links to find the footnote references.
TOC_ENTRIES = []   # (heading text, level, bookmark number)
def with_bookmark(par, name, n):
    return par.replace('</w:pPr>', '</w:pPr>' + bookmark(name, n), 1)

def pageref(name, cached, bold=False):
    r = '<w:rPr>' + ('<w:b/><w:bCs/>' if bold else '') + '<w:rtl/></w:rPr>'
    return (f'<w:r>{r}<w:fldChar w:fldCharType="begin"/></w:r><w:r>{r}<w:instrText xml:space="preserve"> PAGEREF {name} </w:instrText></w:r>'
            f'<w:r>{r}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{r}<w:t>{cached}</w:t></w:r><w:r>{r}<w:fldChar w:fldCharType="end"/></w:r>')

def page_cached(name):
    if not PAGES: return '٠٠'
    if name.startswith('_pre') and name in PAGES and '_sec1' in PAGES:   # a prelims page: its letter (the first one is ب)
        return abjad(PAGES[name] - PAGES['_sec1'] + 2)
    return str(PAGES[name]).translate(HINDI) if name in PAGES else '؟'

def numbered_line(text, refs, ind='', bold=False):
    """A line of the contents or of an index: the text, dot leaders, then its page numbers (fields), «٣، ١٢»."""
    tabs = f'<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{TEXTW}"/></w:tabs>'
    par = P(f'{text}\t', jc="right", after=40, ind=ind, bold=bold, extra=tabs)
    sep = f'<w:r><w:rPr>{"<w:b/><w:bCs/>" if bold else ""}<w:rtl/></w:rPr><w:t xml:space="preserve">، </w:t></w:r>'
    nums = sep.join(pageref(n, page_cached(n), bold) for n in refs) if refs else f'<w:r><w:rPr><w:rtl/></w:rPr><w:t>{"٠٠" if not PAGES else "؟"}</w:t></w:r>'
    return par[:-len('</w:p>')] + nums + '</w:p>'

def toc(entries=None):
    out = []
    for t, lvl, name in TOC_ENTRIES:
        ind = '<w:ind w:left="567"/>' if lvl == 2 else ''   # the start side (see the note on hanging indents above)
        # a Latin title (Abstract) keeps the Latin font in its line, as under its heading
        t = '`'.join(x if k % 2 else LATIN.sub(lambda m: '`\u202a' + m.group(0) + '\u202c`', x) for k, x in enumerate(t.split('`')))
        out.append(numbered_line(t, [name], ind=ind, bold=(lvl == 1)))
    return ''.join(out)

def toc_head(par, text, lvl):
    """A heading the contents list: it gets a bookmark the contents' page number refers to."""
    k = len(TOC_ENTRIES) + 1
    name = f'_pre{k}' if PROFILE == 'kku' and SECT in ('front', 'prelims') else f'_toc{k}'   # the prelims are numbered in letters
    TOC_ENTRIES.append((re.sub(r'\*\*|\[\^[^\]]+\]', '', indexes.strip_marks(text)).strip(), lvl, name))
    return with_bookmark(par, name, 900000 + k)


# ================= PARSER (markdown-ish input) =================
LATIN = re.compile(r'[A-Za-z][A-Za-z0-9 .,:;/_\-@&+#%=?~]*[A-Za-z0-9/]|[A-Za-z]')
VREF = re.compile(r'(\[[^\[\]\^]+?:\s*[٠-٩0-9\-–، ]+\])')
DEATH = re.compile(r'\((ت\s*:\s*)([٠-٩0-9]+(?:هـ|ه)?)\)')
# Short references in () or [] that hold a number — (ت: ٤٦٨) (٢/ ٦٥٣) (١٢/٢٨٣) [البقرة: ١٤٣] — must never
# split across lines. Glue them with invisible aids only: spaces become no-break spaces and a word joiner
# goes between parts (never between two Arabic letters, so shaping is untouched). Visible text is unchanged.
SHORTREF = re.compile(r'[\(\[][^()\[\]\n⟦⟧⟪⟫⟬⟭⟮⟯⟨⟩`^]{1,28}[\)\]]')
AR = re.compile(r'[\u0621-\u064A\u066E-\u06D3]')
WJ, NBSP = '\u2060', '\u00a0'
def glue(m):
    tok = m.group(0)
    if not re.search(r'[٠-٩0-9]', tok) or len(tok.split()) > 4: return tok
    out = ''
    for i, ch in enumerate(tok):
        if ch == ' ': out += NBSP; continue
        if i and out and out[-1] not in (NBSP, WJ) and not (AR.match(ch) and AR.match(tok[i-1])) and not (ch.isdigit() and tok[i-1].isdigit()) and not unicodedata.combining(ch) and ch not in '\u200e\u200f\u0651\u064b\u064c\u064d\u064e\u064f\u0650\u0652':
            out += WJ
        out += ch
    return out
# Uthmani script is opt-in (the user must ask for it). Only what the author marked as a verse is looked at: the text
# between ﴿ ﴾, and the text between quotation marks or parentheses when a phrase that says so comes right before it
# (قال تعالى، قوله تعالى، قال الله، وقال سبحانه…). The rest of the author's words are never searched. The verse's place
# is helped by the reference after it — [البقرة: ١٤٣], or the surah's name alone — or by «سورة …» right before it.
# A verse that is not recognised stays exactly as written.
UTHMANI = False; QURAN_USED = False
VERSE = re.compile(r'(﴿)([^﴿﴾]+)(﴾)')
QUOTED = re.compile(r'(«)([^«»﴿﴾⟪⟫]+)(»)|(")([^"﴿﴾⟪⟫]+)(")|(“)([^“”﴿﴾⟪⟫]+)(”)|(\()([^()﴿﴾⟪⟫]+)(\))')
SAYS = re.compile(r'(?:قال|قوله|يقول|قول)\s+(?:الله|تعالى|سبحانه|ربنا|عز|جل|تبارك)[^.؛!؟?«»"“”()﴿﴾⟪⟫]{0,40}$')
REF = re.compile(r'\s*[\[(]\s*([^\[\]()\^:٠-٩0-9]+?)\s*(?::\s*([٠-٩0-9\-–، ]+?))?\s*[\])]')
NAMED = re.compile(r'سورة\s+([^\s:،]+)(\s+[^\s:،]+)?\s*[:،]?\s*$')
STANDALONE = re.compile(r'^\s*﴿[^﴿﴾]+﴾(?:\s*\[[^\[\]]*\])*[\s.،؛:]*$')   # a paragraph that is only a verse
def bare(t): return ''.join(c for c in t if unicodedata.category(c) != 'Mn')
# ---------- index entries ----------
# Marks in in.md ({{علم|…}}, see indexes.py) leave the author's words in place and record an entry; in the text a
# bookmark goes where the entry stands, and make.py reads its page from the PDF. An entry inside a footnote takes the
# page of the note's reference (LibreOffice gives no page to a bookmark inside a note).
IX = []            # dict(id, kind, text, entry, group, note, place)
IX_WANT = set()    # the indexes asked for (@index lines)
IX_UNPLACED = []   # verses the index of verses could not place: (verse, why) — reported, in Arabic
IX_UNKNOWN = []    # marks of an unknown kind (their words are kept, the mark is dropped)
CUR_NOTE = None    # the footnote being set
IX_OFF = False     # True while the indexes themselves are set: nothing is recorded or converted then
PAGES = {}         # bookmark name -> page (make.py)
def take_marks(t):
    def mk(m):
        k = indexes.kind(m.group(1)); words = m.group(2)
        if IX_OFF: return words
        if k not in indexes.MARKABLE: IX_UNKNOWN.append(m.group(1).strip()); return words
        n = len(IX) + 1
        IX.append(dict(id=n, kind=k, text=words, entry=(m.group(3) or '').strip() or words.strip(),
                       group=(m.group(4) or '').strip() or None, note=CUR_NOTE, place=None))
        return words if CUR_NOTE else f'⟮{n}⟯{words}'
    return indexes.MARK.sub(mk, t)

# ---------- citation styles (on request): {{مرجع|id|place}} -> the citation in the chosen style ----------
CITES = {}; CITE_STYLE = None; CITED = set(); CITE_ORDER = []
CITE = re.compile(r'\{\{\s*مرجع\s*\|([^{}|]+)(?:\|([^{}|]*))?\}\}')
def expand_cites(t):
    def f(m):
        sid = m.group(1).strip()
        if not CITE_STYLE: raise SystemExit(f'a citation {{{{مرجع|{sid}}}}} needs --cite=STYLE and --sources=FILE')
        if sid not in CITES: raise SystemExit(f'citation of an unknown source id: {sid}')
        first = sid not in CITED; CITED.add(sid)
        if first: CITE_ORDER.append(sid)
        t = cite.note(CITES[sid], m.group(2) or '', CITE_STYLE, first, CITE_ORDER.index(sid) + 1)
        # a full stop closes the citation only where nothing of the author's follows it and it does not end in one
        rest = m.string[m.end():].strip()
        return t + ('.' if not rest and not re.search(r'[.!?؟]\s*$', t) else '')
    return CITE.sub(f, t)

def verse(m):
    """What the author marked as a verse: set in Uthmani script when asked for, and entered in the index of verses."""
    global QURAN_USED
    op, v, cl = [g for g in m.groups() if g is not None]
    before = bare(m.string[:m.start()])
    if IX_OFF or (op != '﴿' and not SAYS.search(before)): return m.group(0)
    ref = None; r = REF.match(m.string, m.end()); n = NAMED.search(before)
    if r and (r.group(2) or quran.surah(r.group(1))): ref = (r.group(1), r.group(2))
    elif n: ref = next(((x, None) for x in (n.group(1) + (n.group(2) or ''), n.group(1)) if quran.surah(x)), None)
    out = m.group(0); u = None
    if UTHMANI:
        u = quran.convert(v, ref)
        if u is not None:
            QURAN_USED = True
            # the marks around the verse are marked no-proof too: Word checks «﴿word» as one word across the run boundary
            out = '⟬' + op + '⟭' + v[:len(v) - len(v.lstrip())] + '⟪' + u + '⟫' + v[len(v.rstrip()):] + '⟬' + cl + '⟭'
    if 'آية' in IX_WANT:
        hit, why = quran.place(v, ref)
        if hit and not why:
            k = len(IX) + 1
            shown = '⟬﴿⟭⟪' + u + '⟫⟬﴾⟭' if u is not None else '﴿' + v.strip() + '﴾'
            IX.append(dict(id=k, kind='آية', text=shown, entry=shown, group=None, note=CUR_NOTE, place=hit[:3]))
            if not CUR_NOTE: out = f'⟮{k}⟯' + out
        else: IX_UNPLACED.append((v.strip(), why))
    return out
uthmani = verse
def inline(t, fnmap):
    t = take_marks(expand_cites(t))
    if UTHMANI or 'آية' in IX_WANT: t = QUOTED.sub(verse, VERSE.sub(verse, t))
    t = re.sub(r'\[\^([^\]]+)\]', lambda m: '^%d' % fnmap.setdefault(m.group(1), len(fnmap)+1), t)
    t = DEATH.sub(lambda m: '⟦(' + m.group(1) + m.group(2) + ')⟧', t)   # spacing kept exactly as written
    t = VREF.sub(r'⟦\1⟧', t)
    t = SHORTREF.sub(glue, t)
    # a bracket that closes the paragraph gets a right-to-left mark after it (Word mirrors it the wrong way otherwise)
    t = re.sub(r'([\)\]])(⟧?)\s*$', lambda m: m.group(1) + RLM + m.group(2), t)
    parts = re.split(r'(`[^`]*`)', t)
    # A Latin run is held in a left-to-right embedding (LRE…PDF): Word otherwise resolves the direction of each line on
    # its own, and a comma or a number that ends a line inside a wrapped Latin run jumps to the other end of that line.
    # A run that ends in a sign (a URL's closing «/») also gets a left-to-right mark, or the sign jumps to its other end.
    def latin(m): return '`\u202a' + m.group(0) + ('' if m.group(0)[-1].isalnum() else '\u200e') + '\u202c`'
    out = ''.join(p if p.startswith('`') else LATIN.sub(latin, p) for p in parts)
    # A text with no Arabic letter (a Latin reference in a numbered list): the full stop that closes it belongs to the
    # Latin, so a left-to-right mark follows it, or it lands at the far (left) end of the line, away from its word
    if not AR.search(out) and LATIN.search(out): out = re.sub(r'([.,;:!?]+)((?:\^\d+)*)$', '\\1\u200e\\2', out)
    return out

META = {}
BREAK_BEFORE = set()   # indexes of the # / ## / ### headings that start a new page (set by make.py for the PDF only)
HEADER = None          # the running header (@header), on request only
BASMALA = None         # 1-7: the opening basmala set as one of Lotus Lotfi's basmalas (on request only)
BASMALA_USED = False
SORT_KEPT = []         # @sort blocks left in their order because the author numbered them
def sort_blocks(body):
    """@sort … @end: the author's lines in between (a list of sources) in alphabetical order, each line unchanged. A list
    the author numbered keeps its order (renumbering would change the text)."""
    out = []; block = None
    for ln in body:
        if ln.strip() == '@sort' and block is None: block = []; continue
        if ln.strip() == '@end' and block is not None:
            items = [l for l in block if l.strip()]
            if any(re.match(r'^\s*[٠-٩0-9]+\s*[-–.)]', l) for l in items): SORT_KEPT.append(len(items)); out += block
            else: out += sorted(items, key=lambda l: indexes.order(indexes.key(indexes.strip_marks(l.lstrip('-*> ')), True)))
            block = None; continue
        (block if block is not None else out).append(ln)
    return out + (block or [])

def basmala_par():
    """The opening basmala as one of Lotus Lotfi's own basmalas, centred, sized to about half the line."""
    global BASMALA_USED
    BASMALA_USED = True
    c = indexes.SHAPES[BASMALA - 1]; f = TTFont(_os.path.join(HERE, "..", "assets", "fonts", "_LotusLotfi-Regular.ttf"))
    adv = f['hmtx'][f.getBestCmap()[c]][0] / f['head'].unitsPerEm
    pt = max(18, min(48, round(230 / adv)))   # ~230 pt wide (the line is ~454 pt), never smaller than the text around it
    fonts = f'<w:rFonts w:ascii="{LOTUS}" w:hAnsi="{LOTUS}" w:eastAsia="{LOTUS}" w:cs="{LOTUS}"/>'
    return (f'<w:p><w:pPr><w:bidi/><w:spacing w:before="0" w:after="360"/><w:jc w:val="center"/></w:pPr>'
            f'<w:r><w:rPr>{fonts}<w:noProof/><w:sz w:val="{2 * pt}"/><w:szCs w:val="{2 * pt}"/><w:rtl/></w:rPr><w:t>{chr(c)}</w:t></w:r></w:p>')

# ================= THESIS (the King Khalid University guide) =================
# «دليل كتابة الرسائل العلمية وإخراجها»، الإصدار الثاني ١٤٤٣هـ (docs/kku-guide-review.md). Chosen with --profile=kku; the
# guide decides everything it states for a thesis: Traditional Arabic 16 with 1.5 lines, headings 20 and 18, margins 3.5 cm
# on the right and 2.5 cm elsewhere, the title page, the approval page and the basmala page of its models, the prelims
# numbered in letters (ب، ج…) and the text from ١, a page of its own before each part (باب) and each appendix, and the
# lists of tables and figures. The fixed wording of its pages is the guide's own; every detail of the student's comes
# from the student, never invented.
PROFILE = 'paper'
SECT = 'front'          # the section being written: front (title, approval, basmala), prelims, text
THESIS_NOTES = []       # in Arabic, for the reply
CAPS = []               # captions of tables and figures: (kind, text, number)
LOGO = None             # (bytes, extension, width EMU, height EMU)
ABJAD = ['أ', 'ب', 'ج', 'د', 'هـ', 'و', 'ز', 'ح', 'ط', 'ي', 'ك', 'ل', 'م', 'ن', 'س', 'ع', 'ف', 'ص', 'ق', 'ر', 'ش', 'ت', 'ث', 'خ', 'ذ', 'ض', 'ظ', 'غ']
def abjad(n): return ABJAD[n - 1] if 1 <= n <= len(ABJAD) else str(n).translate(HINDI)
def title_key(t):
    return re.sub(r'[^\u0621-\u064Aa-z]', '', indexes.bare(indexes.strip_marks(t)).lower().translate(str.maketrans('أإآة', 'اااه')))
PRELIM = {title_key(x): k for x, k in (
    ('الإهداء', 'other'), ('إهداء', 'other'), ('الشكر والتقدير', 'ack'), ('شكر وتقدير', 'ack'), ('الشكر', 'ack'), ('شكر وعرفان', 'ack'),
    ('المستخلص', 'abs_ar'), ('مستخلص الرسالة', 'abs_ar'), ('ملخص الرسالة', 'abs_ar'), ('الملخص', 'abs_ar'), ('المستخلص باللغة العربية', 'abs_ar'),
    ('مستخلص الرسالة باللغة العربية', 'abs_ar'), ('Abstract', 'abs_en'), ('المستخلص باللغة الإنجليزية', 'abs_en'), ('مستخلص الرسالة باللغة الإنجليزية', 'abs_en'),
    ('قائمة الرموز والمصطلحات', 'other'), ('قائمة الرموز', 'other'), ('قائمة المصطلحات', 'other'))}
REFS = re.compile(r'المراجع|المصادر|References|Bibliography')
CAPTION = re.compile(r'^(?:>>\s*)?(?:\*\*)?\s*(جدول|الجدول|شكل|الشكل)\s*(?:رقم)?\s*\(?\s*[٠-٩0-9]+(?:\s*[-–.]\s*[٠-٩0-9]+)?\s*\)?\s*[:：\-–]')
EMU = 360000   # per cm

def frame_lines(lines, ycm, size, width=None, xalign='center', bold=True, font=None):
    """Lines set at a fixed place on the page (cm from the top edge), as the guide's models measure them; a block that
    wraps to more lines does not move the next one."""
    w = width or TEXTW
    fp = f'<w:framePr w:w="{w}" w:hSpace="0" w:wrap="notBeside" w:vAnchor="page" w:hAnchor="margin" w:xAlign="{xalign}" w:y="{int(ycm * 567)}"/>'
    sp = f'<w:spacing w:before="0" w:after="0" w:line="{size * 15}" w:lineRule="exact"/>'
    def r(t):
        if not font: return runs(inline(t, {}), bold, size)
        # a font of its own (the thesis title): no added bold, since its one face is drawn bold; Latin keeps Times
        f = f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="{font}" w:cs="{font}"/>'
        return re.sub(r'<w:rPr>(?!<w:rFonts)', '<w:rPr>' + f, runs(inline(t, {}), False, size))
    return ''.join(f'<w:p><w:pPr>{fp}<w:bidi/>{sp}<w:jc w:val="center"/></w:pPr>{r(t)}</w:p>' for t in lines)

def logo_run(ycm):
    """The university's logo, 4 × 4 cm at most, at the left of the text area, ycm from the top (the user's own image)."""
    if not LOGO: return ''
    data, ext, cx, cy = LOGO
    return (f'<w:r><w:drawing><wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="1" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">'
            f'<wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="page"><wp:posOffset>{int(2.5 * EMU)}</wp:posOffset></wp:positionH>'
            f'<wp:positionV relativeFrom="page"><wp:posOffset>{int(ycm * EMU)}</wp:posOffset></wp:positionV><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/><wp:docPr id="{int(ycm * 10)}" name="logo"/><wp:cNvGraphicFramePr/>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="1" name="logo"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="rIdLogo"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r>')

def load_logo(path):
    """-> (bytes, extension, cx, cy) fitted into 4 × 4 cm with its own proportions (PNG or JPEG)."""
    import struct
    data = open(path, 'rb').read()
    if data[:8] == b'\x89PNG\r\n\x1a\n': w, h = struct.unpack('>II', data[16:24]); ext = 'png'
    elif data[:2] == b'\xff\xd8':
        i = 2; w = h = None
        while i < len(data) - 9:
            if data[i] != 0xFF: i += 1; continue
            marker, seglen = data[i + 1], struct.unpack('>H', data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2): h, w = struct.unpack('>HH', data[i + 5:i + 9]); break
            i += 2 + seglen
        ext = 'jpeg'
        if not w: raise SystemExit('logo: could not read the size of the JPEG image')
    else: raise SystemExit('logo: a PNG or JPEG image is needed')
    k = 4 * EMU / max(w, h)
    return data, ext, int(w * k), int(h * k)

def fixed(k, prefix):
    """A detail of the student's, with the guide's word before it when the student wrote it without («كلية …»)."""
    v = META.get(k, '').strip()
    return v if not v or v.startswith(prefix) else f'{prefix} {v}'

def thesis_front(body):
    """The title page (model 1), the approval page (model 3, when asked for) and the basmala page (when asked for)."""
    m = META; out = []
    missing = [n for k, n in (('title', 'عنوان الرسالة'), ('college', 'الكلية'), ('department', 'القسم'), ('degree', 'الدرجة'), ('field', 'التخصص'),
                              ('author', 'اسم الطالب'), ('supervisor', 'اسم المشرف ولقبه'), ('date', 'تاريخ المناقشة')) if not m.get(k)]
    if missing: THESIS_NOTES.append('THESIS: لم يصلني من بيانات صفحة العنوان: ' + '، '.join(missing))
    if not LOGO: THESIS_NOTES.append('THESIS: لم يصلني شعار الجامعة، فتُرك مكانه في صفحة العنوان وصفحة الإجازة فارغًا')
    tf = title_font(); tf = tf[0] if tf else None   # the guide's title font, when its file is in the skill
    if not tf: THESIS_NOTES.append('THESIS: عنوان الرسالة بخط Traditional Arabic عريض ٢٠، لأن خط PT Bold Heading الذي يسمّيه الدليل ليس في المهارة')
    head = ['المملكة العربية السعودية', 'وزارة التعليم', 'جامعة الملك خالد'] + [x for x in (fixed('college', 'كلية'), fixed('department', 'قسم')) if x]
    statement = (f'قُدمت هذه الرسالة استكمالاً لمتطلبات الحصول على درجة {m["degree"]}' + (f' في {m["field"]}' if m.get('field') else '')) if m.get('degree') else ''
    out.append(frame_lines(head, 3, 32, width=TEXTW // 2, xalign='right'))
    # the logo hangs on an ordinary paragraph of the page (LibreOffice drops a picture anchored in a placed paragraph)
    out.append(f'<w:p><w:pPr><w:bidi/><w:spacing w:before="0" w:after="0"/></w:pPr>{logo_run(3)}</w:p>' if LOGO else '')
    out.append(frame_lines([m['title']] if m.get('title') else [], 11, 40, font=tf))
    out.append(frame_lines([statement] if statement else [], 15, 32))
    out.append(frame_lines([m['author']] if m.get('author') else [], 18, 40))
    out.append(frame_lines([m['supervisor']] if m.get('supervisor') else [], 21, 40))
    out.append(frame_lines([m['date']] if m.get('date') else [], 26, 28))
    if any(l.strip() == '@approval' for l in body):
        out.append(PAGEBREAK)
        head2 = ['جامعة الملك خالد'] + [x for x in (fixed('college', 'كلية'), fixed('department', 'قسم'),
                                                       f'التخصص: {m["field"]}' if m.get('field') else '', f'الدرجة العلمية: {m["degree"]}' if m.get('degree') else '') if x]
        out.append(frame_lines(head2, 2, 32, width=TEXTW // 2, xalign='right'))
        out.append(f'<w:p><w:pPr><w:bidi/><w:spacing w:before="0" w:after="0"/></w:pPr>{logo_run(2)}</w:p>' if LOGO else '')
        out.append(frame_lines([m['title']] if m.get('title') else [], 10, 40, font=tf))
        out.append(frame_lines([m['author']] if m.get('author') else [], 15, 32))
        out.append(frame_lines(['إجازة أعضاء لجنة المناقشة والحكم للرسالة بعد إجراء التعديلات المطلوبة (إن وُجدت)',
                                'التاريخ:      /      /      ١٤هـ   –      /      /      ٢٠م'], 17, 32))
        out.append(frame_lines(['أعضاء لجنة المناقشة والحكم'], 20, 32))
        names = [x.split('|')[0].strip() for x in m.get('members', [])]
        roles = ['مشرف ومقرر', 'مناقش أول/ داخلي', 'مناقش ثاني/', 'مناقش ثالث/', 'مناقش رابع/']
        rows = [['**الاسم**', '**صفة المشاركة**', '**التوقيع**']] + [[names[i] if i < len(names) else '', r, ''] for i, r in enumerate(roles)]
        w3 = [TEXTW * 2 // 5, TEXTW * 3 // 10, TEXTW - TEXTW * 2 // 5 - TEXTW * 3 // 10]
        tbl = table([[inline(c, {}) for c in r] for r in rows], w3)
        out.append(tbl.replace('<w:tblPr>', f'<w:tblPr><w:tblpPr w:leftFromText="0" w:rightFromText="0" w:vertAnchor="page" w:horzAnchor="margin" w:tblpXSpec="center" w:tblpY="{int(21.2 * 567)}"/>', 1))
        out.append(P('', after=0))
    if any(l.strip() == '@basmala' for l in body):
        out.append(PAGEBREAK)
        if not BASMALA: THESIS_NOTES.append('THESIS: صفحة البسملة تحتاج رقم شكلها (١–٧)')
        else:
            c = indexes.SHAPES[BASMALA - 1]; f = TTFont(_os.path.join(HERE, "..", "assets", "fonts", "_LotusLotfi-Regular.ttf"))
            adv = f['hmtx'][f.getBestCmap()[c]][0] / f['head'].unitsPerEm
            pt = max(28, min(110, round(330 / adv)))   # «بخط كبير، ومميز، وسط الصفحة»: about 11.5 cm wide
            fonts = f'<w:rFonts w:ascii="{LOTUS}" w:hAnsi="{LOTUS}" w:eastAsia="{LOTUS}" w:cs="{LOTUS}"/>'
            fp = f'<w:framePr w:w="{TEXTW}" w:hSpace="0" w:wrap="notBeside" w:vAnchor="page" w:hAnchor="margin" w:xAlign="center" w:y="{int(11 * 567)}"/>'
            out.append(f'<w:p><w:pPr>{fp}<w:bidi/><w:spacing w:before="0" w:after="0"/><w:jc w:val="center"/></w:pPr>'
                       f'<w:r><w:rPr>{fonts}<w:noProof/><w:sz w:val="{2 * pt}"/><w:szCs w:val="{2 * pt}"/><w:rtl/></w:rPr><w:t>{chr(c)}</w:t></w:r></w:p>')
            global BASMALA_USED
            BASMALA_USED = True
        out.append(P('', after=0))
    else:
        out.append(P('', after=0))
    return out

PAGEBREAK = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
def separator(lines, sizes):
    """A page with only these lines, in the middle of the page (a part's title, an appendix's number and title)."""
    out = [P(t, 'Heading1' if k == 0 else None, jc='center', bold=True, size=sz, before=4800 if k == 0 else 120, after=0,
             extra='' if k == 0 else '<w:keepNext/>') for k, (t, sz) in enumerate(zip(lines, sizes))]
    return out

def parse(path):
    global HEADER, CUR_NOTE, SECT
    lines = open(path, encoding='utf-8').read().split('\n')
    B_ = []; fnmap = {}; fndefs = {}
    i = 0
    if lines and lines[0].strip() == '---':
        i = 1; META['lines'] = []
        while lines[i].strip() != '---':
            k, _, v = lines[i].partition(':')
            k = k.strip(); v = v.strip()
            if k == 'line': META['lines'].append(v)
            elif k == 'member': META.setdefault('members', []).append(v)
            elif k: META[k] = v
            i += 1
        i += 1
    body = []
    for ln in lines[i:]:
        m = re.match(r'^\[\^([^\]]+)\]:\s*(.*)$', ln)
        if m: fndefs[m.group(1)] = m.group(2)
        elif re.match(r'^@header\b', ln.strip()):   # the running header: the text given, or the title of the work
            HEADER = ln.strip()[len('@header'):].strip() or True
        else: body.append(ln)
    body = sort_blocks(body)
    for ln in body:
        k = indexes.directive(ln)
        if k: IX_WANT.add(k)
    if HEADER is True:
        first = next((l for l in body if l.strip() and not l.startswith('@') and not indexes.is_basmala(l)), '')
        HEADER = META.get('title') or (first[2:] if first.startswith('# ') else None)
        if not HEADER: raise SystemExit('@header: the work has no title to put in the header; give the header text after @header')
    if HEADER: HEADER = re.sub(r'\*\*|\[\^[^\]]+\]', '', indexes.strip_marks(HEADER)).strip()
    if PROFILE == 'kku':
        global LOGO
        if META.get('logo'):
            lp = META['logo'] if os.path.isabs(META['logo']) else os.path.join(os.path.dirname(os.path.abspath(path)), META['logo'])
            LOGO = load_logo(lp)
        B_.extend(thesis_front(body))
        body = [l for l in body if l.strip() not in ('@approval', '@basmala')]
    elif META.get('title'):
        B_.append(P(inline(META['title'], fnmap), 'CoverTitle', before=3400))
        for k, l in enumerate(META.get('lines', [])):
            B_.append(P(inline(l, fnmap), jc='center', before=240 if k == 0 else None, after=40))
        if META.get('author'):
            B_.append(P('إعداد:', jc='center', before=2000, after=200))
            B_.append(P('**' + inline(META['author'], fnmap) + '**', jc='center', after=40))
            if META.get('affiliation'): B_.append(P(inline(META['affiliation'], fnmap), jc='center'))
        if META.get('date'): B_.append(P(inline(META['date'], fnmap), jc='center', before=2400))
    tbl = []
    def flush():
        if not tbl: return
        rows = [[c.strip() for c in r.strip().strip('|').split('|')] for r in tbl if not re.match(r'^\|?\s*:?-{2,}', r.strip())]
        n = len(rows[0])
        def plain(c): return re.sub(r'\*\*|\[\^[^\]]+\]', '', c).strip()
        def need(j):  # twips a column needs to hold its widest cell on one line (14pt Lotus ≈ 135 twips/char) + cell margins
            longest = max((len(plain(r[j])) for r in rows if j < len(r)), default=0)
            word = max((len(w) for r in rows if j < len(r) for w in plain(r[j]).split()), default=0)
            return min(max(longest * 135 + 300, word * 150 + 300, 680), 3200)
        last_long = max(len(plain(r[-1])) for r in rows) > 60
        if last_long and n > 1:
            fixed = [need(j) for j in range(n - 1)]
            widths = fixed + [TEXTW - sum(fixed)]
        else:
            widths = [TEXTW // n]*n
            # widen any column whose longest word would otherwise break, taking space from the others
            mins = [min(max(len(w) for r in rows if j < len(r) for w in (plain(r[j]).split() or [''])) * 150 + 300, TEXTW // 2) for j in range(n)]
            short = [j for j in range(n) if widths[j] < mins[j]]
            if short:
                extra = sum(mins[j] - widths[j] for j in short)
                rest = [j for j in range(n) if j not in short]
                if rest:
                    for j in short: widths[j] = mins[j]
                    for j in rest: widths[j] -= extra // len(rest)
            widths[-1] += TEXTW - sum(widths)
        B_.append(table([[inline(c, fnmap) for c in r] for r in rows], widths, body_jc='both' if last_long else 'center'))
        B_.append(P('', after=0)); tbl.clear()
    # An article with no cover opens with its title: the first block, if it is a level-1 heading, sits ~4 lines down
    # with ~3 lines below it (a line ≈ 24 pt), and the text follows on the same page. A «>>» line right under it (the
    # writer's name, when the author's text has one) shares that gap: one line above it, one below.
    # With a cover (a research paper) every level-1 heading starts a new page; with none (an article) the later ones
    # follow on, ~1.5 lines below the text before them — except the first one after the contents, which starts the text
    # on a new page.
    LINE = 480; started = False; after_title = False; nhead = 0; after_toc = False
    # the opening basmala (the first line of the text, before its title or its first paragraph) stands apart from the text
    lead = next((k for k, l in enumerate(body) if l.strip()), None)
    opening = lead if lead is not None and indexes.is_basmala(body[lead]) else None
    topgap = 4 * LINE   # above an article's title: ~4 lines, or one line when the basmala stands above it
    nonblank = [l.rstrip() for k, l in enumerate(body) if l.strip() and k != opening]
    cover_open = bool(META.get('title')) and PROFILE != 'kku'
    kind = None        # the kind of the thesis section being set (acknowledgements, abstract, references…)
    napp = 0           # appendices so far
    def enter(k):      # a new section of the thesis: the Word file and the PDF start a page with its own numbering
        global SECT
        B_.append(f'SECT:{k}'); SECT = 'prelims' if k == 'prelims' else 'text'
    def is_prelim(line):
        t = line.strip()
        return t in ('@toc', '@figures', '@tables') or (t.startswith('# ') and title_key(t[2:]) in PRELIM)
    # contents placed after the text (at the end, with the indexes) start a page of their own in an article too
    toc_late = False; titled = False
    for l in body:
        t = l.strip()
        if t == '@toc': break
        if not t or t.startswith(('@', '>> ')) or indexes.is_basmala(t): continue
        if t.startswith('# ') and not titled: titled = True; continue
        toc_late = True; break
    for ln in body:
        s_ = ln.rstrip()
        # the cover stands on its own page: the text after it starts a new one even when it does not open with a level-1
        # heading or the contents (which start a new page by themselves)
        if cover_open and s_.strip():
            if not (s_.startswith('# ') or s_.strip() in ('@toc', '@pagebreak')): B_.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
            cover_open = False
        if s_.startswith('|'): tbl.append(s_); continue
        flush()
        if not s_.strip(): continue
        if PROFILE == 'kku':
            t_ = s_.strip()
            if SECT == 'front' and not indexes.directive(t_) and t_ not in ('@pagebreak',) and not (opening is not None and s_ == body[opening].rstrip()):
                enter('prelims' if is_prelim(s_) else 'text')
            elif SECT == 'prelims' and t_.startswith('# ') and not is_prelim(s_):
                enter('text')
            if t_.startswith('# '):
                h = t_[2:]
                kind = PRELIM.get(title_key(h)) or ('refs' if REFS.search(indexes.bare(h)) else None)
                if SECT == 'text' and indexes.bare(h).startswith('الباب'):   # a part: its title alone on a page, no number shown
                    enter('bab')
                    B_.append(toc_head(separator([inline(h, fnmap)], [40])[0], h, 1)); B_.append(PAGEBREAK)
                    nhead += 1; started = True; continue
            if t_ in ('@figures', '@tables'):
                cap = 'figure' if t_ == '@figures' else 'table'; ttl = 'قائمة الأشكال' if cap == 'figure' else 'قائمة الجداول'
                B_.append(toc_head(H1(ttl), ttl, 1)); B_.append(f'CAPLIST:{cap}'); kind = None; continue
            if t_.startswith('@appendix'):
                napp += 1; ttl = t_[len('@appendix'):].strip(); num = f'ملحق رقم ({str(napp).translate(HINDI)})'
                sep = separator([num] + ([inline(ttl, fnmap)] if ttl else []), [40, 36])
                B_.append(toc_head(sep[0], num + (f': {ttl}' if ttl else ''), 2)); B_.extend(sep[1:]); B_.append(PAGEBREAK); continue
        if opening is not None and s_ == body[opening].rstrip():
            opening = None; topgap = LINE
            if PROFILE == 'kku' and BASMALA_USED: continue   # set on its own page already
            if BASMALA: B_.append(basmala_par()); continue
            if not META.get('title'):   # left as written: a centred line of its own, and the title after it keeps its place
                B_.append(P(inline(s_.lstrip('> ').strip() if s_.startswith('>> ') else s_, fnmap), jc='center', bold=s_.startswith('>> '), after=0)); continue
        k = indexes.directive(s_)
        if k:   # an index: its own heading, on a new page, then its entries (set in build)
            brk = '<w:pageBreakBefore/>' if nhead in BREAK_BEFORE else ''; nhead += 1
            B_.append(toc_head(P(indexes.KINDS[k], 'Heading1', extra=brk), indexes.KINDS[k], 1)); B_.append(f'INDEX_PLACEHOLDER:{k}'); started = True; continue
        if not s_.startswith(('# ', '>> ')): started = True; after_title = False
        if s_.strip() == '@toc':
            # with a cover the contents have a page of their own; an article's contents follow its title on page 1
            if PROFILE == 'kku':   # the guide's name; it lists the prelims and itself
                B_.append(toc_head(H1('قائمة المحتويات'), 'قائمة المحتويات', 1)); B_.append('TOC_PLACEHOLDER'); after_toc = True; kind = None; continue
            B_.append(H1('فهرس الموضوعات') if META.get('title') or toc_late else P('فهرس الموضوعات', 'Heading1', before=3 * LINE // 2, extra='<w:pageBreakBefore w:val="0"/>'))
            B_.append('TOC_PLACEHOLDER'); after_toc = True; continue
        if s_.strip() == '@pagebreak': B_.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>'); continue
        if s_.startswith(('### ', '## ', '# ')):
            # make.py may ask for a page break before a heading that the PDF engine left alone at the foot of a page
            brk = '<w:pageBreakBefore/>' if nhead in BREAK_BEFORE else ''; nhead += 1
        if s_.startswith(('### ', '## ')):
            if s_.startswith('### '): B_.append(P(inline(s_[4:], fnmap), 'RunHead', extra=brk))
            else: B_.append(toc_head(P(inline(s_[3:], fnmap), 'Heading2', extra=brk), s_[3:], 2))
            continue
        if s_.startswith('# '):
            if not started and not META.get('title'):
                byline = len(nonblank) > 1 and nonblank[1].startswith('>> ')
                B_.append(P(inline(s_[2:], fnmap), 'Heading1', before=topgap, after=LINE if byline else 3 * LINE,
                           extra='' if topgap == 4 * LINE else '<w:pageBreakBefore w:val="0"/>')); after_title = byline
            elif META.get('title') or after_toc: B_.append(toc_head(H1(inline(s_[2:], fnmap)), s_[2:], 1))
            else: B_.append(toc_head(P(inline(s_[2:], fnmap), 'Heading1', before=3 * LINE // 2, extra=brk or '<w:pageBreakBefore w:val="0"/>'), s_[2:], 1))
            started = True; after_toc = False; continue
        if s_.startswith('-- '): B_.append(bullet(inline(s_[3:], fnmap), lvl=1)); continue
        if s_.startswith('* '): B_.append(bullet(inline(s_[2:], fnmap), lvl=0, bold=True)); continue
        if s_.startswith('- '): B_.append(bullet(inline(s_[2:], fnmap), lvl=0, bold=False)); continue
        m = re.match(r'^([٠-٩0-9]+)\s*([-–.)])\s+(.*)$', s_)
        if m: B_.append(item(m.group(1), inline(m.group(3), fnmap), m.group(2))); continue
        if PROFILE == 'kku' and CAPTION.match(s_):   # a table's or a figure's caption, as the author wrote it: its list refers here
            text = s_[3:] if s_.startswith('>> ') else s_
            CAPS.append(('figure' if 'شكل' in CAPTION.match(s_).group(1) else 'table', re.sub(r'\*\*', '', indexes.strip_marks(text)).strip(), len(CAPS) + 1))
            par = P(inline(text, fnmap), jc='center', bold=s_.startswith('>> '), after=0, extra='<w:keepNext/>')
            B_.append(with_bookmark(par, f'_cap{len(CAPS)}', 800000 + len(CAPS))); continue
        if s_.startswith('>> '): B_.append(P(inline(s_[3:], fnmap), jc='center', bold=True, after=LINE if after_title else None)); after_title = False; started = True; continue
        if PROFILE == 'kku' and kind in ('ack', 'abs_ar'):   # the guide: 14 pt; the abstract with single spacing
            B_.append(P(inline(s_, fnmap), ind='<w:ind w:firstLine="567"/>', after=0, size=28, line=240 if kind == 'abs_ar' else None)); continue
        if PROFILE == 'kku' and kind == 'abs_en' or PROFILE == 'kku' and kind == 'refs' and len(re.findall(r'[A-Za-z]', s_)) > len(AR.findall(s_)):
            # English: left to right in Times New Roman (the abstract 12 pt with single spacing, a foreign reference 14 pt)
            ind = '<w:ind w:firstLine="567"/>' if kind == 'abs_en' else '<w:ind w:left="567" w:hanging="567"/>'
            B_.append(f'<w:p><w:pPr><w:bidi w:val="0"/><w:spacing w:after="{0 if kind == "abs_en" else 60}"' + (' w:line="240" w:lineRule="auto"' if kind == 'abs_en' else '')
                      + f'/>{ind}<w:jc w:val="{"both" if kind == "abs_en" else "left"}"/></w:pPr>' + runs(ltr_text(take_marks(expand_cites(s_))), size=28 if kind == 'abs_en' else 32, ltr_para=True) + '</w:p>')
            continue
        if PROFILE == 'kku' and kind == 'refs':   # each reference with its later lines hanging
            B_.append(P(inline(s_, fnmap), ind='<w:ind w:left="567" w:hanging="567"/>', after=60)); continue
        # ordinary paragraphs: 1 cm first-line indent, no space after; a paragraph that is only a verse is centred instead
        if STANDALONE.match(s_): B_.append(P(inline(s_, fnmap), jc='center'))
        else: B_.append(P(inline(s_, fnmap), ind='<w:ind w:firstLine="567"/>', after=0))
    flush()
    for label, n in fnmap.items():
        CUR_NOTE = n
        raw = take_marks(expand_cites(fndefs.get(label, '[حاشية مفقودة]')))
        if UNBREAKABLE.search(raw): RAGGED_NOTES.add(n)
        if len(re.findall(r'[A-Za-z]', raw)) > len(AR.findall(raw)):
            # mostly Latin: the whole note runs left to right in Times; any Arabic words in it keep Lotus
            LTR_NOTES.add(n)
            # (the Arabic signs of U+FB50–U+FEFF, ﷺ ﷻ ﴿ ﴾, count as Arabic here: Times has none of them)
            footnotes[n] = ltr_text(raw)
        else: footnotes[n] = inline(raw, {})
    CUR_NOTE = None
    return B_

def ltr_text(raw):
    """A text written mostly in Latin letters, for a left-to-right paragraph: its Arabic words keep Lotus, the rest is
    Latin (Times); bold and italic marks stay marks."""
    A_ = '\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF'
    out = ''
    for piece in re.split(r'((?<!\*)\*\*(?!\*)|⟨|⟩)', raw.replace('`', '')):
        if piece in ('**', '⟨', '⟩'): out += piece; continue
        out += ''.join(c if re.match(f'[{A_}]', c) else '`' + c + '`' for c in re.split(f'([{A_}](?:[{A_}\\s]*[{A_}])?)', piece) if c)
    return out

# ================= INDEXES =================
HINDI = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
def pages_of(es):
    """The bookmarks of a merged entry, one for each page it is on (in the PDF), in page order. Before the first layout
    every place counts once."""
    names = [f'_fn{e["note"]}' if e['note'] else f'_ix{e["id"]}' for e in es]
    if not PAGES: return list(dict.fromkeys(names))
    first = {}
    for n in names:
        if n in PAGES: first.setdefault(PAGES[n], n)
    return [first[p] for p in sorted(first)]

def entry_line(text, refs, ind=''):
    return numbered_line(text, refs, ind)

def group_head(t):
    return P(t, jc='center', bold=True, before=200, after=80, extra='<w:keepNext/>')

def index_body(k):
    """The entries of one index, grouped and in order."""
    global IX_OFF
    IX_OFF = True
    out = []
    try:
        if k == 'مصدر':   # the list of sources, in the chosen citation style
            if not CITES: raise SystemExit('@index مصدر needs a citation style (--cite) and its sources file (--sources)')
            if CITE_STYLE == 'ieee':   # numbered in the order of first citation
                listed = [(CITES[k], n + 1) for n, k in enumerate(CITE_ORDER)]
            else:
                listed = [(x, None) for x in sorted(CITES.values(), key=lambda x: indexes.order(indexes.key(cite.sort_name(x), True)))]
            for src, num in listed:
                t = cite.bib(src, CITE_STYLE, num)
                if cite.arabic(src): out.append(P(inline(t, {}), ind='<w:ind w:left="567" w:hanging="567"/>', after=60))
                else: out.append('<w:p><w:pPr><w:bidi w:val="0"/><w:spacing w:after="60"/><w:ind w:left="567" w:hanging="567"/><w:jc w:val="left"/></w:pPr>'
                                 + runs(ltr_text(t), ltr_para=True) + '</w:p>')
            return ''.join(out)
        es = [e for e in IX if e['kind'] == k]
        if k == 'آية':   # by surah, in the Mushaf's order; each verse with its ayah numbers
            merged = {}
            for e in es: merged.setdefault(e['place'], []).append(e)
            last = None
            for (sura, a, b), group in sorted(merged.items()):
                if sura != last: out.append(group_head('سورة ' + quran.SURAHS[sura - 1].replace('\u00a0', ' '))); last = sura
                num = (f'{a}' + (f'-{b}' if b != a else '')).translate(HINDI)
                out.append(entry_line(group[0]['text'] + f' ⟦[{num}]⟧', pages_of(group)))
            return ''.join(out)
        merged = {}
        for e in es:
            clean = re.sub(r'\[\^[^\]]+\]', '', e['entry']).strip()
            merged.setdefault(indexes.key(clean), (clean, []))[1].append(e)
        drop = k in indexes.DROP_AL
        def group(clean, group_es):
            if k == 'شعر': return next((e['group'] for e in group_es if e['group']), None) or indexes.rhyme(group_es[0]['text'])
            return next((e['group'] for e in group_es if e['group']), None) or indexes.letter(indexes.key(clean, drop))
        rows = sorted(merged.values(), key=lambda r: (indexes.order(indexes.key(group(*r) or '')) if k == 'شعر' else [], indexes.order(indexes.key(r[0], drop))))
        last = 0
        for clean, group_es in rows:
            g = group(clean, group_es)
            if g != last:
                name = indexes.NAMES.get((g or '').translate(indexes.FOLD), g or '')
                out.append(group_head(('قافية ' if k == 'شعر' else 'حرف ') + name)); last = g
            out.append(entry_line(inline(clean, {}), pages_of(group_es)))
        return ''.join(out)
    finally:
        IX_OFF = False

# ================= PACKAGE =================
def caplist(kind):
    es = [(t, n) for k, t, n in CAPS if k == kind]
    if not es: THESIS_NOTES.append('THESIS: ' + ('قائمة الأشكال' if kind == 'figure' else 'قائمة الجداول') + ' فارغة: لم أجد في النص عنوانًا يبدأ بـ«' + ('شكل' if kind == 'figure' else 'جدول') + ' (١-١):» ونحوه')
    return ''.join(numbered_line(t, [f'_cap{n}']) for t, n in es)

def section(kind):
    """The settings of a section of the thesis: front (no number), prelims (letters from ب), text (from ١), a part (its
    first page, the part's title, shows neither header nor number)."""
    refs = ''
    if kind != 'front':
        refs = (('<w:headerReference w:type="default" r:id="rIdH1"/>' + ('<w:headerReference w:type="first" r:id="rIdH2"/>' if kind == 'bab' else ''))
                + f'<w:footerReference w:type="default" r:id="{"rIdF3" if kind == "prelims" else "rIdF1"}"/>'
                + ('<w:footerReference w:type="first" r:id="rIdF2"/>' if kind == 'bab' else ''))
    num = {'prelims': '<w:pgNumType w:fmt="arabicAbjad" w:start="2"/>', 'text': '<w:pgNumType w:fmt="decimal" w:start="1"/>'}.get(kind, '<w:pgNumType w:fmt="decimal"/>')
    return (f'<w:sectPr>{refs}<w:footnotePr><w:numFmt w:val="decimal"/><w:numRestart w:val="eachPage"/></w:footnotePr>'
            f'<w:type w:val="nextPage"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" w:right="{MARGIN_RIGHT}" w:bottom="1417" w:left="1417" w:header="709" w:footer="567" w:gutter="0"/>'
            f'{num}<w:cols w:space="708"/>' + ('<w:titlePg/>' if kind == 'bab' else '') + '<w:bidi/></w:sectPr>')

def join_sections(parts):
    """The body with its sections: each SECT marker closes the section before it (its settings go into the last
    paragraph of that section) and opens the next; the prelims' first paragraph carries a bookmark for its page."""
    out = []; cur = 'front'; mark = None
    for b in parts:
        if b.startswith('SECT:'):
            k = len(out) - 1
            while k >= 0 and not out[k].startswith('<w:p>'): k -= 1
            last = out[k] if k >= 0 else '<w:p><w:pPr><w:bidi/></w:pPr></w:p>'
            j = last.rfind('<w:p>')   # the last paragraph of a block of several (the contents, a list…)
            tail = last[j:]
            if not tail.startswith('<w:p><w:pPr>'): tail = tail.replace('<w:p>', '<w:p><w:pPr></w:pPr>', 1)
            i = tail.index('</w:pPr>'); last = last[:j] + tail[:i] + section(cur) + tail[i:]
            if k >= 0: out[k] = last
            else: out.insert(0, last)
            cur = b[5:]; mark = '_sec1' if cur == 'prelims' else None
            continue
        if mark and b.startswith('<w:p>'): b = with_bookmark(b, mark, 799999) if '<w:pPr>' in b else b; mark = None
        out.append(b)
    return ''.join(out), section(cur)

def build(toc_entries, out):
    parts = [toc(toc_entries) if b == 'TOC_PLACEHOLDER' else index_body(b.split(':', 1)[1]) if b.startswith('INDEX_PLACEHOLDER:')
             else caplist(b.split(':', 1)[1]) if b.startswith('CAPLIST:') else b for b in B]
    if PROFILE == 'kku':
        body, last_sect = join_sections(parts)
    else:
        body = ''.join(parts)
    sect = ('<w:sectPr><w:headerReference w:type="default" r:id="rIdH1"/><w:headerReference w:type="first" r:id="rIdH2"/>'
            '<w:footerReference w:type="default" r:id="rIdF1"/><w:footerReference w:type="first" r:id="rIdF2"/>'
            '<w:footnotePr><w:numFmt w:val="decimal"/><w:numRestart w:val="eachPage"/></w:footnotePr>'
            '<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1417" w:header="709" w:footer="567" w:gutter="0"/>'
            '<w:pgNumType w:fmt="decimal"/><w:cols w:space="708"/>' + ('<w:titlePg/>' if META.get('title') or HEADER else '') + '<w:bidi/></w:sectPr>')
    if PROFILE == 'kku': sect = last_sect
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W_NS}><w:body>{body}{sect}</w:body></w:document>'
    K = PROFILE == 'kku'   # the guide: 1.5 lines, chapter headings 20 pt, sub-headings 18 pt, the header without a rule

    rpr_def = f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:eastAsia="{FONT}" w:cs="{FONT}"/><w:sz w:val="32"/><w:szCs w:val="32"/><w:lang w:val="ar-SA" w:eastAsia="en-US" w:bidi="ar-SA"/>'
    def st(sid, name, ppr='', rpr='', typ='paragraph', based='Normal', extra=''):
        b = f'<w:basedOn w:val="{based}"/>' if based else ''
        return f'<w:style w:type="{typ}" w:styleId="{sid}"><w:name w:val="{name}"/>{b}{extra}<w:qFormat/><w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>' if typ=='paragraph' else f'<w:style w:type="{typ}" w:styleId="{sid}"><w:name w:val="{name}"/>{b}<w:rPr>{rpr}</w:rPr></w:style>'
    BLD = '<w:b/><w:bCs/>'
    styles = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {W_NS}>
<w:docDefaults><w:rPrDefault><w:rPr>{rpr_def}</w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:bidi/><w:spacing w:after="120" w:line="240" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:bidi/>{'<w:spacing w:line="360" w:lineRule="auto"/>' if K else ''}<w:jc w:val="both"/></w:pPr><w:rPr><w:rtl/></w:rPr></w:style>
<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/></w:style>
{st('Heading1','heading 1','<w:keepNext/><w:pageBreakBefore/><w:spacing w:before="0" w:after="360"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/>', BLD+('<w:sz w:val="40"/><w:szCs w:val="40"/>' if K else '<w:sz w:val="36"/><w:szCs w:val="36"/>'), extra='<w:next w:val="Normal"/>')}
{st('Heading2','heading 2','<w:keepNext/><w:spacing w:before="240" w:after="0"/><w:jc w:val="both"/><w:outlineLvl w:val="1"/>', BLD + ('<w:sz w:val="36"/><w:szCs w:val="36"/>' if K else ''), extra='<w:next w:val="Normal"/>')}
{st('RunHead','Run-in Head','<w:keepNext/><w:spacing w:before="120" w:after="60"/>', BLD)}
{st('CoverTitle','Cover Title','<w:spacing w:after="240"/><w:jc w:val="center"/>', BLD+'<w:sz w:val="40"/><w:szCs w:val="40"/>')}
{st('TableText','Table Text','<w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/>', '<w:sz w:val="28"/><w:szCs w:val="28"/>')}
{st('FootnoteText','footnote text','<w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="340" w:hanging="340"/><w:jc w:val="both"/>', '<w:sz w:val="26"/><w:szCs w:val="26"/>')}
{st('FootnoteReference','footnote reference', rpr='<w:vertAlign w:val="superscript"/>', typ='character', based='DefaultParagraphFont')}
{st('Footer','footer','<w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/>', '<w:sz w:val="28"/><w:szCs w:val="28"/>')}
{st('Header','header',('' if K else '<w:pBdr><w:bottom w:val="single" w:sz="4" w:space="4" w:color="000000"/></w:pBdr>') + '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/>', '<w:sz w:val="26"/><w:szCs w:val="26"/>')}
</w:styles>'''

    numbering = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering {W_NS}>
<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>
<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="397" w:hanging="397"/></w:pPr><w:rPr><w:rFonts w:ascii="{FALLBACK}" w:hAnsi="{FALLBACK}" w:cs="{FALLBACK}"/></w:rPr></w:lvl>
<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="o"/><w:lvlJc w:val="left"/><w:pPr><w:ind w:left="964" w:hanging="397"/></w:pPr><w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:lvl>
</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>'''

    # The number in the note sits on the line at the margin, not raised, and the text hangs clear of it. A Latin note
    # has its number in Western digits, «(1)», set as the note's own text is (Times, marked English): left to the
    # paragraph's defaults, one program draws it ١ and another 1.
    def fnpara(n, t):
        ltr = n in LTR_NOTES; m = '' if ltr else RLM
        num = '<w:rPr>' + (f'<w:rFonts w:ascii="{FALLBACK}" w:hAnsi="{FALLBACK}" w:cs="{FALLBACK}"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:rtl w:val="0"/><w:lang w:val="en-US"/>'
                           if ltr else '<w:sz w:val="26"/><w:szCs w:val="26"/><w:rtl/>') + '</w:rPr>'
        open_p = f'<w:r>{num}<w:t>{m}({m}</w:t></w:r>' if VARIANT == 'word' else ''
        close_p = f'<w:r>{num}<w:t>{m}){m}</w:t></w:r>' if VARIANT == 'word' else ''
        # in a right-to-left paragraph Word's «left» means the start side (the right)
        ppr = '<w:pStyle w:val="FootnoteText"/>' + ('<w:bidi w:val="0"/><w:jc w:val="left"/>' if ltr
                                                    else '<w:bidi/>' + ('<w:jc w:val="left"/>' if n in RAGGED_NOTES else ''))
        return (f'<w:p><w:pPr>{ppr}</w:pPr>{open_p}<w:r>{num}<w:footnoteRef/></w:r>{close_p}'
                f'<w:r>{num}<w:tab/></w:r>{runs(t, size=26, ltr_para=ltr)}</w:p>')
    fns = ''.join(f'<w:footnote w:id="{n}">{fnpara(n, t)}</w:footnote>' for n, t in sorted(footnotes.items()))
    footnotes_xml = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:footnotes {W_NS}>'
        '<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr><w:bidi/><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:separator/></w:r></w:p></w:footnote>'
        '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr><w:bidi/><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
        f'{fns}</w:footnotes>')

    # the running header is on request only (@header): the title of the work, centred over a thin rule, on every page
    # but the first (the cover, or an article's own title); otherwise the header parts stay empty
    empty_h = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {W_NS}><w:p><w:pPr><w:bidi/></w:pPr></w:p></w:hdr>'
    empty_f = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {W_NS}><w:p><w:pPr><w:bidi/></w:pPr></w:p></w:ftr>'
    r = '<w:rPr><w:rtl/></w:rPr>'; MC = 'http://schemas.openxmlformats.org/markup-compatibility/2006'
    def fld(parts, result=None):   # a Word field; parts are instruction text or nested fields
        x = f'<w:r>{r}<w:fldChar w:fldCharType="begin"/></w:r>'
        for part in parts: x += part if part.startswith('<w:r>') else f'<w:r>{r}<w:instrText xml:space="preserve">{part}</w:instrText></w:r>'
        if result: x += f'<w:r>{r}<w:fldChar w:fldCharType="separate"/></w:r><w:r>{r}<w:t>{result}</w:t></w:r>'
        return x + f'<w:r>{r}<w:fldChar w:fldCharType="end"/></w:r>'
    if VARIANT == 'word':
        # Word has no Arabic-Indic number format and shapes automatic digits by the reader's own settings, so the
        # number is spelled out digit by digit: nested IF fields pick each digit of PAGE as a literal ٠…٩ (up to 999).
        def digit(div):
            x = '٩'
            for d in range(8, -1, -1):
                x = fld([' IF ', fld([' = MOD(INT(', fld([' PAGE ']), f'/{div}),10) ']), f' = {d} "{"٠١٢٣٤٥٦٧٨٩"[d]}" "', x, '" '])
            return x
        number = (fld([' IF ', fld([' PAGE ']), ' > 99 "', digit(100), '" "" ']) + fld([' IF ', fld([' PAGE ']), ' > 9 "', digit(10), '" "" ']) + digit(1))
        # Programs that do not evaluate nested fields (LibreOffice prints every inner PAGE) get a plain PAGE field instead
        number = (f'<mc:AlternateContent xmlns:mc="{MC}"><mc:Choice xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" Requires="w15">{number}</mc:Choice>'
                  f'<mc:Fallback>{fld([" PAGE "], "٢")}</mc:Fallback></mc:AlternateContent>')
    else:
        number = fld([' PAGE '], '٢')   # LibreOffice (the PDF) shows it in Arabic-Indic digits by itself
    ftr1 = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {W_NS}><w:p><w:pPr><w:pStyle w:val="Footer"/><w:bidi/></w:pPr>{number}</w:p></w:ftr>'
    hdr1 = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {W_NS}><w:p><w:pPr><w:pStyle w:val="Header"/><w:bidi/></w:pPr>'
            f'{runs(inline(HEADER, {}), size=26)}</w:p></w:hdr>') if HEADER else None
    # with no cover, the first page still shows its number when it has no header (an article's first page)
    ftr2 = ftr1 if HEADER and not META.get('title') and PROFILE != 'kku' else None
    # the prelims of a thesis: their page number in letters (the section's own format)
    ftr3 = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr {W_NS}><w:p><w:pPr><w:pStyle w:val="Footer"/><w:bidi/></w:pPr>{fld([" PAGE "], "ب")}</w:p></w:ftr>'

    settings = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {W_NS}>
{'<w:embedTrueTypeFonts/>' if QURAN_USED else ''}{'<w:updateFields w:val="true"/>' if any(b == 'TOC_PLACEHOLDER' or b.startswith('INDEX_PLACEHOLDER:') for b in B) else ''}<w:defaultTabStop w:val="720"/><w:characterSpacingControl w:val="doNotCompress"/>
<w:footnotePr><w:numFmt w:val="decimal"/><w:numRestart w:val="eachPage"/><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr>
<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>
<w:themeFontLang w:val="en-US" w:bidi="ar-SA"/></w:settings>'''

    # embedded, obfuscated fonts
    def obf(path, key_guid):
        data = bytearray(open(path, 'rb').read())
        hx = key_guid.strip('{}').replace('-', '')
        key = [int(hx[i:i+2], 16) for i in range(0, 32, 2)][::-1]
        for i in range(32): data[i] ^= key[i % 16]
        return bytes(data)
    # Lotus Lotfi is not embedded: its embedding permission (preview & print) makes Word open the file read-only
    # for anyone who does not have the font, and Word for Mac ignores embedded fonts anyway. make.py puts the font
    # files beside the output instead. The Quran font allows embedding and stays embedded.
    g1 = '{' + str(uuid.uuid4()).upper() + '}'
    qfont = (f'<w:font w:name="{quran.FONT}"><w:charset w:val="B2"/><w:family w:val="auto"/><w:pitch w:val="variable"/>'
             f'<w:embedRegular r:id="rIdFont1" w:fontKey="{g1}"/></w:font>') if QURAN_USED else ''
    qrel = '<Relationship Id="rIdFont1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/font" Target="fonts/font1.odttf"/>' if QURAN_USED else ''
    fonttable = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:fonts {W_NS}>'
        f'<w:font w:name="{FONT}"><w:charset w:val="B2"/><w:family w:val="roman"/><w:pitch w:val="variable"/></w:font>{qfont}'
        + (f'<w:font w:name="{LOTUS}"><w:charset w:val="B2"/><w:family w:val="roman"/><w:pitch w:val="variable"/></w:font>' if FONT != LOTUS and BASMALA_USED else '') +
        f'<w:font w:name="{FALLBACK}"><w:charset w:val="00"/><w:family w:val="roman"/><w:pitch w:val="variable"/></w:font>'
        '<w:font w:name="Courier New"><w:charset w:val="00"/><w:family w:val="modern"/><w:pitch w:val="fixed"/></w:font></w:fonts>')
    fonttable_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + qrel + '</Relationships>')
    R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rIdS" Type="{R}styles" Target="styles.xml"/><Relationship Id="rIdSet" Type="{R}settings" Target="settings.xml"/>'
        f'<Relationship Id="rIdFT" Type="{R}fontTable" Target="fontTable.xml"/><Relationship Id="rIdN" Type="{R}numbering" Target="numbering.xml"/>'
        f'<Relationship Id="rIdFn" Type="{R}footnotes" Target="footnotes.xml"/>'
        f'<Relationship Id="rIdH1" Type="{R}header" Target="header1.xml"/><Relationship Id="rIdH2" Type="{R}header" Target="header2.xml"/>'
        f'<Relationship Id="rIdF1" Type="{R}footer" Target="footer1.xml"/><Relationship Id="rIdF2" Type="{R}footer" Target="footer2.xml"/>'
        f'<Relationship Id="rIdF3" Type="{R}footer" Target="footer3.xml"/>'
        + (f'<Relationship Id="rIdLogo" Type="{R}image" Target="media/logo.{LOGO[1]}"/>' if LOGO else '') + '</Relationships>')
    WM = 'application/vnd.openxmlformats-officedocument.wordprocessingml.'
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="odttf" ContentType="application/vnd.openxmlformats-officedocument.obfuscatedFont"/>'
        '<Default Extension="png" ContentType="image/png"/><Default Extension="jpeg" ContentType="image/jpeg"/>'
        f'<Override PartName="/word/document.xml" ContentType="{WM}document.main+xml"/><Override PartName="/word/styles.xml" ContentType="{WM}styles+xml"/>'
        f'<Override PartName="/word/settings.xml" ContentType="{WM}settings+xml"/><Override PartName="/word/fontTable.xml" ContentType="{WM}fontTable+xml"/>'
        f'<Override PartName="/word/numbering.xml" ContentType="{WM}numbering+xml"/><Override PartName="/word/footnotes.xml" ContentType="{WM}footnotes+xml"/>'
        f'<Override PartName="/word/header1.xml" ContentType="{WM}header+xml"/><Override PartName="/word/header2.xml" ContentType="{WM}header+xml"/>'
        f'<Override PartName="/word/footer1.xml" ContentType="{WM}footer+xml"/><Override PartName="/word/footer2.xml" ContentType="{WM}footer+xml"/>'
        f'<Override PartName="/word/footer3.xml" ContentType="{WM}footer+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:title>'+escape(META.get('title',''))+'</dc:title><dc:creator>'+escape(META.get('author',''))+'</dc:creator><dc:language>ar-SA</dc:language></cp:coreProperties>')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', rels); z.writestr('docProps/core.xml', core)
        z.writestr('word/document.xml', doc); z.writestr('word/_rels/document.xml.rels', doc_rels)
        z.writestr('word/styles.xml', styles); z.writestr('word/settings.xml', settings); z.writestr('word/numbering.xml', numbering)
        z.writestr('word/footnotes.xml', footnotes_xml); z.writestr('word/fontTable.xml', fonttable); z.writestr('word/_rels/fontTable.xml.rels', fonttable_rels)
        if QURAN_USED: z.writestr('word/fonts/font1.odttf', obf(quran.FONT_FILE, g1))
        z.writestr('word/header1.xml', hdr1 or empty_h); z.writestr('word/header2.xml', empty_h)
        z.writestr('word/footer1.xml', ftr1); z.writestr('word/footer2.xml', ftr2 or empty_f); z.writestr('word/footer3.xml', ftr3)
        if LOGO: z.writestr(f'word/media/logo.{LOGO[1]}', LOGO[0])


import sys, json
if __name__ == '__main__':
    # usage: typeset.py input.md out.docx variant(word|lo) [toc.json] [--uthmani] [--break-before=N,N] [--font=traditional]
    #        [--basmala=N] [--cite=STYLE --sources=FILE] [--pages=FILE]
    opt = lambda name: next((a.split('=', 1)[1] for a in sys.argv if a.startswith(f'--{name}=')), None)
    UTHMANI = '--uthmani' in sys.argv
    BREAK_BEFORE = {int(x) for x in (opt('break-before') or '').split(',') if x}
    PROFILE = opt('profile') or 'paper'
    if PROFILE not in ('paper', 'kku'): raise SystemExit('--profile: paper | kku')
    if PROFILE == 'kku':   # the guide: Traditional Arabic, 3.5 cm on the right
        MARGIN_RIGHT = 1984; TEXTW = 11906 - 1984 - 1417
    use_font('traditional' if PROFILE == 'kku' else (opt('font') or 'lotus'))
    BASMALA = int(opt('basmala')) if opt('basmala') else None
    if BASMALA is not None and not 1 <= BASMALA <= len(indexes.SHAPES): raise SystemExit(f'--basmala: 1 to {len(indexes.SHAPES)}')
    CITE_STYLE = (opt('cite') or '').lower() or None
    if CITE_STYLE and CITE_STYLE not in cite.STYLES: raise SystemExit('--cite: ' + ' | '.join(cite.STYLES))
    if CITE_STYLE: CITES = cite.load(opt('sources')) if opt('sources') else {}
    if opt('pages') and os.path.exists(opt('pages')): PAGES = json.load(open(opt('pages')))
    argv = [a for a in sys.argv if not a.startswith('--')]
    VARIANT = argv[3]
    B = parse(argv[1])
    toc_entries = json.load(open(argv[4])) if len(argv) > 4 else []
    build(toc_entries, argv[2])
    if VARIANT == 'word':   # the reports, once per build; the QURAN and INDEX lines are in Arabic: they go into the reply as they are
        if UTHMANI:
            kept = [r for r in quran.REPORT if not r[0]]
            print(f'QURAN: عدد الآيات المحوَّلة إلى الرسم العثماني: {len(quran.REPORT) - len(kept)}، وعدد ما بقي كما كتبه الكاتب: {len(kept)}'.translate(quran.HINDI))
            for done, verse_, note in kept:
                print('QURAN بقيت كما كُتبت: ﴿' + (verse_ if len(verse_) < 60 else verse_[:57] + '…') + '﴾ — ' + note)
        for verse_, why in IX_UNPLACED:
            print('INDEX لم تدخل فهرس الآيات: ﴿' + (verse_ if len(verse_) < 60 else verse_[:57] + '…') + '﴾ — ' + why)
        for k in sorted(IX_WANT - {'آية', 'مصدر'}):
            if not any(e['kind'] == k for e in IX): print(f'INDEX: no entry was marked for {k} — its index is empty')
        if IX_UNKNOWN: print('INDEX: unknown kind of mark (its words kept, the mark dropped): ' + ', '.join(sorted(set(IX_UNKNOWN))))
        if SORT_KEPT: print('SORT: a list the author numbered was left in its order (renumbering would change the text)')
        if CITE_STYLE:
            for line in cite.report({k: v for k, v in CITES.items() if k in CITED}, CITE_STYLE): print(line)
        if BASMALA and not BASMALA_USED: print('BASMALA: the text does not open with the basmala — nothing was set')
        if PROFILE == 'kku':
            words = {}; cur = None
            for line in open(argv[1], encoding='utf-8').read().split('\n'):
                t = line.strip()
                if t.startswith('# '): cur = PRELIM.get(title_key(t[2:])); continue
                if t and not t.startswith(('@', '[^')) and cur in ('abs_ar', 'abs_en'): words[cur] = words.get(cur, 0) + len(t.split())
            for k, n in words.items():
                if n > 300: THESIS_NOTES.append(f'THESIS: {"المستخلص العربي" if k == "abs_ar" else "المستخلص الإنجليزي"} {n} كلمة، والدليل يحدّه بـ٣٠٠ كلمة'.translate(HINDI))
            ack = next((i for i, (t, l, n) in enumerate(TOC_ENTRIES) if PRELIM.get(title_key(t)) == 'ack'), None)
            if PAGES and ack is not None and ack + 1 < len(TOC_ENTRIES):
                a, b = PAGES.get(TOC_ENTRIES[ack][2]), PAGES.get(TOC_ENTRIES[ack + 1][2])
                if a and b and b - a > 1: THESIS_NOTES.append('THESIS: صفحة الشكر والتقدير تزيد على صفحة، والدليل يحدّها بصفحة واحدة')
            for n in dict.fromkeys(THESIS_NOTES): print(n)
        if PAGES and 'TOC_PLACEHOLDER' in B:
            lost = [t for t, lvl, k in TOC_ENTRIES if k not in PAGES]
            if lost: print('TOC: page not found for:', lost)

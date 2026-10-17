import re, os, zipfile, uuid, unicodedata
import quran
from xml.sax.saxutils import escape

FONT = "_Lotus Lotfi"
import os as _os
HERE=_os.path.dirname(_os.path.abspath(__file__))
REG = _os.path.join(HERE,"..","assets","fonts","_LotusLotfi-Regular.ttf")
BOLD = _os.path.join(HERE,"..","assets","fonts","_LotusLotfi-Bold.ttf")
RLM = "\u200f"
TEXTW = 9072  # A4 width 11906 - 2*1417

W_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')

# ---------- inline markup ----------
# **bold**   ⟦small⟧ (verse refs, death dates)   ⟪verse in Uthmani script⟫   ^N footnote   `latin`
from fontTools.ttLib import TTFont
CMAP = set(TTFont(REG).getBestCmap())
FALLBACK = "Times New Roman"
# Honorific signs and ligature words (U+FD00–U+FDFF: ﷻ ﷽ ﵁ …) that Lotus does not have at their standard code points
# are set in Noto Naskh Arabic (assets/symbols, SIL OFL), each character as the author wrote it.
SYMBOL_FONT = "Noto Naskh Arabic"
SYMBOL_FILE = _os.path.join(HERE,"..","assets","symbols","NotoNaskhArabic-Regular.ttf")
SYMBOLS = {c for c in TTFont(SYMBOL_FILE).getBestCmap() if 0xFD00 <= c <= 0xFDFF} - CMAP
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
TOK = re.compile(r'(\*\*|⟦|⟧|⟪|⟫|⟬|⟭|\^\d+|`[^`]*`)')
footnotes = {}
LTR_NOTES = set()   # footnotes written mostly in Latin letters: set left-to-right in Times
RAGGED_NOTES = set()   # footnotes holding a word that cannot break (a link…): not justified, or the line before it is stretched
UNBREAKABLE = re.compile(r'\S*://\S+|\bwww\.\S+|\S{30,}')

def runs(text, base_bold=False, size=None, ltr_para=False):
    out = []; bold = base_bold; small = False; verse = False; noproof = False
    for part in TOK.split(text):
        if not part: continue
        if part == '**': bold = not bold; continue
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
            out.append(f'<w:r><w:rPr>{sup}</w:rPr><w:t>\u200f(\u200f</w:t></w:r>')
            out.append(f'<w:r><w:rPr>{sup}</w:rPr><w:footnoteReference w:id="{n}"/></w:r>')
            out.append(f'<w:r><w:rPr>{sup}</w:rPr><w:t>\u200f)\u200f</w:t></w:r>')
            continue
        ltr = part.startswith('`')
        if ltr: part = part[1:-1]
        rp = ''
        if bold: rp += '<w:b/><w:bCs/>'
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

def P(text='', style=None, jc=None, before=None, after=None, ind=None, numid=None, lvl=0, bold=False, size=None, extra=''):
    pp = ''
    if style: pp += f'<w:pStyle w:val="{style}"/>'
    if numid: pp += f'<w:numPr><w:ilvl w:val="{lvl}"/><w:numId w:val="{numid}"/></w:numPr>'
    pp += extra
    pp += '<w:bidi/>'
    if before is not None or after is not None:
        pp += '<w:spacing' + (f' w:before="{before}"' if before is not None else '') + (f' w:after="{after}"' if after is not None else '') + '/>'
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

def toc(entries):
    out = []
    for t, pg, lvl in entries:
        ind = '<w:ind w:left="567"/>' if lvl == 2 else ''   # the start side (see the note on hanging indents above)
        tabs = f'<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{TEXTW}"/></w:tabs>'
        out.append(P(f'{t}\t{pg}', jc="right", after=40, ind=ind, bold=(lvl==1), extra=tabs))
    return ''.join(out)


# ================= PARSER (markdown-ish input) =================
LATIN = re.compile(r'[A-Za-z][A-Za-z0-9 .,:;/_\-@&+#%=?~]*[A-Za-z0-9/]|[A-Za-z]')
VREF = re.compile(r'(\[[^\[\]\^]+?:\s*[٠-٩0-9\-–، ]+\])')
DEATH = re.compile(r'\((ت\s*:\s*)([٠-٩0-9]+(?:هـ|ه)?)\)')
# Short references in () or [] that hold a number — (ت: ٤٦٨) (٢/ ٦٥٣) (١٢/٢٨٣) [البقرة: ١٤٣] — must never
# split across lines. Glue them with invisible aids only: spaces become no-break spaces and a word joiner
# goes between parts (never between two Arabic letters, so shaping is untouched). Visible text is unchanged.
SHORTREF = re.compile(r'[\(\[][^()\[\]\n⟦⟧⟪⟫⟬⟭`^]{1,28}[\)\]]')
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
def uthmani(m):
    global QURAN_USED
    op, v, cl = [g for g in m.groups() if g is not None]
    before = bare(m.string[:m.start()])
    if op != '﴿' and not SAYS.search(before): return m.group(0)
    ref = None; r = REF.match(m.string, m.end()); n = NAMED.search(before)
    if r and (r.group(2) or quran.surah(r.group(1))): ref = (r.group(1), r.group(2))
    elif n: ref = next(((x, None) for x in (n.group(1) + (n.group(2) or ''), n.group(1)) if quran.surah(x)), None)
    u = quran.convert(v, ref)
    if u is None: return m.group(0)
    QURAN_USED = True
    # the marks around the verse are marked no-proof too: Word checks «﴿word» as one word across the run boundary
    return '⟬' + op + '⟭' + v[:len(v) - len(v.lstrip())] + '⟪' + u + '⟫' + v[len(v.rstrip()):] + '⟬' + cl + '⟭'
def inline(t, fnmap):
    if UTHMANI: t = QUOTED.sub(uthmani, VERSE.sub(uthmani, t))
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
def parse(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    B_ = []; fnmap = {}; fndefs = {}
    i = 0
    if lines and lines[0].strip() == '---':
        i = 1; META['lines'] = []
        while lines[i].strip() != '---':
            k, _, v = lines[i].partition(':')
            k = k.strip(); v = v.strip()
            if k == 'line': META['lines'].append(v)
            elif k: META[k] = v
            i += 1
        i += 1
    body = []
    for ln in lines[i:]:
        m = re.match(r'^\[\^([^\]]+)\]:\s*(.*)$', ln)
        if m: fndefs[m.group(1)] = m.group(2)
        else: body.append(ln)
    if META.get('title'):
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
    nonblank = [l.rstrip() for l in body if l.strip()]
    cover_open = bool(META.get('title'))
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
        if not s_.startswith(('# ', '>> ')): started = True; after_title = False
        if s_.strip() == '@toc':
            # with a cover the contents have a page of their own; an article's contents follow its title on page 1
            B_.append(H1('فهرس الموضوعات') if META.get('title') else P('فهرس الموضوعات', 'Heading1', before=3 * LINE // 2, extra='<w:pageBreakBefore w:val="0"/>'))
            B_.append('TOC_PLACEHOLDER'); after_toc = True; continue
        if s_.strip() == '@pagebreak': B_.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>'); continue
        if s_.startswith(('### ', '## ', '# ')):
            # make.py may ask for a page break before a heading that the PDF engine left alone at the foot of a page
            brk = '<w:pageBreakBefore/>' if nhead in BREAK_BEFORE else ''; nhead += 1
        if s_.startswith(('### ', '## ')):
            if s_.startswith('### '): B_.append(P(inline(s_[4:], fnmap), 'RunHead', extra=brk))
            else: B_.append(P(inline(s_[3:], fnmap), 'Heading2', extra=brk))
            continue
        if s_.startswith('# '):
            if not started and not META.get('title'):
                byline = len(nonblank) > 1 and nonblank[1].startswith('>> ')
                B_.append(P(inline(s_[2:], fnmap), 'Heading1', before=4 * LINE, after=LINE if byline else 3 * LINE)); after_title = byline
            elif META.get('title') or after_toc: B_.append(H1(inline(s_[2:], fnmap)))
            else: B_.append(P(inline(s_[2:], fnmap), 'Heading1', before=3 * LINE // 2, extra=brk or '<w:pageBreakBefore w:val="0"/>'))
            started = True; after_toc = False; continue
        if s_.startswith('-- '): B_.append(bullet(inline(s_[3:], fnmap), lvl=1)); continue
        if s_.startswith('* '): B_.append(bullet(inline(s_[2:], fnmap), lvl=0, bold=True)); continue
        if s_.startswith('- '): B_.append(bullet(inline(s_[2:], fnmap), lvl=0, bold=False)); continue
        m = re.match(r'^([٠-٩0-9]+)\s*([-–.)])\s+(.*)$', s_)
        if m: B_.append(item(m.group(1), inline(m.group(3), fnmap), m.group(2))); continue
        if s_.startswith('>> '): B_.append(P(inline(s_[3:], fnmap), jc='center', bold=True, after=LINE if after_title else None)); after_title = False; started = True; continue
        # ordinary paragraphs: 1 cm first-line indent, no space after; a paragraph that is only a verse is centred instead
        if STANDALONE.match(s_): B_.append(P(inline(s_, fnmap), jc='center'))
        else: B_.append(P(inline(s_, fnmap), ind='<w:ind w:firstLine="567"/>', after=0))
    flush()
    for label, n in fnmap.items():
        raw = fndefs.get(label, '[حاشية مفقودة]')
        if UNBREAKABLE.search(raw): RAGGED_NOTES.add(n)
        if len(re.findall(r'[A-Za-z]', raw)) > len(AR.findall(raw)):
            # mostly Latin: the whole note runs left to right in Times; any Arabic words in it keep Lotus
            LTR_NOTES.add(n)
            # (the Arabic signs of U+FB50–U+FEFF, ﷺ ﷻ ﴿ ﴾, count as Arabic here: Times has none of them)
            A_ = '\u0600-\u06FF\uFB50-\uFDFF\uFE70-\uFEFF'
            footnotes[n] = ''.join(c if re.match(f'[{A_}]', c) else '`' + c + '`' for c in re.split(f'([{A_}](?:[{A_}\\s]*[{A_}])?)', raw.replace('`', '')) if c)
        else: footnotes[n] = inline(raw, {})
    return B_

# ================= PACKAGE =================
def build(toc_entries, out):
    body = ''.join(toc(toc_entries) if b == 'TOC_PLACEHOLDER' else b for b in B)
    sect = ('<w:sectPr><w:headerReference w:type="default" r:id="rIdH1"/><w:headerReference w:type="first" r:id="rIdH2"/>'
            '<w:footerReference w:type="default" r:id="rIdF1"/><w:footerReference w:type="first" r:id="rIdF2"/>'
            '<w:footnotePr><w:numFmt w:val="decimal"/><w:numRestart w:val="eachPage"/></w:footnotePr>'
            '<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1417" w:header="709" w:footer="567" w:gutter="0"/>'
            '<w:pgNumType w:fmt="decimal"/><w:cols w:space="708"/>' + ('<w:titlePg/>' if META.get('title') else '') + '<w:bidi/></w:sectPr>')
    doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W_NS}><w:body>{body}{sect}</w:body></w:document>'

    rpr_def = f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:eastAsia="{FONT}" w:cs="{FONT}"/><w:sz w:val="32"/><w:szCs w:val="32"/><w:lang w:val="ar-SA" w:eastAsia="en-US" w:bidi="ar-SA"/>'
    def st(sid, name, ppr='', rpr='', typ='paragraph', based='Normal', extra=''):
        b = f'<w:basedOn w:val="{based}"/>' if based else ''
        return f'<w:style w:type="{typ}" w:styleId="{sid}"><w:name w:val="{name}"/>{b}{extra}<w:qFormat/><w:pPr>{ppr}</w:pPr><w:rPr>{rpr}</w:rPr></w:style>' if typ=='paragraph' else f'<w:style w:type="{typ}" w:styleId="{sid}"><w:name w:val="{name}"/>{b}<w:rPr>{rpr}</w:rPr></w:style>'
    BLD = '<w:b/><w:bCs/>'
    styles = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {W_NS}>
<w:docDefaults><w:rPrDefault><w:rPr>{rpr_def}</w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:bidi/><w:spacing w:after="120" w:line="240" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:bidi/><w:jc w:val="both"/></w:pPr><w:rPr><w:rtl/></w:rPr></w:style>
<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/></w:style>
{st('Heading1','heading 1','<w:keepNext/><w:pageBreakBefore/><w:spacing w:before="0" w:after="360"/><w:jc w:val="center"/><w:outlineLvl w:val="0"/>', BLD+'<w:sz w:val="36"/><w:szCs w:val="36"/>', extra='<w:next w:val="Normal"/>')}
{st('Heading2','heading 2','<w:keepNext/><w:spacing w:before="240" w:after="0"/><w:jc w:val="both"/><w:outlineLvl w:val="1"/>', BLD, extra='<w:next w:val="Normal"/>')}
{st('RunHead','Run-in Head','<w:keepNext/><w:spacing w:before="120" w:after="60"/>', BLD)}
{st('CoverTitle','Cover Title','<w:spacing w:after="240"/><w:jc w:val="center"/>', BLD+'<w:sz w:val="40"/><w:szCs w:val="40"/>')}
{st('TableText','Table Text','<w:spacing w:before="20" w:after="20"/>', '<w:sz w:val="28"/><w:szCs w:val="28"/>')}
{st('FootnoteText','footnote text','<w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="340" w:hanging="340"/><w:jc w:val="both"/>', '<w:sz w:val="26"/><w:szCs w:val="26"/>')}
{st('FootnoteReference','footnote reference', rpr='<w:vertAlign w:val="superscript"/>', typ='character', based='DefaultParagraphFont')}
{st('Footer','footer','<w:spacing w:after="0"/><w:jc w:val="center"/>', '<w:sz w:val="28"/><w:szCs w:val="28"/>')}
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

    # no running header, by design; the header parts stay empty
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

    settings = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {W_NS}>
{'<w:embedTrueTypeFonts/>' if QURAN_USED else ''}<w:defaultTabStop w:val="720"/><w:characterSpacingControl w:val="doNotCompress"/>
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
        f'<w:font w:name="{FALLBACK}"><w:charset w:val="00"/><w:family w:val="roman"/><w:pitch w:val="variable"/></w:font>'
        '<w:font w:name="Courier New"><w:charset w:val="00"/><w:family w:val="modern"/><w:pitch w:val="fixed"/></w:font></w:fonts>')
    fonttable_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + qrel + '</Relationships>')
    R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
    doc_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rIdS" Type="{R}styles" Target="styles.xml"/><Relationship Id="rIdSet" Type="{R}settings" Target="settings.xml"/>'
        f'<Relationship Id="rIdFT" Type="{R}fontTable" Target="fontTable.xml"/><Relationship Id="rIdN" Type="{R}numbering" Target="numbering.xml"/>'
        f'<Relationship Id="rIdFn" Type="{R}footnotes" Target="footnotes.xml"/>'
        f'<Relationship Id="rIdH1" Type="{R}header" Target="header1.xml"/><Relationship Id="rIdH2" Type="{R}header" Target="header2.xml"/>'
        f'<Relationship Id="rIdF1" Type="{R}footer" Target="footer1.xml"/><Relationship Id="rIdF2" Type="{R}footer" Target="footer2.xml"/></Relationships>')
    WM = 'application/vnd.openxmlformats-officedocument.wordprocessingml.'
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
        '<Default Extension="odttf" ContentType="application/vnd.openxmlformats-officedocument.obfuscatedFont"/>'
        f'<Override PartName="/word/document.xml" ContentType="{WM}document.main+xml"/><Override PartName="/word/styles.xml" ContentType="{WM}styles+xml"/>'
        f'<Override PartName="/word/settings.xml" ContentType="{WM}settings+xml"/><Override PartName="/word/fontTable.xml" ContentType="{WM}fontTable+xml"/>'
        f'<Override PartName="/word/numbering.xml" ContentType="{WM}numbering+xml"/><Override PartName="/word/footnotes.xml" ContentType="{WM}footnotes+xml"/>'
        f'<Override PartName="/word/header1.xml" ContentType="{WM}header+xml"/><Override PartName="/word/header2.xml" ContentType="{WM}header+xml"/>'
        f'<Override PartName="/word/footer1.xml" ContentType="{WM}footer+xml"/><Override PartName="/word/footer2.xml" ContentType="{WM}footer+xml"/>'
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
        z.writestr('word/header1.xml', empty_h); z.writestr('word/header2.xml', empty_h)
        z.writestr('word/footer1.xml', ftr1); z.writestr('word/footer2.xml', empty_f)


import sys, json
if __name__ == '__main__':
    # usage: typeset.py input.md out.docx variant(word|lo) [toc.json] [--uthmani] [--break-before=N,N]
    UTHMANI = '--uthmani' in sys.argv
    BREAK_BEFORE = {int(x) for a in sys.argv if a.startswith('--break-before=') for x in a.split('=')[1].split(',') if x}
    argv = [a for a in sys.argv if a != '--uthmani' and not a.startswith('--break-before=')]
    VARIANT = argv[3]
    B = parse(argv[1])
    toc_entries = json.load(open(argv[4])) if len(argv) > 4 else []
    build(toc_entries, argv[2])
    if UTHMANI and VARIANT == 'word':   # one report per build, in Arabic: it goes into the reply to the user as it is
        kept = [r for r in quran.REPORT if not r[0]]
        print(f'QURAN: عدد الآيات المحوَّلة إلى الرسم العثماني: {len(quran.REPORT) - len(kept)}، وعدد ما بقي كما كتبه الكاتب: {len(kept)}'.translate(quran.HINDI))
        for done, verse, note in kept:
            print('QURAN بقيت كما كُتبت: ﴿' + (verse if len(verse) < 60 else verse[:57] + '…') + '﴾ — ' + note)

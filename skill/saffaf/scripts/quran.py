"""Uthmani-script verses (Hafs). What the author marked as a verse is recognised by its letters alone — every vowel
mark the author wrote is ignored — word by word against the imlāʾī Quran text; the same words are then taken from the
Uthmani text, with the Mushaf's own marks. Anything that is not recognised, or whose place cannot be settled, is left
exactly as the author wrote it and listed in REPORT."""
import os, re, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
QDIR = os.path.join(HERE, '..', 'assets', 'quran')
FONT = 'KFGQPC HAFS Uthmanic Script'
FONT_FILE = os.path.join(QDIR, 'UthmanicHafs_V22.ttf')
REPORT = []   # (converted: bool, verse as written, why it was left as written — in Arabic, for the reply)

SURAHS = ('الفاتحة البقرة آل_عمران النساء المائدة الأنعام الأعراف الأنفال التوبة يونس هود يوسف الرعد إبراهيم الحجر النحل '
          'الإسراء الكهف مريم طه الأنبياء الحج المؤمنون النور الفرقان الشعراء النمل القصص العنكبوت الروم لقمان السجدة '
          'الأحزاب سبأ فاطر يس الصافات ص الزمر غافر فصلت الشورى الزخرف الدخان الجاثية الأحقاف محمد الفتح الحجرات ق '
          'الذاريات الطور النجم القمر الرحمن الواقعة الحديد المجادلة الحشر الممتحنة الصف الجمعة المنافقون التغابن الطلاق '
          'التحريم الملك القلم الحاقة المعارج نوح الجن المزمل المدثر القيامة الإنسان المرسلات النبأ النازعات عبس التكوير '
          'الانفطار المطففين الانشقاق البروج الطارق الأعلى الغاشية الفجر البلد الشمس الليل الضحى الشرح التين العلق القدر '
          'البينة الزلزلة العاديات القارعة التكاثر العصر الهمزة الفيل قريش الماعون الكوثر الكافرون النصر المسد الإخلاص '
          'الفلق الناس').replace('_', ' ').split(' ')
ALIASES = {'براءة': 9, 'بني إسرائيل': 17, 'الملائكة': 35, 'المؤمن': 40, 'حم السجدة': 41, 'القتال': 47, 'الدهر': 76,
           'الانشراح': 94, 'اللهب': 111, 'تبت': 111}
DIG = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

def _name(s):  # surah names are looked up leniently (they are a reference, not Quran text)
    s = ''.join(c for c in s if not unicodedata.combining(c)).replace(' ', ' ')
    s = re.sub(r'^\s*سورة\s+', '', s).translate(str.maketrans('أإآٱةى', 'ااااهي'))
    return ' '.join(s.split())
NAMES = {_name(n): i + 1 for i, n in enumerate(SURAHS)}
NAMES.update({_name(n): i for n, i in ALIASES.items()})

# Word division differs between the two texts in these ayahs: (index of the first imlāʾī word, imlāʾī words, Uthmani words).
# Everywhere else one imlāʾī word is one Uthmani word, except that the vocative «يَا» / «وَيَا» joins the word after it.
SPLITS = {'2:181': (2, 1, 2), '8:6': (3, 1, 2), '13:37': (7, 1, 2), '20:94': (1, 3, 1), '37:130': (2, 2, 1), '72:16': (0, 2, 1),
          '3:66': (0, 2, 1), '3:119': (0, 2, 1), '4:109': (0, 2, 1), '47:38': (0, 2, 1)}   # the last four: «هَا أَنتُمْ»

def _pause(tok): return all('ۖ' <= c <= 'ۜ' for c in tok)   # stand-alone pause marks in the imlāʾī text

def _word(w):
    """The letters of a word: every combining sign (vowels, shadda, sukun, dagger alif…) is left out."""
    return ''.join(ch for ch in w if unicodedata.category(ch) != 'Mn')

def align(key, imlaei, uthmani):
    """One ayah -> [(imlāʾī words, Uthmani words), ...]; None if the two texts do not line up."""
    iw = [t for t in imlaei.split() if not _pause(t)]
    out = []; i = j = 0
    while i < len(iw):
        if key in SPLITS and SPLITS[key][0] == i: ni, nu = SPLITS[key][1:]
        elif iw[i] in ('يَا', 'وَيَا'): ni, nu = 2, 1
        else: ni, nu = 1, 1
        out.append((iw[i:i + ni], uthmani[j:j + nu])); i += ni; j += nu
    return out if (i == len(iw) and j == len(uthmani)) else None

def source():
    """-> {'s:a': (imlāʾī text, [Uthmani words without the closing ayah number])} for the whole Quran.
    The data file has one line per ayah — the imlāʾī text, then each Uthmani word, tab-separated — and an empty
    line between surahs (details and sources: assets/quran/SOURCE.md)."""
    import lzma
    out = {}; s = 1; a = 0
    for line in lzma.open(os.path.join(QDIR, 'quran.txt.xz'), 'rt', encoding='utf-8').read().rstrip('\n').split('\n'):
        if not line: s += 1; a = 0; continue
        a += 1; f = line.split('\t'); out[f'{s}:{a}'] = (f[0], f[1:])
    return out

_flat = None; _index = None
def _load():
    """Per surah, one flat list of imlāʾī words: (letters, ayah, Uthmani words | None, closes a group)."""
    global _flat, _index
    if _flat is not None: return
    _flat = {}; _index = {}
    for key, (imlaei, uthmani) in source().items():
        s, a = map(int, key.split(':'))
        row = _flat.setdefault(s, [])
        for iw, uw in align(key, imlaei, uthmani):
            for n, w in enumerate(iw):
                letters = _word(w)
                _index.setdefault(letters, []).append((s, len(row)))
                # the Uthmani words hang on the first imlāʾī word of the group; the last one closes it
                row.append((letters, a, uw if n == 0 else None, n == len(iw) - 1))

def _tokens(text):
    """The author's verse -> [('w', letters) | ('n', ayah number)]. Pause marks are ignored."""
    out = []
    for tok in text.split():
        tok = ''.join(c for c in tok if not ('ۖ' <= c <= 'ۜ'))
        if not tok: continue
        num = tok.strip('()۝')
        if num and all(c in '٠١٢٣٤٥٦٧٨٩0123456789' for c in num): out.append(('n', int(num.translate(DIG))))
        else: out.append(('w', _word(tok)))
    return out

def _match(tokens, s, p):
    """Try the author's tokens at word p of surah s -> (first ayah, last ayah, Uthmani text) or None."""
    row = _flat[s]
    if row[p][2] is None: return None          # must start on a whole Uthmani word
    out = []; first = row[p][1]
    for t in tokens:
        if t[0] == 'n':   # an ayah number the author wrote: only right after the last word of that ayah
            if not out or row[p - 1][1] != t[1] or (p < len(row) and row[p][1] == t[1]): return None
            out.append(str(t[1]).translate(HINDI))
            continue
        if p >= len(row) or t[1] != row[p][0]: return None   # the letters decide; the author's marks play no part
        uw = row[p][2]
        if uw: out.extend(w[2:] if w.startswith('۞ ') else w for w in uw)   # the ۞ hizb sign is a page mark, not text
        p += 1
    if not row[p - 1][3]: return None          # must end on a whole Uthmani word
    return first, row[p - 1][1], ' '.join(out)

HINDI = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
def surah(name):
    """The number of the surah the author named, or None."""
    return NAMES.get(_name(name))

def _where(s, a, b=None):
    return SURAHS[s - 1].replace('\u00a0', ' ') + (f': {a}' + (f'-{b}' if b not in (None, a) else '') if a else '').translate(HINDI)

def place(verse, ref=None):
    """verse: the text the author marked as a verse; ref: (surah name, ayah numbers or None) as written, or None.
    -> ((surah, first ayah, last ayah, Uthmani text), '') when the letters settle one place, or (None, why not — in Arabic).
    Nothing is recorded: the index of verses asks where a verse is without converting it."""
    _load()
    tokens = _tokens(verse)
    if not tokens or tokens[0][0] != 'w': return None, 'ليس فيها نص آية'
    hits = [(s,) + m for s, p in _index.get(tokens[0][1], []) for m in [_match(tokens, s, p)] if m]   # (surah, first ayah, last ayah, text)
    def listed(hs):
        places = sorted({h[:3] for h in hs})
        return '، '.join(_where(*x) for x in places[:4]) + (' …' if len(places) > 4 else '')
    if ref:
        s = surah(ref[0]); n = [int(x) for x in re.findall(r'\d+', (ref[1] or '').translate(DIG))]
        if not s: return None, f'اسم السورة في الإحالة غير معروف «{ref[0].strip()}»'
        lo, hi = (min(n), max(n)) if n else (1, 10 ** 4)
        there = [h for h in hits if h[0] == s and lo <= h[1] and h[2] <= hi]
        told = _where(s, lo if n else None, hi)
        if not there:
            # the letters decide the place; a reference that points elsewhere is the author's to check
            if hits: return None, f'حروفها تطابق [{listed(hits)}]، والإحالة تشير إلى [{told}]؛ فتحقّق من أحدهما'
            return None, f'حروفها لا تطابق نص المصحف في [{told}] ولا في غيره'
        hits = there
    elif not hits: return None, 'حروفها لا تطابق نص المصحف'
    texts = {h[3] for h in hits}
    # the same wording in several places is converted as long as its Uthmani text is one and the same in all of them
    if len(texts) > 1: return None, f'وردت بهذا اللفظ في مواضع يختلف رسمها [{listed(hits)}]؛ فأضف إحالتها أو اسم سورتها'
    # one Uthmani text in several places: it converts, but the index cannot tell which place the author meant
    many = len({h[:3] for h in hits}) > 1
    return min(hits), (f'وردت بهذا اللفظ في أكثر من موضع [{listed(hits)}]؛ فأضف إحالتها ليُعرف موضعها' if many else '')

def convert(verse, ref=None):
    """verse: the text the author marked as a verse; ref: (surah name, ayah numbers or None) as written, or None.
    -> the Uthmani text, or None when the verse must stay as written. Every call adds a line to REPORT."""
    hit, note = place(verse, ref)
    REPORT.append((hit is not None, verse.strip(), '' if hit else note))
    return hit[3] if hit else None

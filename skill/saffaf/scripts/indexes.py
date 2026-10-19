"""Shared by typeset.py and make.py: the indexes (الفهارس), the marks that feed them, Arabic alphabetical order, and the
opening basmala.

A mark wraps the author's own words in in.md and changes none of them:
    {{علم|ابن تيمية}}                    the words as written are the entry
    {{علم|شيخ الإسلام|ابن تيمية}}        the third field is the entry when the index should list it under another form
    {{شعر|البيت كما كتبه المؤلف||ب}}      a fourth field sets the group (poetry: the rhyme letter, القافية)
The words between the braces stay in the text exactly as they are; only the braces, the kind and the extra fields go."""
import re, unicodedata

# kind -> title of its index, in the order the indexes conventionally follow one another at the end of a work
KINDS = {
    'آية': 'فهرس الآيات القرآنية',
    'حديث': 'فهرس الأحاديث النبوية',
    'أثر': 'فهرس الآثار',
    'علم': 'فهرس الأعلام',
    'راو': 'فهرس رواة الحديث',
    'نسب': 'فهرس الأنساب',
    'غريب': 'فهرس الكلمات الغريبة',
    'شعر': 'فهرس الشواهد الشعرية',
    'مكان': 'فهرس الأماكن والبلدان',
    'مصطلح': 'فهرس المصطلحات',
    'مصدر': 'فهرس المصادر والمراجع',
}
ALIASES = {'راوي': 'راو', 'الآيات': 'آية', 'آيات': 'آية', 'الأحاديث': 'حديث', 'أحاديث': 'حديث', 'الآثار': 'أثر', 'آثار': 'أثر',
           'الأعلام': 'علم', 'أعلام': 'علم', 'رواة': 'راو', 'الرواة': 'راو', 'الأنساب': 'نسب', 'أنساب': 'نسب', 'الغريب': 'غريب',
           'الشعر': 'شعر', 'الأماكن': 'مكان', 'أماكن': 'مكان', 'البلدان': 'مكان', 'المصطلحات': 'مصطلح', 'مصطلحات': 'مصطلح',
           'المصادر': 'مصدر', 'مصادر': 'مصدر', 'المراجع': 'مصدر'}
MARKABLE = [k for k in KINDS if k not in ('آية', 'مصدر')]   # verses are found by themselves; sources come from the citations
# names, places and words are ordered without their «ال»; sayings and verses of poetry by their first word as written
DROP_AL = {'علم', 'راو', 'نسب', 'غريب', 'مكان', 'مصطلح', 'مصدر'}

def kind(word):
    w = word.strip()
    w = ALIASES.get(w, w)
    return w if w in KINDS else None

MARK = re.compile(r'\{\{\s*([^{}|]+?)\s*\|([^{}|]*)(?:\|([^{}|]*))?(?:\|([^{}|]*))?\}\}')
def strip_marks(t):
    """The text with every mark taken out and the author's words left in place."""
    return MARK.sub(lambda m: m.group(2), t)

def directive(line):
    """«@index علم» -> 'علم'; None for any other line."""
    m = re.match(r'^@index\s+(\S+)\s*$', line.strip())
    return kind(m.group(1)) if m else None

# ---------- alphabetical order (الترتيب الألفبائي) ----------
FOLD = str.maketrans('أإآٱءؤئىة', 'اااااوييه')   # hamza seats, alif wasla and alif maqsura fold into their letter; ة with ه
def bare(t):
    return ''.join(c for c in unicodedata.normalize('NFC', t) if unicodedata.category(c) != 'Mn' and c != 'ـ')

def key(t, drop_al=False):
    """Sort key: the letters only, hamza seats folded, and (for names, places, words) the «ال» of the first word left out."""
    s = re.sub(r'\*\*|\[\^[^\]]+\]|⟦|⟧', '', t)
    s = bare(s).translate(FOLD)
    s = re.sub(r'^[^ء-يA-Za-z0-9]+', '', s)
    if drop_al: s = re.sub(r'^(?:ال)(?=[ء-ي]{2})', '', s)
    return re.sub(r'[^ء-يA-Za-z0-9 ]', '', s).strip()

LETTERS = 'ابتثجحخدذرزسشصضطظعغفقكلمنهوي'
NAMES = dict(zip(LETTERS, ['الألف', 'الباء', 'التاء', 'الثاء', 'الجيم', 'الحاء', 'الخاء', 'الدال', 'الذال', 'الراء', 'الزاي',
                           'السين', 'الشين', 'الصاد', 'الضاد', 'الطاء', 'الظاء', 'العين', 'الغين', 'الفاء', 'القاف', 'الكاف',
                           'اللام', 'الميم', 'النون', 'الهاء', 'الواو', 'الياء']))
def order(k):
    """Position of a sort key: Arabic letters in their alphabetical order, then anything else."""
    return [LETTERS.index(c) if c in LETTERS else (100 + ord(c) if c != ' ' else -1) for c in k]

def letter(k):
    return k[0] if k and k[0] in LETTERS else None

def rhyme(verse):
    """The rhyme letter (الرويّ) of a verse of poetry: its last letter, passing over a final alif, waw or ya of prolongation."""
    s = re.sub(r'[^ء-ي]', '', bare(verse))
    if len(s) > 1 and s[-1] in 'اوي': s = s[:-1]
    s = s.translate(str.maketrans('أإآ', 'ااا'))
    return s[-1] if s else None

# ---------- the basmala ----------
BASMALA = 'بسماللهالرحمنالرحيم'
def is_basmala(line):
    """A line that is only the basmala (with or without vowel marks, brackets or a full stop), or the sign ﷽."""
    t = re.sub(r'^(>>|\*\*)\s*', '', line.strip()).replace('**', '')
    if t.strip() == '﷽': return True
    s = bare(t).translate(str.maketrans('أإآٱ', 'اااا'))
    return re.sub(r'[^ء-ي]', '', s) == BASMALA and not re.search(r'[A-Za-z0-9٠-٩]', t)
SHAPES = [0x1EE00 + i for i in range(7)]   # the basmalas of Lotus Lotfi, in the font's own order (see the preview image)

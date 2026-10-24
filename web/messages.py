"""What the service says to the user, in Arabic. The ready-made lines are the skill's own (SKILL.md, «The reply»),
word for word; the engine's English report lines are said here in Arabic. Lines the engine already writes in Arabic
(QURAN, CITE, THESIS, «INDEX لم تدخل», FONTS) are passed on as they are, without their English tag."""
import re

FONTS_ZIP = ('لعرض ملف Word بالخط الصحيح فكّ الملف المضغوط المرفق (\u2068خطوط-لملف-Word.zip\u2069) وثبّت الخطوط التي فيه. '
             'وملف PDF لا يحتاج شيئًا.')
FIELDS = 'عند فتح ملف Word يسألك عن تحديث الحقول؛ وافق لتصحّ أرقام الصفحات في الفهارس على ترتيب Word نفسه.'
PANEL = 'قرأتُ نصّك، وهذه إعدادات صفّه، ومعها ما أقترحه لكل واحد منها. اختر ما تريد، أو اضغط «صُفَّ النص» لأعتمد المقترح كله.'
REFUSE_PDF = 'لا أقبل ملفات PDF ولا الصور؛ لأن النص المستخرج منها تتلف حروفه، ولا أخمّن حروف الكاتب. أرسل الأصل: ملف Word أو النص نفسه.'
NUMERAL = 'في Word تتبع أرقام الحواشي إعداد «Numeral» عند القارئ؛ ولإظهارها مشرقية يُختار Context أو Hindi. وهي في PDF مشرقية دائمًا.'
MAC_PDF = ('الأصل أن يُستعمل PDF صفّاف. ومن يريد PDF من Word على الماك يصدّره من Print ← Save as PDF ليبقى الخط؛ '
           'فالتصدير المباشر (Save As › PDF) يستبدل بخط الملف خطًّا آخر لأن الملف لا يضمّن خطوطه.')
CITE_MARKS = ('في نصك رموز إحالة {{مرجع|…}} تحتاج نظام إحالة وملف مصادر، وصفّها يحتاج المساعد الذكي، '
              'وهو غير مفعّل في هذه النسخة التجريبية.')
SPLIT_REF = 'قد تنقسم إحالة قصيرة مثل «(ت: ٧٥١هـ)» على سطرين في PDF، وهذا حدٌّ معروف في محرّك PDF؛ وهي سليمة في ملف Word.'

def damaged(examples):
    a = (examples + ['…', '…'])[:2]
    return f'يبدو أن هذا النص منسوخ من ملف PDF، فقد تلفت بعض حروفه، مثل «{a[0]}» و«{a[1]}». أرسل الأصل: ملف Word أو النص نفسه.'

def missing_cover(what):
    return f'لم أجد في النص {what} فتركتُه؛ أرسله إن أردتَ إضافته.'

def unknown_format(ext):
    return (f'لا أعرف صيغة الملف «{ext or "بلا امتداد"}». أرسل ملف Word ‏(DOCX أو DOC) أو ODT أو RTF أو HTML أو EPUB أو TXT أو MD، '
            'أو الصق النص نفسه.')

TO_MD = [
    (re.compile(r'^file was Windows-1256 encoded'), lambda m: None),   # repaired silently: nothing for the user to do
    (re.compile(r'^a table cell contains "\|"'), lambda m: 'في أحد جداولك خانة فيها الرمز «|»؛ راجع ذلك الجدول في الملف الناتج.'),
    (re.compile(r'^EPUB: footnotes stay'), lambda m: 'حواشي ملف EPUB تبقى في مواضعها من الكتاب كما هي (روابط أو تعليقات)، ولا تصير حواشيَ أسفل الصفحة في هذه النسخة.'),
    (re.compile(r'^note (\S+) is referenced but has no text'), lambda m: 'في ملفك إحالة إلى حاشية لا نص لها، فبقيت فارغة.'),
    (re.compile(r'^(\d+) note\(s\) exist but are never referenced'), lambda m: f'في ملفك حواشٍ لا إحالة إليها في المتن (عددها {ar(m.group(1))})، فلم تظهر.'),
]
MAKE = [
    (re.compile(r'^QURAN بقيت كما كُتبت: (.*)$'), lambda m: 'بقيت كما كُتبت: ' + m.group(1)),
    (re.compile(r'^QURAN: (.*)$'), lambda m: m.group(1)),
    (re.compile(r'^INDEX لم تدخل (.*)$'), lambda m: 'لم تدخل ' + m.group(1)),
    (re.compile(r'^INDEX: no entry was marked for (\S+)'), lambda m: f'لم أجد مداخل لفهرس «{m.group(1)}»، فجاء فارغًا.'),
    (re.compile(r'^INDEX: unknown kind of mark'), lambda m: 'في النص علامات فهارس لا أعرف نوعها؛ بقيت كلماتها كما هي.'),
    (re.compile(r'^SORT: '), lambda m: 'قائمة مصادرك مرقّمة، فتركتُ ترتيبها كما كتبتَه؛ لأن إعادة ترقيمها تغيّر النص.'),
    (re.compile(r'^BASMALA: '), lambda m: 'لا يبدأ النص بالبسملة، فلم تُرسم البسملة المخطوطة.'),
    (re.compile(r'^TOC: page not found for: (.*)$'), lambda m: 'لم أجد في PDF صفحة بعض العناوين، فظهر أمامها «؟» في الفهرس.'),
    (re.compile(r'^CITE: complete$'), lambda m: None),
    (re.compile(r'^CITE: (.*)$'), lambda m: m.group(1)),
    (re.compile(r'^THESIS: (.*)$'), lambda m: m.group(1)),
    (re.compile(r'^FONTS: (.*)$'), lambda m: 'في ملف PDF ' + m.group(1).replace('حروف ليست في خطوط المهارة', 'حروف ليست في خطوط صفّاف') + '؛ وهي في ملف Word كما كتبتَها.'),
]

def ar(s): return str(s).translate(str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩'))

def translate(lines, table):
    out = []
    for l in lines:
        l = l.strip()
        for rx, f in table:
            m = rx.match(l)
            if m:
                t = f(m)
                if t and t not in out: out.append(t)
                break
    return out

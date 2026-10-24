"""The structure layer: rules, pasted footnotes, tables, and the guarantee that no role changes the author's text."""
import os, sys, random, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import structure as S

PASTE = """أثر العلم في بناء الإنسان
إعداد: باحث تجريبي
المقدمة
الحمد لله.. أما بعد: فإن العلم أشرف ما رغب فيه الراغب(١)، قال تعالى: ﴿وَقُلْ رَبِّ زِدْنِي عِلْمًا﴾ [طه: ١١٤].
أهداف البحث:
١- بيان فضل العلم.
المبحث الأول: فضل العلم
المطلب الأول: الأمر بالاستزادة
لم يأمر الله نبيه ﷺ بطلب الزيادة إلا من العلم (٢)، وذكره الواحدي (ت:٤٦٨).
المصطلح	المعنى
التفسير	البيان والكشف
الخاتمة
هذه خاتمة.
______
(١) انظر: الوسيط (١/ ٢٢٥).
(٢) تفسير ابن كثير (٥/ ٣١٩)."""

def prepared(text=PASTE, source='text'):
    items = S.parse(text); S.suggest(items, source)
    if source == 'text': S.pair_notes(items); S.tables(items)
    return items

def role_of(items, start):
    return next(it['role'] for it in items if it['kind'] == 'text' and it['text'].startswith(start))

class Rules(unittest.TestCase):
    def test_headings(self):
        it = prepared()
        self.assertEqual(role_of(it, 'أثر العلم'), 'h1')
        self.assertEqual(role_of(it, 'إعداد'), 'center')
        self.assertEqual(role_of(it, 'المقدمة'), 'h1')
        self.assertEqual(role_of(it, 'المبحث الأول'), 'h1')
        self.assertEqual(role_of(it, 'المطلب الأول'), 'h2')
        self.assertEqual(role_of(it, 'أهداف البحث'), 'h3')
        self.assertEqual(role_of(it, 'الحمد لله'), 'p')
        self.assertEqual(role_of(it, '١- بيان'), 'p')

    def test_word_headings_left_alone(self):
        draft = '# العنوان\n**المقدمة**\nنص.\n## المطلب\n**أهداف المقال:**\nنص آخر.'
        it = prepared(draft, 'word')
        self.assertEqual(role_of(it, 'العنوان'), 'h1')
        self.assertEqual(role_of(it, 'المقدمة'), 'h1')
        self.assertEqual(role_of(it, 'أهداف المقال'), 'h3')

    def test_sentence_is_not_a_heading(self):
        it = prepared('المقدمة في هذا البحث طويلة وتنتهي بنقطة كما ترى هنا في هذا المثال.\nنص.', 'text')
        self.assertEqual(it[0]['role'], 'p')

class PastedNotes(unittest.TestCase):
    def test_paired(self):
        it = prepared()
        notes = [x for x in it if x['kind'] == 'pnote']
        self.assertEqual(len(notes), 2)
        body, cover, _ = S.render(it)
        md = '\n'.join(body)
        self.assertIn('الراغب[^n1]،', md)
        self.assertIn('العلم [^n2]،', md)   # the author's space before the number is kept
        self.assertIn('[^n1]: انظر: الوسيط (١/ ٢٢٥).', md)
        self.assertNotIn('______', md)       # the separator line above the notes
        self.assertEqual(S.verify(it, body, cover), [])

    def test_ambiguous_left_as_written(self):
        text = PASTE.replace('هذه خاتمة.', 'هذه خاتمة (١).')   # «(١)» twice in the text
        it = S.parse(text); n, why = S.pair_notes(it)
        self.assertEqual(n, 0); self.assertTrue(why)
        self.assertFalse(any(x['kind'] == 'pnote' for x in it))

    def test_restarting_numbers_left_as_written(self):
        it = S.parse('نص(١) ونص(٢)\nنص آخر(١)\n(١) أ\n(٢) ب\n(١) ج'); n, why = S.pair_notes(it)
        self.assertEqual(n, 0); self.assertIn('ليست مرقّمة', why)

class Tables(unittest.TestCase):
    def test_tab_table(self):
        it = prepared()
        body, cover, _ = S.render(it)
        self.assertIn('| المصطلح | المعنى |', body)
        self.assertIn('|---|---|', body)
        self.assertEqual(S.verify(it, body, cover), [])

class Guarantee(unittest.TestCase):
    """Whatever roles the user (or a model) picks, the author's text comes back unchanged."""
    def test_any_roles_keep_the_text(self):
        rnd = random.Random(7)
        for _ in range(300):
            it = prepared()
            for x in it:
                if x['kind'] == 'text': x['role'] = rnd.choice(S.EDITABLE)
            body, cover, _ = S.render(it)
            self.assertEqual(S.verify(it, body, cover), [], body)

    def test_tampering_is_caught(self):
        it = prepared(); body, cover, _ = S.render(it)
        for k, l in enumerate(body):
            if l.startswith('الحمد'): body[k] = l.replace('أشرف', 'اشرف')
        self.assertTrue(S.verify(it, body, cover))
        it = prepared(); body, cover, _ = S.render(it)
        body = [l for l in body if not l.startswith('هذه خاتمة')]
        self.assertTrue(S.verify(it, body, cover))

    def test_invented_cover_is_caught(self):
        it = prepared(); body, cover, _ = S.render(it)
        cover['author'] = ['اسم لم يكتبه أحد']
        self.assertTrue(S.verify(it, body, cover))
        self.assertEqual(S.verify(it, body, cover, typed={'author': 'اسم لم يكتبه أحد'}), [])

    def test_cover_role_moves_the_line(self):
        it = prepared()
        for x in it:
            if x['kind'] == 'text' and x['text'].startswith('أثر العلم'): x['role'] = 'c_title'
        body, cover, moved = S.render(it)
        self.assertEqual(cover['title'], ['أثر العلم في بناء الإنسان'])
        self.assertFalse(any('أثر العلم' in l for l in body))
        self.assertEqual(S.verify(it, body, cover), [])

if __name__ == '__main__':
    unittest.main()

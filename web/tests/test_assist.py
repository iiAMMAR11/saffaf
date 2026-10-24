"""The assistant's answers are checked before use. These tests feed hand-written answers (good and bad) — no model is
called, nothing is sent anywhere."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from assist import validate as V, providers, tasks
import indexes

P = {
    1: 'وقال شيخ الإسلام ابن تيمية: العلم ما قام عليه الدليل.',
    2: 'وذكر ابن تيمية أن أهل مكة كانوا يعظّمون العلم.',
    3: 'قال رسول الله ﷺ: «إنما الأعمال بالنيات»[^f1].',
}

class Marks(unittest.TestCase):
    def test_good_marks_keep_the_text(self):
        t1 = P[1]; s = t1.index('شيخ الإسلام')
        ans = {'marks': [
            dict(i=1, start=s, end=s + len('شيخ الإسلام'), kind='علم', entry='ابن تيمية'),
            dict(i=2, start=P[2].index('مكة'), end=P[2].index('مكة') + 3, kind='مكان', entry=''),
            dict(i=3, start=P[3].index('إنما'), end=P[3].index('بالنيات') + len('بالنيات'), kind='حديث', entry=''),
        ]}
        out, dropped = V.marks(ans, P)
        self.assertEqual(dropped, [])
        self.assertIn('{{علم|شيخ الإسلام|ابن تيمية}}', out[1])
        for i, t in out.items(): self.assertEqual(indexes.strip_marks(t), P[i])

    def test_bad_marks_are_dropped(self):
        ans = {'marks': [
            dict(i=9, start=0, end=3, kind='علم', entry=''),                       # no such paragraph
            dict(i=1, start=5, end=500, kind='علم', entry=''),                     # outside
            dict(i=1, start=0, end=4, kind='آية', entry=''),                       # verses are not marked by hand
            dict(i=3, start=P[3].index('بالنيات'), end=len(P[3]), kind='حديث', entry=''),   # cuts the footnote link
            dict(i=2, start=P[2].index('ابن'), end=P[2].index('ابن') + 9, kind='علم', entry='أحمد بن عبد الحليم'),  # a form not in the text
        ]}
        out, dropped = V.marks(ans, P)
        self.assertEqual(len(dropped), 5)
        self.assertEqual(out.get(2), 'وذكر {{علم|ابن تيمية}} أن أهل مكة كانوا يعظّمون العلم.')   # kept, without the invented form

class Sources(unittest.TestCase):
    NOTES = {1: 'انظر: مجموع الفتاوى، لابن تيمية، ٣/ ٤٥، وفيه نظر.', 2: 'مجموع الفتاوى ١٠/ ٢٠.'}
    TEXT = '\n'.join(NOTES.values()) + '\nمجموع الفتاوى، ابن تيمية، المدينة المنورة: مجمع الملك فهد، ١٤١٦هـ.'

    def test_details_only_from_the_text(self):
        n1 = self.NOTES[1]; s = n1.index('مجموع'); e = n1.index('٤٥') + 2
        ans = {'sources': [dict(id='fatawa', type='book', authors=['ابن تيمية'], title='مجموع الفتاوى',
                                place='المدينة المنورة', publisher='مجمع الملك فهد', year='١٤١٦هـ',
                                editor='عبد الرحمن بن قاسم')],   # the editor is nowhere in the text
               'cites': [dict(note=1, start=s, end=e, id='fatawa', place='٣/ ٤٥')]}
        src, notes, missing, dropped = V.sources(ans, self.NOTES, self.TEXT)
        self.assertNotIn('editor', src['fatawa']); self.assertIn('editor', missing['fatawa'])
        self.assertEqual(src['fatawa']['publisher'], 'مجمع الملك فهد')
        self.assertEqual(notes[1], 'انظر: {{مرجع|fatawa|٣/ ٤٥}}، وفيه نظر.')   # the author's other words stay

    def test_supplied_detail_is_kept(self):
        ans = {'sources': [dict(id='fatawa', type='book', authors=['ابن تيمية'], title='مجموع الفتاوى', editor='')], 'cites': []}
        src, _, missing, _ = V.sources(ans, self.NOTES, self.TEXT, supplied={'fatawa': {'editor': 'عبد الرحمن بن قاسم'}})
        self.assertEqual(src['fatawa']['editor'], 'عبد الرحمن بن قاسم')

    def test_place_must_be_in_the_reference(self):
        n2 = self.NOTES[2]
        ans = {'sources': [dict(id='fatawa', type='book', authors=[], title='مجموع الفتاوى')],
               'cites': [dict(note=2, start=0, end=len(n2) - 1, id='fatawa', place='٩/ ٩٩')]}
        _, notes, _, dropped = V.sources(ans, self.NOTES, self.TEXT)
        self.assertEqual(notes.get(2, n2), n2); self.assertTrue(dropped)

class Labels(unittest.TestCase):
    def test_labels(self):
        out, dropped = V.labels({'labels': [dict(i=1, role='h1'), dict(i=7, role='h1'), dict(i=2, role='bold')]}, P)
        self.assertEqual(out, {1: 'h1'}); self.assertEqual(len(dropped), 2)

class Off(unittest.TestCase):
    def test_disabled_by_default(self):
        os.environ.pop('SAFFAF_ASSIST', None)
        p = providers.provider()
        self.assertEqual(p.name, 'disabled')
        with self.assertRaises(providers.AssistantDisabled): p.ask('marks', [(1, P[1])])

    def test_schemas_are_strict(self):
        def walk(s):
            if s.get('type') == 'object': self.assertIs(s.get('additionalProperties'), False); [walk(v) for v in s['properties'].values()]
            if s.get('type') == 'array': walk(s['items'])
        for t in tasks.TASKS.values(): walk(t['schema'])

if __name__ == '__main__':
    unittest.main()

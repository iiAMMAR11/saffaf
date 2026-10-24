"""The service end to end, through its HTTP interface: every accepted format, every refusal, the text kept letter for
letter in the Word file, the check that stops a changed file, and the deletion of a job's files.
Needs LibreOffice and poppler-utils, like the engine's own tests. Takes a few minutes."""
import os, sys, re, time, shutil, zipfile, tempfile, unittest
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
os.environ['SAFFAF_JOBS_DIR'] = tempfile.mkdtemp(prefix='saffaf-test-jobs-')
sys.path.insert(0, HERE)
from fastapi.testclient import TestClient
import app as A, pipeline, structure
from tests.test_structure import PASTE

C = TestClient(A.app)
F = os.path.join(ROOT, 'tests', 'formats')

def upload(name=None, data=None, text=None):
    if text is not None: return C.post('/api/jobs', data={'text': text})
    return C.post('/api/jobs', files={'file': (name, data)})

def typeset(jid, opts, limit=300):
    C.post(f'/api/jobs/{jid}/typeset', json=opts)
    t = time.time()
    while time.time() - t < limit:
        s = C.get(f'/api/jobs/{jid}').json()
        if s['state'] != 'running': return s
        time.sleep(1)
    raise AssertionError('typesetting did not finish')

def paragraphs(docx):
    return '\n'.join(pipeline.docx_text(docx))

class Refusals(unittest.TestCase):
    def test_pdf_by_extension(self):
        r = upload('x.pdf', open(os.path.join(F, 'reject.pdf'), 'rb').read())
        self.assertEqual(r.status_code, 422); self.assertIn('لا أقبل ملفات PDF', r.json()['refused'])
    def test_pdf_by_content(self):   # a PDF renamed .docx
        r = upload('x.docx', open(os.path.join(F, 'reject.pdf'), 'rb').read())
        self.assertEqual(r.status_code, 422); self.assertIn('لا أقبل ملفات PDF', r.json()['refused'])
    def test_image(self):
        r = upload('scan.png', b'\x89PNG\r\n\x1a\n' + b'0' * 100)
        self.assertEqual(r.status_code, 422); self.assertIn('الصور', r.json()['refused'])
    def test_damaged_text(self):
        r = upload('x.txt', open(os.path.join(F, 'copied_from_pdf.txt'), 'rb').read())
        self.assertEqual(r.status_code, 422); self.assertIn('منسوخ من ملف PDF', r.json()['refused'])
    def test_unknown(self):
        r = upload('x.xyz', b'abc'); self.assertEqual(r.status_code, 422)
    def test_empty_text(self):
        r = upload(text='   '); self.assertEqual(r.status_code, 422)
    def test_refused_job_leaves_no_files(self):
        before = set(os.listdir(os.environ['SAFFAF_JOBS_DIR']))
        upload('x.pdf', b'%PDF-1.4')
        self.assertEqual(set(os.listdir(os.environ['SAFFAF_JOBS_DIR'])), before)

class Formats(unittest.TestCase):
    def test_each_format_is_read(self):
        for name in ('sample.docx', 'sample.odt', 'sample.epub', 'cp1256.txt', 'utf8_bom.txt', 'stress_article.docx', 'aga_symbols.docx'):
            with self.subTest(name=name):
                r = upload(name, open(os.path.join(F, name), 'rb').read())
                self.assertEqual(r.status_code, 200, r.text)
                v = r.json()
                self.assertTrue(v['items'])
                C.delete(f'/api/jobs/{v["id"]}')
    def test_md_with_front_matter(self):
        r = upload('basic.md', open(os.path.join(ROOT, 'tests', 'inputs', 'basic.md'), 'rb').read())
        self.assertEqual(r.status_code, 200); C.delete(f'/api/jobs/{r.json()["id"]}')

class EndToEnd(unittest.TestCase):
    def test_pasted_text_paper(self):
        v = upload(text=PASTE).json()
        self.assertTrue(v['needs_review'])
        s = typeset(v['id'], dict(kind='paper', toc='front', uthmani=True, verse_index=True, header=True,
                                  cover=dict(author='باحث تجريبي', date='١٤٤٧هـ')))
        self.assertEqual(s['state'], 'done', s)
        j = A.store.get(v['id'])
        docx = j.path('out', 'نص.docx')
        text = paragraphs(docx)
        # every line of the author's (bar the verse set in Uthmani script) is in the Word file, letter for letter
        for line in PASTE.split('\n'):
            line = structure.NOTE_LINE.sub(lambda m: m.group(3), line) if structure.NOTE_LINE.match(line) else line
            line = re.sub(r'\(\s*[١٢]\s*\)', '', line) if not line.startswith('(') else line   # the number becomes the note's link; the author's space before it stays
            if not line.strip() or line.startswith('___') or '﴿' in line: continue
            for cell in line.split('\t'):
                self.assertIn(pipeline.norm(cell), pipeline.norm(text.replace('', '')), cell)
        z = zipfile.ZipFile(j.path('out', 'خطوط-لملف-Word.zip')).namelist()
        self.assertIn('_LotusLotfi-Regular.ttf', z); self.assertIn('UthmanicHafs_V22.ttf', z)
        for kind in ('pdf', 'docx', 'fonts'):
            r = C.get(f'/api/jobs/{v["id"]}/files/{kind}'); self.assertEqual(r.status_code, 200); self.assertGreater(len(r.content), 1000)
        self.assertEqual(C.get(f'/api/jobs/{v["id"]}/pages/1').status_code, 200)
        self.assertEqual(C.get(f'/api/jobs/{v["id"]}/pages/1?big=1').status_code, 200)
        # deleting the job removes every file of it
        d = j.dir
        self.assertTrue(C.delete(f'/api/jobs/{v["id"]}').json()['deleted'])
        self.assertFalse(os.path.exists(d))
        self.assertEqual(C.get(f'/api/jobs/{v["id"]}').status_code, 404)

    def test_word_article_with_symbols(self):
        v = upload('aga_symbols.docx', open(os.path.join(F, 'aga_symbols.docx'), 'rb').read()).json()
        self.assertTrue(v['symbols'])
        s = typeset(v['id'], dict(kind='article', toc='none', symbols=True))
        self.assertEqual(s['state'], 'done', s)
        text = paragraphs(A.store.get(v['id']).path('out', v['name'] + '.docx'))
        self.assertIn('ﷺ', text)
        C.delete(f'/api/jobs/{v["id"]}')

    def test_changed_output_is_stopped(self):
        """check_output finds a letter changed in the Word file (as an engine bug would)."""
        v = upload(text=PASTE).json()
        s = typeset(v['id'], dict(kind='article', toc='none'))
        self.assertEqual(s['state'], 'done', s)
        j = A.store.get(v['id']); docx = j.path('out', 'نص.docx')
        self.assertEqual(pipeline.check_output(j, docx, {}), [])
        bad = docx + '.bad.docx'
        zin = zipfile.ZipFile(docx); zout = zipfile.ZipFile(bad, 'w')
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename == 'word/document.xml': data = data.decode().replace('خاتمة', 'خاتمه', 1).encode()
            zout.writestr(it, data)
        zout.close()
        self.assertTrue(pipeline.check_output(j, bad, {}))
        C.delete(f'/api/jobs/{v["id"]}')

    def test_citation_marks_need_the_assistant(self):
        v = upload('indexes.md', open(os.path.join(ROOT, 'tests', 'inputs', 'indexes.md'), 'rb').read()).json()
        s = typeset(v['id'], dict(kind='paper', toc='none'))
        self.assertEqual(s['state'], 'failed'); self.assertIn('المساعد الذكي', s['error']['error'])
        C.delete(f'/api/jobs/{v["id"]}')

if __name__ == '__main__':
    unittest.main()

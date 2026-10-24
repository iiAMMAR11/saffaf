"""Jobs side by side: two documents set at once come out exactly as when set one after the other, and stopping one
job stops its own processes only."""
import os, sys, time, shutil, tempfile, threading, subprocess, unittest
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
os.environ.setdefault('SAFFAF_JOBS_DIR', tempfile.mkdtemp(prefix='saffaf-test-jobs-'))
sys.path.insert(0, HERE)
import jobs, pipeline
from tests.test_structure import PASTE

STORE = jobs.Store()
OPTS = dict(kind='article', toc='front')

def prepare_text(text):
    j = STORE.new(); src = pipeline.receive(j, text=text); pipeline.prepare(j, src); return j

def prepare_file(path):
    j = STORE.new(); src = pipeline.receive(j, filename=os.path.basename(path), data=open(path, 'rb').read()); pipeline.prepare(j, src); return j

def pdf_text(j):
    return subprocess.run(['pdftotext', '-layout', j.path('out', j.data['name'] + '.pdf'), '-'], capture_output=True, text=True).stdout

def processes_of(job_dir):
    n = 0
    for pid in os.listdir('/proc'):
        if not pid.isdigit(): continue
        try:
            if job_dir in open(f'/proc/{pid}/cmdline', 'rb').read().decode('utf-8', 'replace'): n += 1
        except OSError: pass
    return n

class Concurrency(unittest.TestCase):
    def test_parallel_equals_serial(self):
        docx = os.path.join(ROOT, 'tests', 'formats', 'stress_article.docx')
        serial = []
        for make in (lambda: prepare_text(PASTE), lambda: prepare_file(docx)):
            j = make(); r = pipeline.typeset(j, OPTS); self.assertTrue(r['ok'], r); serial.append(pdf_text(j)); STORE.delete(j.id)
        par = [prepare_text(PASTE), prepare_file(docx)]
        res = [None, None]
        def go(k): res[k] = pipeline.typeset(par[k], OPTS)
        ts = [threading.Thread(target=go, args=(k,)) for k in range(2)]
        [t.start() for t in ts]; [t.join() for t in ts]
        for k in range(2):
            self.assertTrue(res[k]['ok'], res[k])
            self.assertEqual(pdf_text(par[k]), serial[k])
            self.assertTrue(os.path.isdir(par[k].path('lo', 'user')))   # its own LibreOffice profile
            STORE.delete(par[k].id)

    def test_stopping_one_job_spares_the_other(self):
        long_md = os.path.join(ROOT, 'tests', 'inputs', 'long_text.md')
        a = STORE.new(); b = prepare_text(PASTE)
        with open(long_md, encoding='utf-8') as f: text = f.read()
        with open(a.path('in.md'), 'w', encoding='utf-8') as f: f.write('\n'.join([text] * 6))   # long enough to outlast the limit
        out = {}
        def slow(): out['a'] = jobs.run(a, [os.path.join(jobs.SCRIPTS, 'make.py'), a.path('in.md'), a.path('out', 'x')], timeout=2)
        def normal(): out['b'] = pipeline.typeset(b, OPTS)
        ta = threading.Thread(target=slow); tb = threading.Thread(target=normal)
        tb.start(); time.sleep(1); ta.start(); ta.join()
        self.assertIsNone(out['a'][0])              # past its limit: stopped
        time.sleep(1)
        self.assertEqual(processes_of(a.dir), 0)    # with everything it started
        tb.join()
        self.assertTrue(out['b']['ok'], out['b'])   # the other job finished as usual
        STORE.delete(a.id); STORE.delete(b.id)

    def test_temporary_files_stay_in_the_job(self):
        j = prepare_text(PASTE); pipeline.typeset(j, OPTS)
        d = j.dir; STORE.delete(j.id)
        self.assertFalse(os.path.exists(d))

if __name__ == '__main__':
    unittest.main()

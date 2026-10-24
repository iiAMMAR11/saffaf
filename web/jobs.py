"""Jobs: one directory per document, one LibreOffice profile per job, a pool of workers, a time limit per job, and
deletion of every file once the job expires or the user deletes it.

Every process a job starts carries the job's directory in its command line (its files, its LibreOffice profile), so
stopping a job stops exactly its own processes — never another document's."""
import os, re, sys, json, time, shutil, signal, secrets, threading, subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, 'skill', 'saffaf', 'scripts')
JOBS_DIR = os.environ.get('SAFFAF_JOBS_DIR') or os.path.join('/tmp', 'saffaf-jobs')
TTL = int(os.environ.get('SAFFAF_JOB_TTL', 3600))            # seconds a job's files are kept
WORKERS = int(os.environ.get('SAFFAF_WORKERS', 2))           # documents set at the same time
JOB_TIMEOUT = int(os.environ.get('SAFFAF_JOB_TIMEOUT', 900))  # seconds one typesetting run may take
ID = re.compile(r'^[A-Za-z0-9_-]{20,40}$')

class Job:
    def __init__(self, jid):
        self.id = jid; self.dir = os.path.join(JOBS_DIR, jid)
        self.created = time.time(); self.state = 'new'; self.lock = threading.Lock()
        self.data = {}       # conversion results, items, options, results
        self.cancelled = False
    def path(self, *p): return os.path.join(self.dir, *p)
    def env(self):
        """The environment of every process of this job: its own home (fontconfig's per-user fonts and cache), its own
        temporary directory (every tempfile of the engine lands inside the job) and its own LibreOffice profiles."""
        e = dict(os.environ)
        e.update(HOME=self.path('home'), TMPDIR=self.path('tmp'), SAFFAF_LO_PROFILE=self.path('lo'),
                 SAFFAF_CONV_PROFILE=self.path('lo-conv'), PYTHONDONTWRITEBYTECODE='1')
        return e
    def save(self):
        with open(self.path('job.json'), 'w', encoding='utf-8') as f:
            json.dump(dict(id=self.id, state=self.state, created=self.created, data=self.data), f, ensure_ascii=False)

class Store:
    def __init__(self):
        os.makedirs(JOBS_DIR, exist_ok=True)
        self.jobs = {}; self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix='saffaf')
        self.gate = threading.BoundedSemaphore(WORKERS)   # LibreOffice runs at once (conversions and typesetting)
        threading.Thread(target=self._janitor, daemon=True).start()

    def new(self):
        jid = secrets.token_urlsafe(18)
        j = Job(jid)
        for d in ('src', 'out', 'home', 'tmp', 'lo', 'lo-conv'): os.makedirs(j.path(d), exist_ok=True)
        with self.lock: self.jobs[jid] = j
        return j

    def get(self, jid):
        if not ID.match(jid or ''): return None
        with self.lock: return self.jobs.get(jid)

    def delete(self, jid):
        with self.lock: j = self.jobs.pop(jid, None)
        if not j: return False
        j.cancelled = True
        kill(j.dir)
        shutil.rmtree(j.dir, ignore_errors=True)
        return True

    def _janitor(self):
        while True:
            time.sleep(30)
            now = time.time()
            with self.lock: old = [jid for jid, j in self.jobs.items() if now - j.created > TTL and j.state != 'running']
            for jid in old: self.delete(jid)
            # directories left by an earlier run of the service
            for d in os.listdir(JOBS_DIR):
                p = os.path.join(JOBS_DIR, d)
                with self.lock: known = d in self.jobs
                if not known and os.path.isdir(p) and now - os.path.getmtime(p) > TTL: shutil.rmtree(p, ignore_errors=True)

def kill(job_dir):
    """Stop every process whose command line names the job's directory (its make.py, typeset.py, LibreOffice …)."""
    me = os.getpid(); n = 0
    for pid in os.listdir('/proc'):
        if not pid.isdigit() or int(pid) == me: continue
        try:
            with open(f'/proc/{pid}/cmdline', 'rb') as f: cmd = f.read().decode('utf-8', 'replace')
        except OSError: continue
        if job_dir in cmd:
            try: os.kill(int(pid), signal.SIGKILL); n += 1
            except OSError: pass
    return n

def run(job, args, timeout=JOB_TIMEOUT, stdin=None):
    """Run one engine script for the job, in its own process group and environment. -> (returncode, stdout, stderr);
    returncode None when it ran past the time limit (it and everything it started are then stopped)."""
    p = subprocess.Popen([sys.executable] + args, cwd=job.dir, env=job.env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, start_new_session=True)
    try:
        out, err = p.communicate(timeout=timeout)
        return p.returncode, out, err
    except subprocess.TimeoutExpired:
        try: os.killpg(p.pid, signal.SIGKILL)
        except OSError: pass
        kill(job.dir)
        out, err = p.communicate()
        return None, out, err

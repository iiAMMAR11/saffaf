"""صفّاف — the web service. Run: uvicorn app:app (from web/), or ./run.sh."""
import os, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import jobs, pipeline
from pipeline import Refused

HERE = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(title='صفّاف', docs_url=None, redoc_url=None, openapi_url=None)
store = jobs.Store()
app.mount('/static', StaticFiles(directory=os.path.join(HERE, 'static')), name='static')

@app.middleware('http')
async def headers(request: Request, call_next):
    r = await call_next(request)
    r.headers['X-Content-Type-Options'] = 'nosniff'
    r.headers['Referrer-Policy'] = 'no-referrer'
    r.headers['X-Robots-Tag'] = 'noindex, nofollow'   # a trial: not for search engines
    if request.url.path.startswith('/api/'): r.headers['Cache-Control'] = 'no-store'
    return r

@app.get('/')
def index(): return FileResponse(os.path.join(HERE, 'static', 'index.html'), headers={'Cache-Control': 'no-cache'})

@app.get('/basmala-shapes.png')
def basmala(): return FileResponse(os.path.join(jobs.ROOT, 'skill', 'saffaf', 'assets', 'basmala-shapes.png'))

@app.get('/api/health')
def health(): return dict(ok=True, workers=jobs.WORKERS, jobs=len(store.jobs))

def job_or_404(jid):
    j = store.get(jid)
    if not j: raise HTTPException(404, 'انتهت مدة هذا الملف أو حُذف. أرسل نصك من جديد.')
    return j

@app.post('/api/jobs')
def create(file: UploadFile | None = File(None), text: str | None = Form(None)):
    j = store.new()
    try:
        if file is not None and file.filename:
            data = file.file.read(pipeline.MAX_BYTES + 1)
            src = pipeline.receive(j, filename=file.filename, data=data)
        elif text is not None:
            if len(text) > 2_000_000: raise Refused('النص أطول من الحدّ المسموح في هذه النسخة.')
            src = pipeline.receive(j, text=text)
        else: raise Refused('أرسل ملفًّا أو الصق نصًّا.')
        with store.gate: view = pipeline.prepare(j, src)
        j.state = 'ready'
        return view
    except Refused as e:
        store.delete(j.id)
        return JSONResponse(dict(refused=str(e)), status_code=422)
    except Exception:
        store.delete(j.id)
        raise

@app.post('/api/jobs/{jid}/logo')
def logo(jid: str, file: UploadFile = File(...)):
    j = job_or_404(jid)
    data = file.file.read(2 * 1024 * 1024 + 1)
    ext = '.png' if data[:4] == b'\x89PNG' else '.jpg' if data[:3] == b'\xff\xd8\xff' else None
    if not ext or len(data) > 2 * 1024 * 1024: raise HTTPException(422, 'الشعار صورة PNG أو JPEG لا تزيد على ٢ ميغابايت.')
    p = j.path('src', 'logo' + ext)
    with open(p, 'wb') as f: f.write(data)
    j.data['logo'] = p
    return dict(ok=True)

@app.post('/api/jobs/{jid}/typeset')
def start(jid: str, opts: dict):
    j = job_or_404(jid)
    with j.lock:
        if j.state == 'running': return dict(state='running')
        j.state = 'running'; j.data['error'] = None; j.data['started'] = time.time()
    def work():
        try:
            with store.gate:
                if j.cancelled: return
                res = pipeline.typeset(j, opts)
            if res.get('ok'): j.state = 'done'
            else: j.state = 'failed'; j.data['error'] = res
        except Exception as e:
            j.state = 'failed'; j.data['error'] = dict(ok=False, error='حدث خطأ غير متوقّع أثناء الصفّ.', detail=str(e)[:300])
    store.pool.submit(work)
    return dict(state='running')

@app.get('/api/jobs/{jid}')
def status(jid: str):
    j = job_or_404(jid)
    out = dict(state=j.state, expires_in=max(0, int(jobs.TTL - (time.time() - j.created))))
    if j.state == 'done': out['results'] = j.data.get('results')
    if j.state == 'failed': out['error'] = j.data.get('error')
    if j.state == 'running': out['elapsed'] = int(time.time() - j.data.get('started', time.time()))
    return out

FILES = {'pdf': ('application/pdf', '.pdf'), 'docx': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
         'fonts': ('application/zip', None)}

@app.get('/api/jobs/{jid}/files/{kind}')
def download(jid: str, kind: str, inline: int = 0):
    j = job_or_404(jid)
    if j.state != 'done' or kind not in FILES: raise HTTPException(404)
    mime, ext = FILES[kind]
    name = j.data['name'] + ext if ext else 'خطوط-لملف-Word.zip'
    p = j.path('out', name)
    if not os.path.exists(p): raise HTTPException(404)
    disp = 'inline' if inline and kind == 'pdf' else 'attachment'
    return FileResponse(p, media_type=mime, headers={'Content-Disposition': f"{disp}; filename*=UTF-8''{urllib.parse.quote(name)}"})

@app.get('/api/jobs/{jid}/pages/{n}')
def page(jid: str, n: int, big: int = 0):
    j = job_or_404(jid)
    if j.state != 'done': raise HTTPException(404)
    p = pipeline.page_image(j, n, bool(big))
    if not p: raise HTTPException(404)
    return FileResponse(p, media_type='image/png')

@app.delete('/api/jobs/{jid}')
def delete(jid: str):
    return dict(deleted=store.delete(jid))

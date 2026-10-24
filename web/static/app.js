// صفّاف — the page: send → review → options → files
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const AR = n => String(n).replace(/[0-9]/g, d => '٠١٢٣٤٥٦٧٨٩'[d]);
const VIEWS = ['send', 'review', 'options', 'result'];
const ROLES = [
  ['p', 'فقرة'], ['h1', 'عنوان رئيسي'], ['h2', 'عنوان فرعي'], ['h3', 'رأس مدمج'], ['center', 'سطر في الوسط'],
  ['c_title', 'الغلاف: العنوان'], ['c_line', 'الغلاف: سطر تحت العنوان'], ['c_author', 'الغلاف: المؤلف'],
  ['c_affil', 'الغلاف: الصفة'], ['c_date', 'الغلاف: التاريخ'],
];
const FIXED = { note: 'حاشية', pnote: 'حاشية', table: 'جدول', ttable: 'جدول', list: 'قائمة', directive: 'سطر المحرّك', front: 'الغلاف', sep: 'فاصل الحواشي' };
let job = null, roles = {}, tab = 'file', filter = 'main', poll = null;

function show(view) {
  VIEWS.forEach(v => { $('#v-' + v).hidden = v !== view; });
  const k = VIEWS.indexOf(view);
  $$('#steps li').forEach((li, i) => { li.classList.toggle('on', i === k); li.classList.toggle('done', i < k); });
  $('#hero').hidden = view !== 'send';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
function seg(el, value) { $$('button', el).forEach(b => b.classList.toggle('on', b.dataset.v === value)); }
function segVal(el) { const b = $('button.on', el); return b ? b.dataset.v : null; }
function alertBox(text, cls = '', small = '') {
  const d = document.createElement('div'); d.className = 'alert ' + cls; d.textContent = text;
  if (small) { const s = document.createElement('small'); s.textContent = small; d.append(s); }
  return d;
}
function refused(msg) { const r = $('#refused'); r.className = 'alert bad'; r.textContent = msg; r.hidden = !msg; if (msg) r.scrollIntoView({ behavior: 'smooth', block: 'center' }); }

// ---------- 1. send
$$('#v-send .seg button').forEach(b => b.onclick = () => {
  tab = b.dataset.tab; $$('#v-send .seg button').forEach(x => x.classList.toggle('on', x === b));
  $$('#v-send [data-pane]').forEach(p => p.hidden = p.dataset.pane !== tab);
});
const drop = $('#drop'), fileIn = $('#file');
fileIn.onchange = () => { $('#drop-title').textContent = fileIn.files[0] ? fileIn.files[0].name : 'اختر ملف بحثك أو اسحبه إلى هنا'; refused(''); };
['dragenter', 'dragover'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach(e => drop.addEventListener(e, ev => { ev.preventDefault(); drop.classList.remove('over'); }));
drop.addEventListener('drop', ev => { if (ev.dataTransfer.files[0]) { fileIn.files = ev.dataTransfer.files; fileIn.onchange(); } });

$('#send').onclick = async () => {
  refused('');
  const fd = new FormData();
  if (tab === 'file') { if (!fileIn.files[0]) return refused('اختر ملفًّا أولًا.'); fd.append('file', fileIn.files[0]); }
  else { const t = $('#text').value; if (!t.trim()) return refused('الصق النص أولًا.'); fd.append('text', t); }
  const btn = $('#send'); btn.disabled = true; btn.textContent = 'أقرأ نصّك…';
  try {
    const r = await fetch('/api/jobs', { method: 'POST', body: fd });
    const j = await r.json();
    if (!r.ok) return refused(j.refused || j.detail || 'تعذّر قراءة النص.');
    job = j; roles = {};
    job.items.forEach(it => { if (it.kind === 'text') roles[it.i] = it.role; });
    renderReview(); renderOptions();
    show(job.needs_review ? 'review' : 'options');
  } catch (e) { refused('تعذّر الاتصال بالخادم. أعد المحاولة.'); }
  finally { btn.disabled = false; btn.textContent = 'تابع'; }
};

// ---------- 2. review
function renderReview() {
  const s = job.summary, chips = $('#summary'); chips.innerHTML = '';
  [['عناوين رئيسية', s.h1], ['عناوين فرعية', s.h2], ['رؤوس مدمجة', s.h3], ['فقرات', s.paragraphs], ['حواشٍ', s.notes], ['جداول', s.tables]]
    .forEach(([k, v]) => { const c = document.createElement('span'); c.className = 'chip'; c.innerHTML = `${k} <b>${AR(v)}</b>`; chips.append(c); });
  const al = $('#review-alerts'); al.innerHTML = '';
  if (s.suggested) al.append(alertBox(`اقترحتُ دور ${AR(s.suggested)} من الأسطر (مظلَّلة)؛ راجعها.`, 'ok'));
  job.warnings.forEach(w => al.append(alertBox(w)));
  drawLines();
}
function drawLines() {
  const ol = $('#lines'); ol.innerHTML = '';
  const main = filter === 'main';
  job.items.forEach(it => {
    const editable = it.kind === 'text';
    if (main && (!editable || (roles[it.i] === 'p' && !it.suggested))) return;
    const li = document.createElement('li');
    if (!editable) {
      li.className = 'fixed';
      li.innerHTML = `<span class="kind"></span><span class="t"></span>`;
      $('.kind', li).textContent = FIXED[it.kind] || '';
      $('.t', li).textContent = it.text;
      return ol.append(li);
    }
    if (it.suggested) li.className = 'sug';
    const sel = document.createElement('select');
    sel.setAttribute('aria-label', 'دور السطر');
    ROLES.forEach(([v, l]) => { const o = document.createElement('option'); o.value = v; o.textContent = l; sel.append(o); });
    sel.value = roles[it.i];
    const t = document.createElement('div'); t.className = 't ' + roles[it.i]; t.textContent = it.text;
    if (it.refs) { const n = document.createElement('span'); n.className = 'why'; n.textContent = `فيه ${AR(it.refs)} من أرقام الحواشي، رُبطت بحواشيها`; t.append(n); }
    if (it.suggested && it.why) { const w = document.createElement('span'); w.className = 'why'; w.textContent = 'مقترح: ' + it.why; t.append(w); }
    sel.onchange = () => { roles[it.i] = sel.value; t.className = 't ' + sel.value; };
    li.append(sel, t); ol.append(li);
  });
  if (!ol.children.length) { const li = document.createElement('li'); li.className = 'fixed'; li.textContent = 'لا عناوين في نصك. اختر «كل الأسطر» لتحديدها.'; ol.append(li); }
}
$$('#filter button').forEach(b => b.onclick = () => { filter = b.dataset.f; $$('#filter button').forEach(x => x.classList.toggle('on', x === b)); drawLines(); });
$('#to-options').onclick = () => { renderOptions(true); show('options'); };
$$('[data-back]').forEach(b => b.onclick = () => show(b.dataset.back === 'review' && !job.needs_review ? 'review' : b.dataset.back));

// ---------- 3. options
function renderOptions(keep) {
  const a = job.analysis || {};
  $('#panel-line').textContent = job.panel;
  if (!keep) {
    seg($('#kind'), job.kind_hint);
    const heads = job.items.filter(it => it.kind === 'text' && ['h1', 'h2'].includes(roles[it.i])).length;
    seg($('#toc'), job.kind_hint !== 'article' || heads >= 5 || a.toc ? 'front' : 'none');
    $('#uthmani').checked = false; $('#verse-index').checked = false; $('#header').checked = false;
    seg($('#font'), 'lotus');
  }
  const al = $('#options-alerts'); al.innerHTML = '';
  if (!job.needs_review) job.warnings.forEach(w => al.append(alertBox(w)));
  $('#verses-box').hidden = !a.verses;
  $('#verses-count').textContent = a.verses ? `(${AR(a.verses)} في نصك)` : '';
  $('#symbols-box').hidden = !job.symbols;
  if (job.symbols && !keep) $('#symbols').checked = true;
  const sources = job.items.some(it => it.kind === 'text' && roles[it.i] === 'h1' && /المصادر|المراجع/.test(it.text));
  $('#sort-box').hidden = !sources;
  const chips = $('#ai-chips'); chips.innerHTML = '';
  [['أحاديث', a.hadith], ['إحالات في الحواشي', a.citations], ['أبيات شعر', a.poetry]].forEach(([k, v]) => {
    if (v) { const c = document.createElement('span'); c.className = 'chip'; c.innerHTML = `${k} في نصك <b>${AR(v)}</b>`; chips.append(c); }
  });
  $$('#kind button')[2].disabled = !job.trad; $$('#font button')[1].disabled = !job.trad;
  kindChanged();
}
const KIND_HINT = {
  article: 'مقال بلا غلاف: عنوانه في رأس الصفحة الأولى ويليه النص، وعناوينه الكبرى تأتي بعد ما قبلها بمسافة.',
  paper: 'بحث بغلاف: غلاف من بيانات البحث، ويبدأ كل عنوان رئيسي صفحةً جديدة.',
  thesis: 'رسالة ماجستير أو دكتوراه بدليل جامعة الملك خالد: صفحة العنوان، والأوائل بالحروف، وقائمة المحتويات على النموذج ٥.',
};
function kindChanged() {
  const k = segVal($('#kind')) || 'article';
  $('#kind-hint').textContent = KIND_HINT[k];
  $('#cover-box').hidden = k !== 'paper';
  $('#thesis-box').hidden = k !== 'thesis';
  $('#aw-box').hidden = k !== 'thesis';
  $('#font-box').hidden = k === 'thesis';
  const opening = (job.analysis || {}).basmala;
  $('#basmala-box').hidden = !(opening || (k === 'thesis' && $('#t-basmala').checked));
}
$$('.seg[id] button').forEach(b => b.addEventListener('click', () => {
  if (b.disabled) return; seg(b.parentElement, b.dataset.v); if (b.parentElement.id === 'kind') kindChanged();
}));
$('#t-basmala').onchange = kindChanged;

function options() {
  const kind = segVal($('#kind'));
  const o = {
    kind, roles, toc: segVal($('#toc')),
    uthmani: $('#uthmani').checked, verse_index: $('#verse-index').checked,
    header: $('#header').checked, font: segVal($('#font')),
    basmala: +$('#basmala').value || 0, symbols: $('#symbols').checked && job.symbols,
    sort_sources: !$('#sort-box').hidden && $('#sort').checked,
  };
  if (kind === 'paper') o.cover = { title: $('#c-title').value, author: $('#c-author').value, affiliation: $('#c-affiliation').value, date: $('#c-date').value };
  if (kind === 'thesis') {
    o.thesis = {};
    ['title', 'college', 'department', 'degree', 'field', 'author', 'supervisor', 'date'].forEach(k => o.thesis[k] = $('#t-' + k).value);
    o.thesis.members = $('#t-members').value.split('\n').map(l => l.split('|')).filter(p => p[0].trim()).map(p => ({ name: p[0].trim(), role: (p[1] || '').trim() }));
    o.thesis.approval = $('#t-approval').checked; o.thesis.basmala_page = $('#t-basmala').checked;
    o.thesis.as_written = $$('.aw').filter(x => x.checked).map(x => x.value);
  }
  return o;
}

$('#go').onclick = async () => {
  const btn = $('#go'); btn.disabled = true;
  try {
    const logo = $('#t-logo').files[0];
    if (segVal($('#kind')) === 'thesis' && logo) {
      const fd = new FormData(); fd.append('file', logo);
      const r = await fetch(`/api/jobs/${job.id}/logo`, { method: 'POST', body: fd });
      if (!r.ok) { const j = await r.json(); btn.disabled = false; return $('#options-alerts').prepend(alertBox(j.detail || 'تعذّر رفع الشعار.', 'bad')); }
    }
    const r = await fetch(`/api/jobs/${job.id}/typeset`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(options()) });
    if (!r.ok) throw new Error(r.status);
    show('result'); $('#working').hidden = false; $('#done').hidden = true; $('#failed').hidden = true;
    clearInterval(poll); poll = setInterval(check, 1500);
  } catch (e) { $('#options-alerts').prepend(alertBox('انتهت مدة هذا الملف أو تعذّر الاتصال. أرسل نصك من جديد.', 'bad')); }
  finally { btn.disabled = false; }
};

// ---------- 4. result
async function check() {
  const r = await fetch(`/api/jobs/${job.id}`);
  if (!r.ok) { clearInterval(poll); return failed({ error: 'انتهت مدة هذا الملف. أرسل نصك من جديد.' }); }
  const s = await r.json();
  if (s.state === 'running') { $('#elapsed').textContent = s.elapsed ? `(${AR(s.elapsed)} ث)` : ''; return; }
  clearInterval(poll);
  if (s.state === 'done') done(s.results); else failed(s.error || {});
}
function failed(e) {
  $('#working').hidden = true; $('#failed').hidden = false;
  const m = $('#fail-msg'); m.textContent = e.error || 'لم يكتمل الصفّ.';
  if (e.detail) { const s = document.createElement('small'); s.textContent = e.detail; m.append(s); }
}
function done(res) {
  $('#working').hidden = true; $('#done').hidden = false;
  const base = `/api/jobs/${job.id}/files/`;
  $('#dl-pdf').href = base + 'pdf'; $('#dl-docx').href = base + 'docx'; $('#dl-fonts').href = base + 'fonts';
  const list = (el, arr) => { el.innerHTML = ''; arr.forEach(t => { const li = document.createElement('li'); li.textContent = t; el.append(li); }); };
  list($('#always'), res.always); list($('#word-notes'), res.word_notes);
  const al = $('#result-msgs'); al.innerHTML = ''; res.messages.forEach(m => al.append(alertBox(m.text, m.level === 'info' ? 'ok' : '')));
  $('#pages-count').textContent = `(${AR(res.pages)} صفحة)`;
  const g = $('#pages'); g.innerHTML = '';
  for (let n = 1; n <= Math.min(res.pages, 80); n++) {
    const f = document.createElement('figure'); f.style.margin = 0;
    const b = document.createElement('button'); b.setAttribute('aria-label', `الصفحة ${AR(n)}`);
    const img = document.createElement('img'); img.loading = 'lazy'; img.src = `/api/jobs/${job.id}/pages/${n}`; img.alt = `الصفحة ${AR(n)}`;
    b.append(img); b.onclick = () => openPage(n);
    const c = document.createElement('figcaption'); c.textContent = AR(n);
    f.append(b, c); g.append(f);
  }
}
function openPage(n) { const d = $('#viewer'); $('img', d).src = `/api/jobs/${job.id}/pages/${n}?big=1`; d.showModal(); }
$('#close-viewer').onclick = () => $('#viewer').close();
$('#viewer').addEventListener('click', e => { if (e.target.id === 'viewer') e.target.close(); });
$('#again').onclick = () => { job = null; fileIn.value = ''; fileIn.onchange(); $('#text').value = ''; $('[data-tab=file]').click(); show('send'); };
$('#delete').onclick = async () => {
  if (!confirm('أتحذف ملفاتك من الخادم الآن؟')) return;
  await fetch(`/api/jobs/${job.id}`, { method: 'DELETE' });
  job = null; show('send'); refused(''); $('#refused').hidden = false; $('#refused').className = 'alert ok'; $('#refused').textContent = 'حُذفت ملفاتك من الخادم.';
};
show('send');

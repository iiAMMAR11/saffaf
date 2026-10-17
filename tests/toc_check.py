import re, zipfile, unicodedata, pdfplumber, sys
D=str.maketrans('٠١٢٣٤٥٦٧٨٩','0123456789')
def L(s): return re.sub(r'[^ء-ي]','',unicodedata.normalize('NFKC',s))
def G(s): return ''.join(sorted(re.sub(r'\D','',s.translate(D))))
for base in sys.argv[1:]:
    with pdfplumber.open(base+'.pdf') as d:
        pages=[]
        for p in d.pages:
            t=p.extract_text() or ''
            pages.append(None if '..........' in t else {(''.join(sorted(L(l))),G(l)) for l in t.split('\n')})
    doc=zipfile.ZipFile(base+'.docx').read('word/document.xml').decode()
    ent=[]
    for p in re.findall(r'<w:p>.*?</w:p>',doc):
        if 'w:leader="dot"' in p:
            t=''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>',p)); title,_,pg=t.rpartition('\t'); ent.append((title,int(pg.translate(D))))
    bad=0
    for title,pg in ent:
        if title=='فهرس الموضوعات':
            ok = pages[pg-1] is None
        else:
            hits=[i+1 for i,s in enumerate(pages) if s and (''.join(sorted(L(title))),G(title)) in s]
            ok = bool(hits) and hits[0]==pg
            if not ok: print('  MISMATCH',title,'toc=',pg,'actual=',hits)
        bad += not ok
    print(f'{base}: {len(ent)} TOC entries, {bad} wrong, {len(pages)} pages')

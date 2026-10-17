import pdfplumber, sys, unicodedata
# every Arabic letter must be set in Lotus Lotfi, or in the Quran font (verses in Uthmani script);
# other fonts may only carry the designed fallback (Latin runs, symbols)
for f in sys.argv[1:]:
    n = 0; bad = 0; quran = 0; fonts = set()
    with pdfplumber.open(f) as d:
        for p in d.pages:
            for c in p.chars:
                if any('ء' <= ch <= 'ي' for ch in unicodedata.normalize('NFKC', c['text'])):
                    n += 1
                    if 'KFGQPC' in c['fontname']: quran += 1
                    elif 'LotusLotfi' not in c['fontname']: bad += 1; fonts.add(c['fontname'].split('+')[-1])
    print(f'{f}: {n} Arabic letters, {bad} not in Lotus Lotfi, {quran} in the Quran font' + (' (' + ', '.join(sorted(fonts)) + ')' if fonts else ''))

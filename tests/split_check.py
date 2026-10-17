import pdfplumber, sys, collections, re
# A reference split across two lines leaves a line with an unbalanced bracket. LibreOffice can break at the edge of a
# number, e.g. «(ت: ٧٥١» | «هـ)» (a known limit); what must never happen is a break at the space inside the reference,
# which leaves the opening part ending in «:» or «/».
for f in sys.argv[1:]:
    n = 0; lines = 0; at_space = 0
    with pdfplumber.open(f) as d:
        for p in d.pages:
            rows = collections.defaultdict(list)
            for c in p.chars:
                if c['top'] > p.height - 140: continue      # skip footer/footnotes zone
                rows[round(c['top'] / 4)].append(c['text'])
            for k, cs in rows.items():
                s = ''.join(cs); lines += 1
                if (s.count('(') != s.count(')')) or (s.count('[') != s.count(']')):
                    n += 1
                    if re.search(r'[\(\[][^\(\)\[\]]*[:/][\s ]*$', s): at_space += 1
    print(f'{f}: {lines} lines, {n} with a split reference, {at_space} split at its space')

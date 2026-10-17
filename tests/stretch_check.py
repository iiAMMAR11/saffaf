"""usage: stretch_check.py justified.pdf ragged.pdf  — the same text set by the same engine, justified and not.
Justifying a line may move its words apart; it must never widen a word. A kashida the engine inserts to fill a line
is drawn as extra glyphs that carry no character (a count of U+0640 characters finds nothing), so the words are
measured instead: no word of the justified PDF may be wider than the same word is in the unjustified one.
A word is known by its glyphs (the advance width of each, in order), not by the text the PDF reports for them, which
is not the same from one file to the next."""
import sys, pdfplumber

def measure(pdf):
    """-> ([(glyph widths, width of the word, word as the PDF reports it)], number of lines that reach the far text edge)"""
    words = []; full = 0
    with pdfplumber.open(pdf) as d:
        for p in d.pages:
            rows = {}   # the glyphs of one line in one size share their top exactly; marks (no width) sit elsewhere and are left out
            for c in p.chars:
                if c['width'] >= 0.5: rows.setdefault((round(c['top'], 1), round(c['size'], 1)), []).append(c)
            for row in rows.values():
                row.sort(key=lambda c: c['x0']); word = []
                full += len(row) > 30 and row[0]['x0'] < 72.5
                for c in row + [None]:
                    # a word ends at a space, at a gap (a tab), or with the line
                    if c is None or c['text'].isspace() or (word and c['x0'] - word[-1]['x1'] > 1):
                        if word: words.append((tuple(g['width'] for g in word), word[-1]['x1'] - word[0]['x0'], ''.join(g['text'] for g in word)))
                        word = []
                    if c is not None and not c['text'].isspace(): word.append(c)
    return words, full

def stretched(just, natural, tol=0.3):
    """The words of `just` that are not found among `natural`, glyph for glyph and no wider. (A little narrower is
    not stretching: some LibreOffice versions tighten a line by a fraction of a point to fit it.)"""
    known = {}
    for glyphs, w, _ in natural: known.setdefault(len(glyphs), []).append((glyphs, w))
    same = lambda a, b: all(abs(x - y) < 0.05 for x, y in zip(a, b))
    return [(w, t) for glyphs, w, t in just if not any(-1 < w - n < tol and same(glyphs, g) for g, n in known.get(len(glyphs), []))]

if __name__ == '__main__':
    just, full = measure(sys.argv[1]); natural, _ = measure(sys.argv[2]); wide = stretched(just, natural)
    print(f'{full} justified lines, {len(just)} words ({len(natural)} unjustified), {len(wide)} stretched'
          + (' — ' + '  '.join(f'{t[::-1]} {w:.1f}' for w, t in wide[:6]) if wide else ''))

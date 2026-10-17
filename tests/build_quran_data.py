#!/usr/bin/env python3
"""Build the skill's compact Quran file from the two source files in tests/quran-source/ (see SOURCE.md there).
Nothing in the text is changed: the file only drops what the skill does not use (ids, keys, word numbers and the
closing ayah number, which is the ayah's own number). `load()` is what the test uses to compare the two, ayah by ayah.

    python3 tests/build_quran_data.py        # rewrites skill/saffaf/assets/quran/quran.txt.xz

Format (UTF-8 text, xz-compressed): one line per ayah in Quran order — the imlāʾī text, then each Uthmani word,
separated by tabs; an empty line between surahs."""
import json, lzma, os

T = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(T, 'quran-source')
OUT = os.path.join(T, '..', 'skill', 'saffaf', 'assets', 'quran', 'quran.txt.xz')
HINDI = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')

def raw(name):
    """A source file as obtained (the repository keeps it xz-compressed; this is the original JSON, byte for byte)."""
    return lzma.open(os.path.join(SRC, name + '.xz'), 'rb').read()

def load():
    """-> [(surah, ayah, imlāʾī text, [Uthmani words incl. the closing ayah number])] exactly as the sources have them."""
    im = json.loads(raw('imlaei-script-ayah-by-ayah.json'))
    words = {}
    for v in json.loads(raw('qpc-hafs-word-by-word.json')).values():
        words.setdefault((int(v['surah']), int(v['ayah'])), []).append((int(v['word']), v['text']))
    return [(v['surah'], v['ayah'], v['text'], [t for _, t in sorted(words[(v['surah'], v['ayah'])])]) for v in im.values()]

if __name__ == '__main__':
    lines = []; prev = None
    for s, a, imlaei, uthmani in load():
        assert uthmani[-1] == str(a).translate(HINDI), (s, a)           # the last "word" is only the ayah number
        assert not any(c in t for t in [imlaei] + uthmani for c in '\t\n')
        if prev not in (None, s): lines.append('')
        prev = s; lines.append('\t'.join([imlaei] + uthmani[:-1]))
    with lzma.open(OUT, 'wb', preset=9 | lzma.PRESET_EXTREME) as f: f.write(('\n'.join(lines) + '\n').encode('utf-8'))
    print(len(lines) - 113, 'ayahs ->', os.path.normpath(OUT), os.path.getsize(OUT), 'bytes')

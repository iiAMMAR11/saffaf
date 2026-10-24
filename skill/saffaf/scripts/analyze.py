#!/usr/bin/env python3
"""Read a draft (in.md, from to_md.py) and say what the settings panel should offer the user.
usage: python3 analyze.py draft.md      -> a short report, in English, for Claude (not for the user)

Nothing is changed. The counts are hints for the panel: which options apply to this text, and what to suggest."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import indexes

def facts(path):
    """What the draft holds, as data: the same counts the report below prints."""
    text = open(path, encoding='utf-8').read()
    lines = text.split('\n')
    front = lines[0].strip() == '---'
    if front: lines = lines[lines.index('---', 1) + 1:] if '---' in lines[1:] else lines
    body = [l for l in lines if l.strip() and not re.match(r'^\[\^[^\]]+\]:', l)]
    notes = [re.sub(r'^\[\^[^\]]+\]:\s*', '', l) for l in lines if re.match(r'^\[\^[^\]]+\]:', l)]
    h1 = [l for l in body if l.startswith('# ')]; h2 = [l for l in body if l.startswith('## ')]
    first = next((l for l in body if not l.startswith('@')), '')
    return dict(
        cover=front,
        words=len(re.findall(r'[ء-ي]+', text)),
        h1=len(h1), h2=len(h2),
        notes=len(notes),
        latin_notes=sum(1 for n in notes if len(re.findall(r'[A-Za-z]', n)) > len(re.findall(r'[ء-ي]', n))),
        toc='@toc' in text,
        basmala=indexes.is_basmala(first),
        sources_heading=any(re.search(r'المصادر|المراجع|Bibliography|References', l) for l in h1 + h2),
        verses=len(re.findall(r'﴿[^﴿﴾]+﴾', text)) + len(re.findall(r'(?:قال|قوله|يقول)\s+(?:الله|تعالى|سبحانه)[^«»"]{0,40}[«"]', text)),
        hadith=len(re.findall(r'(?:قال|أن|سمعت|عن)\s+(?:رسول الله|النبي)\s*(?:ﷺ|صلى الله عليه وسلم)?[^«»]{0,20}«', text)),
        poetry=sum(1 for l in body if re.search(r'\*\*\*|…\s*…|\.\.\.\s{2,}', l)),
        citations=sum(1 for n in notes if re.search(r'[٠-٩0-9]+\s*/\s*[٠-٩0-9]+|\bص\s*[٠-٩0-9]|\bpp?\.\s*\d|\(\s*ت\s*:', n)),
    )

def main(path):
    f = facts(path)
    words, h1, h2, notes, latin_notes = f['words'], f['h1'], f['h2'], f['notes'], f['latin_notes']
    front, verses, hadith, poetry, cites, bib = f['cover'], f['verses'], f['hadith'], f['poetry'], f['citations'], f['sources_heading']
    basmala = f['basmala']
    print(f'kind: {"research paper (has a cover block)" if front else "article (no cover block)"} | Arabic words: {words} | headings: {h1} level 1, {h2} level 2 | footnotes: {notes} ({latin_notes} in Latin letters)')
    print(f'has a contents line (@toc): {f["toc"]} | opens with the basmala: {basmala} | a list of sources under its own heading: {bib}')
    print(f'verses marked by the author: {verses} | sayings of the Prophet quoted («» after «قال رسول الله» …): {hadith} | lines that look like poetry: {poetry}')
    print(f'footnotes that look like citations (volume/page): {cites}')
    print('offer: font (Lotus Lotfi | Traditional Arabic); running header with the title; contents (front | end | none)'
          + ('; Uthmani script for the verses' if verses else '')
          + ('; the opening basmala as one of the 7 Lotus basmalas' if basmala else '')
          + ('; a citation style (as written | Chicago | APA | Harvard | MLA)' if cites else '')
          + '; indexes: ' + ', '.join(k for k in indexes.KINDS if k not in ('مصدر',) and (k != 'آية' or verses) and (k != 'حديث' or hadith) and (k != 'شعر' or poetry))
          + ('، مصدر (with a citation style)' if cites else ''))

if __name__ == '__main__':
    if '--json' in sys.argv:
        import json
        print(json.dumps(facts([a for a in sys.argv[1:] if not a.startswith('--')][0]), ensure_ascii=False))
    else: main(sys.argv[1])

# Symbols font — source

The font for the honorific signs and ligature words that Lotus Lotfi does not have at their standard code points: ﷻ (U+FDFB), ﷽ (U+FDFD), the signs U+FD40–U+FD4F such as ﵁ (U+FD41), and any other character of U+FD00–U+FDFF that Lotus lacks. Only those characters are set in it; the author's characters stay as written. Do not edit, re-save, subset or reformat these files.

| File | What it is | Source |
|---|---|---|
| `NotoNaskhArabic-Regular.ttf` | Noto Naskh Arabic, version 2.021 (hinted), exactly as published — SHA-256 `6f0a92031367b2f5a2078fe9d24f3433122b61a0bad57c423aad8f3c39aa2e6e` | The Noto Project, release `NotoNaskhArabic-v2.021` of github.com/notofonts/arabic (2026-01-16), file `NotoNaskhArabic/hinted/ttf/NotoNaskhArabic-Regular.ttf` of `NotoNaskhArabic-v2.021.zip` |
| `OFL.txt` | The font's licence, from the same release zip | same |

## Why this font
Its own character map covers every one of U+FDFB, U+FDFD and U+FD40–U+FD4F (checked from the cmap). Amiri 1.003 was checked first: it has U+FDFB and U+FDFD but none of U+FD40–U+FD4F.

## Licence
SIL Open Font License, version 1.1 (`OFL.txt`); copyright 2022 The Noto Project Authors. It may be used, bundled and redistributed freely, not sold by itself, and must travel with its licence, so `make.py` puts `OFL.txt` in the fonts zip whenever it adds the font. It is not covered by this project's MIT licence.

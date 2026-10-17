# Quran source texts

The two files as obtained on 2026/10/13 from QUL (qul.tarteel.ai), unmodified, each kept here xz-compressed
(`<name>.json.xz`). They are not shipped with the skill: `tests/build_quran_data.py` builds the skill's compact file
from them, and the tests unpack them in memory and compare that file with them, ayah by ayah.

The checksums below are those of the original JSON files, i.e. of each file after unpacking; the tests check them.

| File | What it is | SHA-256 |
|---|---|---|
| `qpc-hafs-word-by-word.json` | Uthmani text, word by word (keys `surah:ayah:word`); the edition of the King Fahd Glorious Quran Printing Complex | `f366269234e24f322146c043fe5fbf0132990613a94aff4b3f23847f45793ea7` |
| `imlaei-script-ayah-by-ayah.json` | Imlāʾī text, ayah by ayah (keys `surah:ayah`) | `2e31ac4b4e2f51e4583aa8f781ac4027ca36b639b3b0c2c44cbbb0e2de8bff04` |

Each of the two texts has 6236 ayahs. They are not covered by this project's MIT licence.

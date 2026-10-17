# Quran assets — sources

Material for setting Quran verses in Uthmani script. Do not edit, re-save, subset or reformat these files.

| File | What it is | Source |
|---|---|---|
| `UthmanicHafs_V22.ttf` | Font «KFGQPC HAFS Uthmanic Script», version 2.2, released 2021 (the font's identifier, name ID 3, ends «KFGQPC HAFS Uthmanic Script Regular: 2021»; 2010 in its copyright notice is the copyright year). The file is exactly as published — SHA-256 `aa68bffce289b4c0ebac68e90502eb69e42356abcd1603cb2b8e99c2c723f145` | King Fahd Glorious Quran Printing Complex, Madinah — fonts.qurancomplex.gov.sa |
| `quran.txt.xz` | The two Quran texts the skill matches against each other: the imlāʾī text ayah by ayah and the Uthmani text word by word, 6236 ayahs each | QUL — qul.tarteel.ai (obtained 2026/10/13); the Uthmani text is the edition of the King Fahd Glorious Quran Printing Complex |

## The text file
`quran.txt.xz` is UTF-8 text, xz-compressed: one line per ayah in Quran order — the imlāʾī text, then each Uthmani word, separated by tabs — and an empty line between surahs. It holds the text of the two QUL files and nothing else: their ids, keys and word numbers are left out, and so is the number that closes each ayah in the Uthmani file (it is the ayah's own number). Not a letter or mark of the text is changed; the project's tests compare every ayah with the two source files.

## Font licence
The licence is embedded in the font itself (name-table record 13, «Electronic End-User License Agreement», © King Fahd Glorious Quran Printing Complex). It grants, free of cost, the rights to use, copy and distribute the font; the font may not be sold, modified or altered. It is not covered by this project's MIT licence.

## Licence of the two texts
Both texts are from the QUL library (qul.tarteel.ai); the Uthmani text is the edition of the King Fahd Glorious Quran Printing Complex. They are not covered by this project's MIT licence.

## Attribution
«خط الآيات: خط الرسم العثماني – حفص (KFGQPC HAFS Uthmanic Script)، من إصدار مجمع الملك فهد لطباعة المصحف الشريف بالمدينة المنورة، يُستخدم ويوزَّع مجانًا وفق رخصته دون تعديل. ونصّا المصحف من مكتبة QUL.»

# Spec (measured from the reference paper, translated to Lotus Lotfi)
| Element | Value |
|---|---|
| Page | A4, margins 2.5 cm all sides; header 1.25 cm, footer 1 cm |
| Body | Lotus Lotfi 16 pt, single line spacing (~30 pt pitch); ordinary paragraphs: first line indented 1 cm, no space after; justified by word spacing, no kashida (the Word file asks for this; in the PDF, LibreOffice before 25 still lengthens some letters) |
| Heading 1 (مبحث/مقدمة/خاتمة) | 18 pt bold, centered, 18 pt after. With a cover (a research paper): page break before. With no cover (an article): it follows the text before it, 36 pt (~1.5 lines) above — except the first one after the contents, which starts a new page |
| Heading 2 (مطلب) | 16 pt bold, half a line (12 pt) before, nothing after |
| Run-in head | 16 pt bold, keep with next |
| Bullets | • level 1 (Times), o level 2; hanging 0.7 cm |
| Numbered items | author's own «١-», beginning at the text edge, the text hanging 0.75 cm inward |
| Verse refs / death dates | 10.5 pt |
| Verses in Uthmani script (on request) | KFGQPC HAFS Uthmanic Script, same size as the surrounding text; the ﴿ ﴾ brackets stay in Lotus; its lines may be justified with kashida, as the Mushaf is |
| Footnotes | 13 pt, single spacing; in the note the number «(١)» sits on the line, beginning exactly at the text edge, and the text hangs 0.6 cm inward; the reference in the text is raised; restart each page, short separator (Word default) |
| Footnote with an unbreakable word (a link) | aligned to the start, not justified; no hidden break points are added |
| Latin footnote | mostly Latin letters → left to right, left aligned, Times New Roman, same hanging indent; its number is Western, «(1)», in the note's own Times, in Word and in every LibreOffice version |
| Article title (first heading 1, no cover) | at the head of page 1, ~4 lines (96 pt) above, ~3 lines (72 pt) below, the text following on the same page; a writer line «>>» right under it sits one line below the title with one line after it |
| Header | none (no running title at the top of pages, by design) |
| Page number | bare number centered at the bottom, 14 pt, Hindi digits; in Word it is spelled out by nested fields so it never depends on the reader's settings |
| Tables | full width, 0.75 pt black borders, header row #D9D9D9 bold, cells 14 pt; columns sized to content (no word breaks), a long last column takes the rest |
| Cover | title 20 bold centered ~6 cm down; lines 16; «إعداد:» + author bold + affiliation; date low |
| TOC | dot leaders, H1 bold, H2 indented 1 cm; it does not list itself. With a cover it has a page of its own; in an article with no cover it follows the title on page 1 and does not list the title, and the text starts on the next page |
| Latin | Times New Roman, 2 pt smaller than surrounding Arabic |
| Signs Lotus lacks (U+FD00–U+FDFF: ﷻ ﷽ ﵁ …) | Noto Naskh Arabic, character by character, same size; the characters stay as written |
| Digits | Hindi (١٢٣) — PDF via LibreOffice CTLTextNumerals=Context; Latin runs are marked English so their digits stay 123; in Word the automatic footnote numbers are decimal and follow Word's Numeral setting |
| Fonts in the Word file | Lotus Lotfi is not embedded (its «preview & print» permission makes Word open the file read-only where the font is missing); the fonts are delivered in one zip, «خطوط-لملف-Word.zip» (the two Lotus files always; the Quran font whenever a verse was set in Uthmani script; Noto Naskh Arabic with its licence whenever a sign was set in it). The Quran font is also embedded when used |

Rendering notes: Lotus Lotfi = Linotype Lotus modified by Lotfi El-Tokhi: conditional ligatures disabled when the first letter is voweled; Allah ligature from Shebli; marked alif maqsura (intentional); 239 Shebli ornament glyphs at U+1EE00–1EEF2 (not used in body — not searchable).

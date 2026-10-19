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
| Header | none by default. On request (`@header`): the title of the work, 13 pt, centred over a 0.5 pt rule, on every page but the first |
| Body font on request | Traditional Arabic (`--font=traditional`), same sizes and measures; Latin and signs it lacks as with Lotus |
| Opening basmala on request | one of Lotus Lotfi's seven basmalas (U+1EE00–U+1EE06), centred, about half the line wide, 18 pt after; one line above an article's title instead of four |
| Indexes (on request) | each on a new page, heading 1; entries 16 pt with dot leaders to the page numbers at the far edge, as in the contents; grouped under a bold centred line (حرف …، قافية …، سورة …); verses by surah in the Mushaf's order with their ayah numbers small; names, places and words ordered without «ال»; the list of sources with a 1 cm hanging indent, Latin sources left to right |
| Citation styles (on request) | Chicago (full note first, short after), APA and Harvard (author and year), MLA (author and short title); titles of whole works bold in Arabic, italic in Latin; article titles in «» (Arabic) or "" (Latin) |
| Page number | bare number centered at the bottom, 14 pt, Hindi digits; in Word it is spelled out by nested fields so it never depends on the reader's settings |
| Tables | full width, 0.75 pt black borders, header row #D9D9D9 bold, cells 14 pt; columns sized to content (no word breaks), a long last column takes the rest |
| Cover | title 20 bold centered ~6 cm down; lines 16; «إعداد:» + author bold + affiliation; date low |
| TOC | dot leaders, H1 bold, H2 indented 1 cm; it does not list itself; it lists the indexes. At the end on request. With a cover it has a page of its own; in an article with no cover it follows the title on page 1 and does not list the title, and the text starts on the next page |
| Latin | Times New Roman, 2 pt smaller than surrounding Arabic |
| Signs Lotus lacks (U+FD00–U+FDFF: ﷻ ﷽ ﵁ …) | Noto Naskh Arabic, character by character, same size; the characters stay as written |
| Digits | Hindi (١٢٣) — PDF via LibreOffice CTLTextNumerals=Context; Latin runs are marked English so their digits stay 123; in Word the automatic footnote numbers are decimal and follow Word's Numeral setting |
| Fonts in the Word file | Lotus Lotfi is not embedded (its «preview & print» permission makes Word open the file read-only where the font is missing); the fonts are delivered in one zip, «خطوط-لملف-Word.zip» (the two Lotus files always; the Quran font whenever a verse was set in Uthmani script; Noto Naskh Arabic with its licence whenever a sign was set in it). The Quran font is also embedded when used |

Rendering notes: Lotus Lotfi = Linotype Lotus modified by Lotfi El-Tokhi: conditional ligatures disabled when the first letter is voweled; Allah ligature from Shebli; marked alif maqsura (intentional); 239 Shebli ornament glyphs at U+1EE00–1EEF2 (not used in body — not searchable; only the seven basmalas U+1EE00–1EE06 are used, for the opening basmala on request).

## Thesis profile (`--profile=kku`, the King Khalid University guide)
Every value below is the guide's; what it leaves to the department (citation style, indexes) stays a panel choice.

| Element | Value |
|---|---|
| Font | Traditional Arabic throughout, the thesis title in PT Bold Heading; Latin in Times New Roman |
| Page | A4; margins top 2.5, bottom 2.5, left 2.5, right 3.5 cm (binding) |
| Body | 16 pt, 1.5 lines, justified, 1 cm first-line indent |
| Headings | heading 1: 20 bold centred, a new page; heading 2: 18 bold |
| Footnotes | as in the paper style (the guide leaves them to the department), numbered again on every page |
| Header | the title on request (`@header`), without the rule |
| Title page (model 1) | the kingdom, ministry, university, college and department lines at the top right; the logo (the user's image, 4 × 4 cm at most) at the top left; the title in PT Bold Heading 20 about 11 cm down (its one face is drawn bold, so no bold is added; Traditional Arabic bold if its file is missing); the degree statement, the author, the supervisor and the date below, at the guide's heights |
| Approval page (model 3) | the same top lines and logo; the title; «إجازة الرسالة»; the committee in a table (name, role, signature) at about 21 cm |
| Basmala page | one of Lotus Lotfi's seven basmalas, about 11 cm down |
| Page numbers | title, approval and basmala pages: none; prelims: letters from «ب» (أبجد); text: 1, 2, 3 … from the introduction; a part's page («الباب …»): no header, no number |
| Contents | «قائمة المحتويات», listing itself, the prelims with their letters, then the text, references, appendices and indexes |
| Lists of tables and figures | «قائمة الجداول» / «قائمة الأشكال»: every caption «جدول (١-١): …» / «شكل (١-١): …» with its page |
| Abstracts and acknowledgements | Arabic abstract and acknowledgements 14 pt, the abstract single-spaced; the English abstract left to right in Times; an abstract over 300 words or acknowledgements over a page are reported |
| References | a 1 cm hanging indent; Latin references left to right |
| Appendices | after the references; before each one a page «ملحق رقم (n)» with its title; the indexes after the appendices |

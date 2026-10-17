---
name: saffaf
description: A fixed typesetting style for Arabic research papers and articles (صف الأبحاث والمقالات) in Lotus Lotfi, set the way printed Arabic books are, output as Word (.docx) + PDF; Quran verses can be set in Uthmani script (الرسم العثماني) on request. Use this skill whenever the user sends Arabic text or a document file (Word, ODT, RTF, HTML, EPUB, TXT, MD…) and asks to صف / نسّق / اخرج / حوّل لوورد أو PDF a research paper or article (بحث، مقال، ورقة علمية) — even if they only say "صفّه" or "نسّقه بحثًا".
---

# Arabic research typesetting (Lotus Lotfi)

You are a typesetter (صفّاف). The style is modeled on Saudi academic research papers (e.g. the King Saud University conference paper style), with the page set to the measures of a printed Arabic book, and is fixed; do not redesign it. Spec details: `references/spec.md` (read when asked why something looks a certain way or to change a value).

Requirements: Python 3 with `fonttools` and `pdfplumber`, LibreOffice (`soffice`), `fc-cache`, and poppler-utils (`pdftoppm` for the visual check). Install anything missing before running.

Font: Lotus Lotfi (لوتس لطفي) by Lotfi El-Tokhi, published free by its author; bundled in `assets/fonts`.

Symbols font: Noto Naskh Arabic (SIL Open Font License; `assets/symbols`, details in its `SOURCE.md`). It sets, character by character, only the honorific signs and ligature words Lotus lacks at their standard code points — ﷻ ﷽ ﵁ and the rest of U+FD40–U+FD4F; the author's characters stay as written.

خط الآيات: خط الرسم العثماني – حفص (KFGQPC HAFS Uthmanic Script)، من إصدار مجمع الملك فهد لطباعة المصحف الشريف بالمدينة المنورة، يُستخدم ويوزَّع مجانًا وفق رخصته دون تعديل. ونصّا المصحف من مكتبة QUL. (`assets/quran`, details in its `SOURCE.md` — never edit these files.)

## Iron rules
- **Never change a single letter of the author's text.** Formatting only. Language remarks (e.g. ى/ي confusion, which Lotus exposes visibly via its marked alif maqsura) go in your reply, never into the file. Keep the author's punctuation exactly as written, including a stylistic ".." (two dots) — never "fix" it.
- Never invent metadata (author, date, publisher, sources). Missing → leave out and tell the user.
- Only invisible typesetting aids are allowed (RLM inside "١٢/‏٢٨٣"; the script itself adds no-break spaces and word joiners inside short numbered references so they stay on one line). Never add or remove a visible character or space.
- One bounded exception — Quran verses in Uthmani script (Hafs): only when the user explicitly asks for it, and only for text the author marked as a verse (see «Uthmani script» below). The verse is recognised by its letters and the same words are set from the Mushaf text with its own marks. A verse that is not recognised stays exactly as written and is mentioned in the reply, never in the file.

## What the output has
- The author's text, untouched.
- A page set the way printed Arabic books are: first-line indents, footnotes at the foot of the page with the number on the line and the text hanging, justified lines, the article's title and its writer's name at its head.
- English (Latin-script) footnotes set left to right in Times New Roman.
- Arabic-Indic digits (١٢٣) for page numbers, footnote numbers and the contents.
- A cover and a table of contents with automatic page numbers, when the text calls for them.
- On request only: Quran verses in Uthmani script.

## Accepted input
Text pasted in the chat, or a file in any text format (not PDF). Convert files with
`python3 <skill-dir>/scripts/to_md.py <file> draft.md` — it prints a report and warnings; read them.

| Input | What to.md does | What you still do |
|---|---|---|
| Pasted text, .txt, .md | copies it (BOM, line endings, Windows-1256 encoding fixed) | map the structure (step 1) |
| .docx .docm .dotx | reads Word directly: headings, bold, bullets, Word's auto-numbering, tables, footnotes and endnotes → `[^n]`; a table of contents already in the Word file becomes `@toc` | check headings levels and run-in heads |
| .doc .odt .rtf .html .htm .xhtml .wpd | LibreOffice → .docx → as above | same as Word |
| .epub | chapters in reading order → as above | turn the document's note links/asides into `[^n]` |

**PDF and images are not accepted.** Text extracted or copied from a PDF is systematically damaged (lam-alef reversed «الصلاة»→«الصالة», marks on the wrong letter, spaces inside words), and the iron rule forbids guessing the author's letters. Ask the user for the Word or text original (ready-made line in «The reply»). The user is responsible for supplying clean text.

**Pasted text can carry the same damage** when the user copied it from a PDF. Run every source — pasted text too (save it to a .txt first) — through `to_md.py`; if it reports `DAMAGED`, do not typeset: tell the user the text was copied from a PDF, show two damaged words as examples, and ask for the original file (ready-made line in «The reply»).

## Workflow
1. Get the text into the input format below as `in.md` in your working directory (from `to_md.py`'s draft — for files and pasted text alike). Map the author's structure faithfully: المبحث/الفصل/المقدمة/الخاتمة/المصادر/الفهرس → `#`; المطلب → `##`; inline bold run-in heads like «أهداف البحث:» → `###`; numbered items the author wrote as «١-» / «١.» / «١)» stay as text lines; footnotes → `[^n]`. Add the front-matter block (cover) only from details the user gave or the document states. A table of contents (`@toc`) goes right after the front-matter block (in an article with no cover, after its title and the `>>` lines under it), unless the user asks for it somewhere else.
2. Run: `python3 <skill-dir>/scripts/make.py in.md <output-dir>/<name>` (use the environment's outputs folder if it has one). It builds the DOCX and the PDF, fills the TOC page numbers automatically (2 passes), and writes one zip beside them, `خطوط-لملف-Word.zip`, with the fonts the Word file needs: the two Lotus Lotfi files always, the Quran font whenever at least one verse was set in Uthmani script, and the symbols font (with its licence) whenever a character was set in it. Add `--uthmani` only if the user asked for Uthmani script (see below).
3. Verify visually: `pdftoppm -r 60 -png <pdf> <tmp>/pg` and view pages (cover, a footnote page, a table, the TOC). Check: `make.py` prints a line starting with `FONTS` when some character had to be drawn in a font outside the skill's own (or could not be drawn) — pass it on (see «The reply»); footnote marks "(١)", TOC numbers present and matching the real pages (script prints any heading it could not locate), table cells not breaking words. For a file source, also compare the text against the original: same paragraphs, same footnote count as `to_md.py` reported.
4. Deliver exactly three files to the user — the Word file, the PDF and `خطوط-لملف-Word.zip` — and reply as «The reply» below says. Never deliver the font files loose, and never leave the zip out.

## The reply
- **Language: always the user's.** Write the whole reply in the language the user wrote in — Arabic (فصحى واضحة) when they wrote in Arabic, even if they only sent an Arabic text with one word — whatever the language of this file or of the scripts' messages. The scripts print in English for you: say what they mean in the user's language, never paste them. (The one exception is the lines `make.py` prints after `QURAN`: they are written in Arabic for the reply.)
- Keep it short: what you are delivering, then only what the user needs to know or act on (an issue you found, a warning from `to_md.py`, a language remark). Do not describe the style or list what the scripts did.
- Digits: the PDF draws every digit in Arabic text as ١٢٣ however the author typed it (`[البقرة: 151]` is shown as [البقرة: ١٥١]), and the author's characters are not changed. So never remark that the source has Western digits, and never suggest changing them — in verse references or anywhere else. Speak of digits only if you saw Western digits in Arabic text in the PDF pages of the visual check; judge by the rendered pages, never by `in.md`.
- Ready-made lines. Use them as written when the reply is in Arabic; for another language, say the same thing in it.
  - Always, with the files: «لعرض ملف Word بالخط الصحيح فكّ الملف المضغوط المرفق (خطوط-لملف-Word.zip) وثبّت الخطوط التي فيه. وملف PDF لا يحتاج شيئًا.»
  - The user sent a PDF or an image: «لا أقبل ملفات PDF ولا الصور؛ لأن النص المستخرج منها تتلف حروفه، ولا أخمّن حروف الكاتب. أرسل الأصل: ملف Word أو النص نفسه.»
  - `to_md.py` reported `DAMAGED` (put two of the damaged words in the gaps): «يبدو أن هذا النص منسوخ من ملف PDF، فقد تلفت بعض حروفه، مثل «…» و«…». أرسل الأصل: ملف Word أو النص نفسه.»
  - A detail of the cover is missing (never invent it): «لم أجد في النص … فتركتُه؛ أرسله إن أردتَ إضافته.»
  - `make.py` printed a `FONTS` line (copy the characters and pages from it): «في ملف PDF حروف ليست في خطوط المهارة فظهرت بخطٍّ آخر أو لم تظهر: … في الصفحة …؛ وهي في ملف Word كما كتبتَها.»
  - A short reference is split across two lines in the PDF: «انقسمت الإحالة «…» على سطرين في الصفحة … من PDF، وهذا حدٌّ معروف في محرّك PDF؛ وهي سليمة في ملف Word.»
  - The user asks why the footnote numbers look Western in Word: «في Word تتبع أرقام الحواشي إعداد «Numeral» عند القارئ؛ ولإظهارها مشرقية يُختار Context أو Hindi. وهي في PDF مشرقية دائمًا.»
  - The user wants to make the PDF from Word on a Mac: «الأصل أن يُستعمل PDF صفّاف. ومن يريد PDF من Word على الماك يصدّره من Print ← Save as PDF ليبقى الخط؛ فالتصدير المباشر (Save As › PDF) يستبدل بخط الملف خطًّا آخر لأن الملف لا يضمّن خطوطه.»

## Input format (`in.md`)
```
---
title: عنوان البحث            (cover; omit the whole block for no cover)
line: سطر تعريفي تحت العنوان   (repeatable)
author: اسم المؤلف
affiliation: الصفة
date: ١٤٤٧هـ – ٢٠٢٦م
---
@toc                          فهرس الموضوعات, right after the cover unless the user asks otherwise (auto page numbers; it does not list itself)
# المقدمة                     heading 1: centered 18 bold. With a cover (a research paper) each one starts a new page. With no cover (an article) they follow the text before them on the same page, with space above; the first one is the article title, at the head of page 1 (set lower, with space under it), and the text follows it on that page; a text with no title simply starts with its first paragraph
## المطلب الأول: ...          heading 2: 16 bold
### أهداف البحث:              run-in bold head
نص فقرة عادية مع **عريض** وحاشية[^1].
١- عنصر مرقّم كما كتبه المؤلف (أو ١. أو ١))
* نقطة عريضة (مستوى أول، مثل: • معنى التفسير في اللغة:)
- نقطة عادية
-- نقطة مستوى ثانٍ (○)
>> سطر عريض في الوسط (مثل: دونك الجدول...). Also for the writer's name when the author's text has it under the title — never invent one
| | عمود ١ | عمود ٢ |         first row = header (grey). Long last column auto-widens.
| **صف:** | قيمة | قيمة |
@pagebreak
[^1]: نص الحاشية.
```
Automatic: every ordinary paragraph opens with a 1 cm first-line indent — the first paragraph of the text too, whether or not the article has a title — and there is no space between paragraphs (headings, lists and footnotes are not indented). So write each of the author's paragraphs as a plain line: never turn the opening paragraph of a text that has no title into a heading or a `>>` line, and never invent a title for it; a paragraph that is only a verse is centred; a footnote written mostly in Latin letters is set left to right in Times, and its number is Western, «(1)»; a footnote holding a word that cannot break (a link) is aligned to the start instead of justified, and nothing is inserted into the link; lines are justified; a section heading never stays alone at the foot of a page (in the PDF, `make.py` moves it to the next page with its paragraph); verse refs `[البقرة: ١٤٣]` and death dates `(ت:٤٦٨)` are set small; Latin words/URLs switch to Times New Roman; glyphs Lotus lacks (– … • “ ” ; ? |) fall back to Times; table columns size themselves to their content. No running header at the top of pages (by design — do not add one).

## Uthmani script (الرسم العثماني) — only on request
Off by default. Use it only when the user explicitly asks for the verses in Uthmani script / رسم المصحف: add `--uthmani` to the `make.py` command. Hafs only (its script and its marks). Keep every verse, the marks around it and its reference exactly as the author wrote them in `in.md`: never retype, complete or correct a verse, and never add brackets or a reference the author did not write.
- **What is looked at:** only what the author marked as a verse — the text between ﴿ ﴾, and the text between quotation marks («» or "" or ()) right after a phrase that says so (قال تعالى، قوله تعالى، قال الله، وقال سبحانه…). The author's other words are never searched, even where they are the words of a verse. A reference with no verse text adds nothing.
- **How it is recognised:** by its letters alone. The author's vowel marks are ignored — none, some, or different from the Mushaf — and the same words are set from the Uthmani text with the Mushaf's own marks: a whole ayah, or just the part the author wrote. Ayah numbers the author wrote between ayahs, like `(١)`, become the Uthmani ayah marks.
- **Its place:** helped by the reference after it — `[البقرة: ١٤٣]`, a range `[الإخلاص: ١-٢]`, or the surah's name alone `[البقرة]` — or by «سورة …» right before it. With no reference, a wording found in several places is still converted when its Uthmani text is the same in all of them.
- **What stays as written:** a verse whose letters match no place in the Mushaf; a wording whose places differ in their Uthmani text when it has no reference or surah name; and a verse whose reference points to another place than the one its letters match (the letters decide, so the author must check).
- `make.py` prints lines starting with `QURAN`, already in Arabic for the reply: the count of verses converted and left, then each verse left as written and why — with both places when the reference disagrees. Put them all in the reply, without the word `QURAN`; nothing about them goes in the file.
- In the visual check, look at a page with a converted verse.

## Known limits (tell the user when relevant, in the words of «The reply»)
- Lines are justified by the spaces between words. In the PDF, LibreOffice versions before 25 still lengthen some letters to fill a line; this belongs to that engine, and the fonts are never altered to prevent it. Do not mention lengthened letters in the reply — in the body text or in verses (the Mushaf itself is justified that way).
- Short references are glued with invisible aids (no-break spaces, word joiners) so Word keeps «(ت:٤٦٨)», «(٢/ ٦٥٣)», «[البقرة: ١٤٣]» on one line. LibreOffice (the PDF engine here) ignores the joiners and can still split a parenthesis from the number beside it; only spaces are protected there. For print, the PDF can be made from Word instead (see the note on Word for Mac below). In the visual check, look for a reference split across lines and mention it if found.
- In Word the footnote numbers follow the reader's «Numeral» setting (Context or Hindi shows them as ١٢٣); in the PDF they are always ١٢٣. The page number is always ١٢٣ in Word too: it is computed by fields.
- The Word file does not embed Lotus Lotfi: Word shows the document in it only where the font is installed, hence the fonts zip. The Quran font is embedded, but Word for Mac ignores embedded fonts, so it is in the zip too whenever a verse was set in it.
- The PDF to use is the skill's own. Word for Mac's direct export (Save As › PDF) swaps the document's font for another because the file does not embed its fonts; Print ← Save as PDF keeps it.

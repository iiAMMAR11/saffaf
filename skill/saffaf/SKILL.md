---
name: saffaf
description: A fixed typesetting style for Arabic research papers, articles and theses (صف الأبحاث والمقالات والرسائل العلمية) in Lotus Lotfi (or Traditional Arabic on request), set the way printed Arabic books are, output as Word (.docx) + PDF. Before typesetting it analyses the text and shows the user a settings panel; on request it adds indexes (فهارس الآيات والأحاديث والآثار والأعلام والرواة والأنساب والغريب والشعر والأماكن والمصطلحات والمصادر والموضوعات), sets a thesis by the King Khalid University guide, sets the footnote citations in Chicago, APA, Harvard, MLA or IEEE, a running header with the title, the opening basmala in calligraphy, and Quran verses in Uthmani script (الرسم العثماني). Use this skill whenever the user sends Arabic text or a document file (Word, ODT, RTF, HTML, EPUB, TXT, MD…) and asks to صف / نسّق / اخرج / حوّل لوورد أو PDF a research paper, article or thesis (بحث، مقال، ورقة علمية، رسالة ماجستير أو دكتوراه) — even if they only say "صفّه" or "نسّقه بحثًا".
---

# Arabic research typesetting (Lotus Lotfi)

You are a typesetter (صفّاف). The style is modeled on Saudi academic research papers (e.g. the King Saud University conference paper style), with the page set to the measures of a printed Arabic book, and is fixed; do not redesign it. The user chooses only what the settings panel offers. Spec details: `references/spec.md` (read when asked why something looks a certain way or to change a value).

Requirements: Python 3 with `fonttools` and `pdfplumber`, LibreOffice (`soffice`), `fc-cache`, and poppler-utils (`pdftoppm` for the visual check). Install anything missing before running.

Font: Lotus Lotfi (لوتس لطفي) by Lotfi El-Tokhi, published free by its author; bundled in `assets/fonts`. On request the body is set in Traditional Arabic instead (`assets/traditional`).

Symbols font: Noto Naskh Arabic (SIL Open Font License; `assets/symbols`, details in its `SOURCE.md`). It sets, character by character, only the honorific signs and ligature words Lotus lacks at their standard code points — ﷻ ﷽ ﵁ and the rest of U+FD40–U+FD4F; the author's characters stay as written.

خط الآيات: خط الرسم العثماني – حفص (KFGQPC HAFS Uthmanic Script)، من إصدار مجمع الملك فهد لطباعة المصحف الشريف بالمدينة المنورة، يُستخدم ويوزَّع مجانًا وفق رخصته دون تعديل. ونصّا المصحف من مكتبة QUL. (`assets/quran`, details in its `SOURCE.md` — never edit these files.)

## Iron rules
- **Never change a single letter of the author's text.** Formatting only. Language remarks (e.g. ى/ي confusion, which Lotus exposes visibly via its marked alif maqsura) go in your reply, never into the file. Keep the author's punctuation exactly as written, including a stylistic ".." (two dots) — never "fix" it.
- Never invent metadata (author, date, publisher, sources). Missing → leave out and tell the user.
- Only invisible typesetting aids are allowed (RLM inside "١٢/‏٢٨٣"; the script itself adds no-break spaces and word joiners inside short numbered references so they stay on one line). Never add or remove a visible character or space.
- Bounded exceptions, each only when the user chose it in the panel or asked for it:
  - Quran verses in Uthmani script (Hafs): only for text the author marked as a verse (see «Uthmani script» below). The verse is recognised by its letters and the same words are set from the Mushaf text with its own marks. A verse that is not recognised stays exactly as written and is mentioned in the reply, never in the file.
  - Citation style: the author's source references in the footnotes are rewritten in the chosen style (Chicago, APA, Harvard, MLA), only from the details the author wrote or the user supplied (see «Citation styles»). What the style needs and the source lacks is asked from the user, never invented; what the style leaves out (APA names no place of publication) is left out. The author's other words in the note stay as written.
  - The opening basmala: the line that is only the basmala, at the very start of the text, is set as one of Lotus Lotfi's seven calligraphic basmalas (`--basmala=N`). No other phrase is ever replaced by an ornament.
  - Symbol fonts: in a Word file whose signs are stored as letters of a symbol font (AGA Arabesque stores ﷺ as «e»), the signs whose meaning is known become their standard character (`to_md.py --symbols`). The others stay and are reported.
- Indexes and the contents are added pages, like the cover: they repeat the author's own words with page numbers. The marks that feed them (`{{علم|…}}`) wrap the author's words and change none of them.

## What the output has
- The author's text, untouched (apart from what the user chose above).
- A page set the way printed Arabic books are: first-line indents, footnotes at the foot of the page with the number on the line and the text hanging, justified lines, the article's title and its writer's name at its head.
- English (Latin-script) footnotes set left to right in Times New Roman.
- Arabic-Indic digits (١٢٣) for page numbers, footnote numbers, the contents and the indexes.
- A cover and a table of contents with automatic page numbers, when the text calls for them.
- What the user chose in the panel: indexes, a citation style, a running header, Traditional Arabic, the calligraphic basmala, verses in Uthmani script.

## Accepted input
Text pasted in the chat, or a file in any text format (not PDF). Convert files with
`python3 <skill-dir>/scripts/to_md.py <file> draft.md` — it prints a report and warnings; read them.

| Input | What to.md does | What you still do |
|---|---|---|
| Pasted text, .txt, .md | copies it (BOM, line endings, Windows-1256 encoding fixed) | map the structure (step 3) |
| .docx .docm .dotx | reads Word directly: headings, bold, bullets, Word's auto-numbering, tables, footnotes and endnotes → `[^n]`; a table of contents already in the Word file becomes `@toc` | check headings levels and run-in heads |
| .doc .odt .rtf .html .htm .xhtml .wpd | LibreOffice → .docx → as above | same as Word |
| .epub | chapters in reading order → as above | turn the document's note links/asides into `[^n]` |

**PDF and images are not accepted.** Text extracted or copied from a PDF is systematically damaged (lam-alef reversed «الصلاة»→«الصالة», marks on the wrong letter, spaces inside words), and the iron rule forbids guessing the author's letters. Ask the user for the Word or text original (ready-made line in «The reply»). The user is responsible for supplying clean text.

**Pasted text can carry the same damage** when the user copied it from a PDF. Run every source — pasted text too (save it to a .txt first) — through `to_md.py`; if it reports `DAMAGED`, do not typeset: tell the user the text was copied from a PDF, show two damaged words as examples, and ask for the original file (ready-made line in «The reply»).

**Symbol fonts.** `to_md.py` prints a `SYMBOLS` line when a Word file draws signs with a symbol font (the file holds «e», the reader sees ﷺ). Offer the conversion in the panel; if the user takes it, run `to_md.py` again with `--symbols`. Signs whose meaning is unknown stay as they are: name them in the reply.

## Workflow
1. **Read the text.** Run `to_md.py` (files and pasted text alike), then `python3 <skill-dir>/scripts/analyze.py draft.md`. It prints, for you, what the text holds (cover details, headings, footnotes, verses, sayings, poetry, citations, an opening basmala, a list of sources) and which settings apply. Read the text itself too: what kind of work it is, and what its indexes would hold.
2. **Show the settings panel, then wait for the answer** (see «The settings panel»). Do not typeset before the user answers, unless their first message already settled every setting.
3. Get the text into the input format below as `in.md` in your working directory (from `to_md.py`'s draft). Map the author's structure faithfully: المبحث/الفصل/المقدمة/الخاتمة/المصادر/الفهرس → `#`; المطلب → `##`; inline bold run-in heads like «أهداف البحث:» → `###`; numbered items the author wrote as «١-» / «١.» / «١)» stay as text lines; footnotes → `[^n]`. Add the front-matter block (cover) only from details the user gave or the document states. A table of contents (`@toc`) goes right after the front-matter block (in an article with no cover, after its title and the `>>` lines under it), or at the very end when the user chose that. Then add what the user chose: `@header`, the index marks and `@index` lines, the citation tokens and `sources.json`.
4. Run: `python3 <skill-dir>/scripts/make.py in.md <output-dir>/<name> [options]` (use the environment's outputs folder if it has one). Options, each only when chosen: `--uthmani`, `--font=traditional`, `--basmala=N`, `--profile=kku`, `--cite=chicago|apa|harvard|mla|ieee --sources=sources.json`. It builds the Word file first and exports the PDF from that same file (one file, never two versions), fills the page numbers of the contents and of every index from the PDF's own layout, and writes one zip beside them, `خطوط-لملف-Word.zip`, with the fonts the Word file needs: the body font always (Lotus Lotfi, or Traditional Arabic), the Quran font whenever at least one verse was set in Uthmani script, Lotus Lotfi with Traditional Arabic when the basmala was set in it, and the symbols font (with its licence) whenever a character was set in it.
5. Verify visually: `pdftoppm -r 60 -png <pdf> <tmp>/pg` and view pages (cover, a footnote page, a table, the TOC, an index page). Check: `make.py` prints a line starting with `FONTS` when some character had to be drawn in a font outside the skill's own (or could not be drawn) — pass it on (see «The reply»); footnote marks "(١)", TOC and index numbers present and matching the real pages (script prints any heading it could not locate; an index entry whose page was not found shows ؟), table cells not breaking words. For a file source, also compare the text against the original: same paragraphs, same footnote count as `to_md.py` reported.
6. Deliver exactly three files to the user — the Word file, the PDF and `خطوط-لملف-Word.zip` — and reply as «The reply» below says. Never deliver the font files loose, and never leave the zip out.

## The settings panel
After reading the text, show the user its settings in one message, each with its options and the one you suggest, so they can answer in a word ("موافق" takes every suggestion). If the environment gives you a tool that asks the user with choices (buttons, a form), use it; otherwise a short numbered list in the chat. The form does not matter; what matters is that the user chooses after you have understood the text. Write it in the user's language, open it with the ready-made line in «The reply», and offer only what applies to this text:

0. **النمط:** بحث أو مقال (default) · رسالة علمية بدليل جامعة الملك خالد — offer it when the text is a thesis (رسالة ماجستير أو دكتوراه: أبواب أو فصول، مستخلص، شكر…); see «Theses». With it the font is Traditional Arabic and settings 1–3 and 6 follow the guide.
1. **الخط:** لوتس لطفي (default) · Traditional Arabic.
2. **الغلاف:** when the text or the user gives the cover details (title, author…); say which details are missing.
3. **فهرس الموضوعات:** after the cover (default) · at the end, after the other indexes · none.
4. **الفهارس:** list each index this text can feed, with a rough count of its entries (verses, sayings, people, places, terms…); suggest the ones with entries. Each one the user picks gets its own pages at the end, in the conventional order (verses, sayings, reports, people, narrators, lineages, rare words, poetry, places, terms, sources, contents).
5. **نظام الإحالة:** as the author wrote it (default) · Chicago · APA · Harvard · MLA · IEEE — only when the footnotes cite sources.
6. **الترويسة:** none (default) · the title of the work at the top of every page.
7. **الرسم العثماني:** only when the text has verses: no (default) · yes.
8. **البسملة:** only when the text opens with the basmala: as written (default) · one of the seven calligraphic basmalas of Lotus Lotfi; send `assets/basmala-shapes.png` so the user can pick a number.
9. **الرموز:** only when `to_md.py` printed a `SYMBOLS` line: convert the known signs (suggested) · leave them.

When the answer leaves something out, take its default and say so in one line.

## Indexes (الفهارس)
Chosen in the panel. Each index is one line in `in.md`, `@index KIND`, where its pages should go (at the end, in the order above; `@toc` after them when the user wants the contents at the end). `make.py` gives each index a heading of its own on a new page and lists it in the contents.

| KIND | Index | Its entries |
|---|---|---|
| `آية` | فهرس الآيات القرآنية | found by themselves: every verse the author marked (as in «Uthmani script»), placed by its letters and its reference, by surah in the Mushaf's order |
| `حديث` | فهرس الأحاديث النبوية | the opening words (طرف) of each saying of the Prophet ﷺ |
| `أثر` | فهرس الآثار | the opening words of each report from a Companion or a later authority |
| `علم` | فهرس الأعلام | people named in the text |
| `راو` | فهرس رواة الحديث | narrators named in a chain or as narrators |
| `نسب` | فهرس الأنساب | tribes, clans, lineages and nisbas (الأنصار، بنو شيبان…) |
| `غريب` | فهرس الكلمات الغريبة | rare words the author explains |
| `شعر` | فهرس الشواهد الشعرية | each verse of poetry quoted, grouped by its rhyme letter |
| `مكان` | فهرس الأماكن والبلدان | places, towns, regions |
| `مصطلح` | فهرس المصطلحات | terms the author defines or relies on |
| `مصدر` | فهرس المصادر والمراجع | the sources file of the chosen citation style, in that style, alphabetical |

**Marking.** Every index except verses and sources is fed by marks you put around the author's words in `in.md`: `{{KIND|the words as written}}`. The words between the braces stay in the text exactly as they are; mark every place the entry occurs, in the body and in the notes (an entry in a note takes the page of the note).
- To list an entry under another form, add it: `{{علم|شيخ الإسلام|ابن تيمية}}` (the text keeps «شيخ الإسلام»; the index lists «ابن تيمية» with this page). Use this to bring the author's different names for one person together, never to add information.
- A saying or report: mark its opening words as the author wrote them, inside the author's quotation marks (`{{حديث|إنما الأعمال بالنيات}}`).
- A verse of poetry: mark the whole verse, so its rhyme letter is its last letter; when that is not so (a final ه of the rhyme, a verse split across lines), give the rhyme letter as a fourth field: `{{شعر|the verse||ب}}`.
- Never change, add or move a character of the author's to make a mark fit; a mark cannot cross a footnote reference, a line or another mark.
- Names, places and words are ordered without their «ال»; sayings and verses by their first word as written.

The contents and the indexes take their page numbers from the PDF, and the Word file carries the same numbers.

**The author's own list of sources** stays as the author wrote it, under the author's heading. When the user asks for it in alphabetical order, put the lines between `@sort` and `@end`; each line is kept whole. A list the author numbered keeps its order (renumbering would change the text) and `make.py` prints `SORT` — tell the user.

## Theses (الرسائل العلمية) — the King Khalid University guide
Chosen in the panel (النمط). `--profile=kku` sets a master's or doctoral thesis by «دليل الرسائل العلمية» of King Khalid University: Traditional Arabic, 1.5 lines, headings 20 and 18 bold, a 3.5 cm binding margin on the right, the header without its rule. What the guide leaves to the department (citation style, indexes) stays a panel choice.
- **Front matter** (only what the user or the document gives; never invent a name, a degree or a date): `title`, `college` (without «كلية»), `department` (without «قسم»), `degree` (الماجستير / الدكتوراه), `field` (the specialisation), `author`, `supervisor` (with the title as the user wrote it), `date`, `logo` (the university's logo, a PNG or JPEG the user sent — never one from elsewhere), and `member: name | role` once per committee member (roles as the guide writes them: مشرف ومقرر، مناقش أول/ داخلي، مناقش ثاني/، …).
- **Pages in the guide's order:** the title page (model 1) is made from the front matter; `@approval` adds the approval page (model 3) with the committee table; `@basmala` adds a page with the calligraphic basmala (`--basmala=N`). These have no number. Then the prelims, numbered in letters from «ب»: write each as a `#` heading the author wrote (الإهداء، الشكر والتقدير، المستخلص، Abstract، قائمة الرموز…), with `@toc` (titled «قائمة المحتويات», listing itself) and `@figures` / `@tables` (lists of the captions «شكل (١-١): …» / «جدول (١-١): …» written as `>>` lines above them) where the author has them. The text starts at page 1 with the first `#` heading after them.
- **Parts:** a `#` heading that starts with «الباب» gets a page of its own, centred, with no header and no number; the chapters follow as `#`.
- **Appendices:** after the references, `@appendix title` gives each appendix its page «ملحق رقم (n)» with its title; the appendix's own text follows it. The indexes the user chose go after the appendices.
- `make.py` prints `THESIS` lines, in Arabic: details of the title page that are missing, a missing logo, the title font (see below), a basmala page with no shape number, an abstract over 300 words, acknowledgements longer than a page, an empty list of tables or figures. Pass them on with the ready-made line in «The reply».
- **The title font:** the guide sets the thesis title on the title and approval pages in «PT Bold Heading», a display font that is not in the skill; the title is set in Traditional Arabic bold 20 instead, and the `THESIS` line says so. It is used only if the user supplies the font file.

## Citation styles (نظام الإحالة)
Chosen in the panel; only when the footnotes cite sources.
1. Build `sources.json` (format at the head of `scripts/cite.py`): one entry per source the notes cite, with only the details the author wrote somewhere in the work (a note, the list of sources) or the user gave. Never complete a detail from your own knowledge — not a publisher, a place, a year, a death date or an editor.
2. Run `python3 <skill-dir>/scripts/cite.py sources.json --cite=STYLE`. Each `CITE` line names a source and the details the style needs and it lacks. Ask the user for them in one message (ready-made line in «The reply»), with the list. What the user cannot supply is left out of the citation.
3. In each footnote, replace the author's reference to a source by `{{مرجع|ID|the place as the author wrote it}}` (`[^3]: انظر: {{مرجع|fatawa|٣/ ٤٥}}، وفيه نظر.`). Keep the rest of the note exactly as written. The first citation of a source is written in full where the style asks for that (Chicago), the later ones short; APA and Harvard write author and year; MLA author and short title; IEEE numbers each source in the order it is first cited, «[1]» with the full reference the first time and «[1]، الموضع» after, and its list of sources follows that order.
4. Add `@index مصدر` for the list of sources in the style, and run `make.py` with `--cite=STYLE --sources=sources.json`. `make.py` prints the `CITE` lines again for any detail still missing.

## The running header (الترويسة)
Chosen in the panel. `@header` (a line of its own anywhere in `in.md`) puts the title of the work — the cover's title, or an article's first heading — at the top of every page but the first, centred over a thin rule. `@header نص` uses that text instead; it must be the title as the author wrote it, never your own.

## The opening basmala (البسملة)
Chosen in the panel. When the first line of the text is only the basmala (with or without marks, or ﷽), `--basmala=N` sets it as Lotus Lotfi's basmala number N (1–7, as numbered in `assets/basmala-shapes.png`), centred. Without the option that line stays as written, centred. The basmala must stay the first line of `in.md`'s text (after the front-matter block).

## Input format (`in.md`)
```
---
title: عنوان البحث            (cover; omit the whole block for no cover)
line: سطر تعريفي تحت العنوان   (repeatable)
author: اسم المؤلف
affiliation: الصفة
date: ١٤٤٧هـ – ٢٠٢٦م
---
بسم الله الرحمن الرحيم        (only if the author's text opens with it)
@header                       the running header, on request only
@toc                          فهرس الموضوعات, right after the cover, or at the end on request (auto page numbers; it does not list itself)
# المقدمة                     heading 1: centered 18 bold. With a cover (a research paper) each one starts a new page. With no cover (an article) they follow the text before them on the same page, with space above; the first one is the article title, at the head of page 1 (set lower, with space under it), and the text follows it on that page; a text with no title simply starts with its first paragraph
## المطلب الأول: ...          heading 2: 16 bold
### أهداف البحث:              run-in bold head
نص فقرة عادية مع **عريض** وحاشية[^1]، وذكره {{علم|ابن تيمية}}.
١- عنصر مرقّم كما كتبه المؤلف (أو ١. أو ١))
* نقطة عريضة (مستوى أول، مثل: • معنى التفسير في اللغة:)
- نقطة عادية
-- نقطة مستوى ثانٍ (○)
>> سطر عريض في الوسط (مثل: دونك الجدول...). Also for the writer's name when the author's text has it under the title — never invent one
| | عمود ١ | عمود ٢ |         first row = header (grey). Long last column auto-widens.
| **صف:** | قيمة | قيمة |
@pagebreak
@sort … @end                  the author's own lines between them in alphabetical order (on request)
@index علم                    an index, on request (see «Indexes»)
[^1]: نص الحاشية، أو {{مرجع|ID|٣/ ٤٥}} with a citation style.
```
Automatic: every ordinary paragraph opens with a 1 cm first-line indent — the first paragraph of the text too, whether or not the article has a title — and there is no space between paragraphs (headings, lists and footnotes are not indented). So write each of the author's paragraphs as a plain line: never turn the opening paragraph of a text that has no title into a heading or a `>>` line, and never invent a title for it; a paragraph that is only a verse is centred; a footnote written mostly in Latin letters is set left to right in Times, and its number is Western, «(1)»; a footnote holding a word that cannot break (a link) is aligned to the start instead of justified, and nothing is inserted into the link; lines are justified; a section heading never stays alone at the foot of a page (in the PDF, `make.py` moves it to the next page with its paragraph); verse refs `[البقرة: ١٤٣]` and death dates `(ت:٤٦٨)` are set small; Latin words/URLs switch to Times New Roman; glyphs Lotus lacks (– … • “ ” ; ? |) fall back to Times; table columns size themselves to their content. No running header at the top of pages unless the user chose it (`@header`).

## The reply
- **Language: always the user's.** Write the whole reply in the language the user wrote in — Arabic (فصحى واضحة) when they wrote in Arabic, even if they only sent an Arabic text with one word — whatever the language of this file or of the scripts' messages. The scripts print in English for you: say what they mean in the user's language, never paste them. (The exceptions are the lines `make.py` prints after `QURAN`, `INDEX لم تدخل`, `CITE` and `THESIS`: they are written in Arabic for the reply.)
- Keep it short: what you are delivering, then only what the user needs to know or act on (an issue you found, a warning from `to_md.py`, a language remark). Do not describe the style or list what the scripts did.
- Digits: the PDF draws every digit in Arabic text as ١٢٣ however the author typed it (`[البقرة: 151]` is shown as [البقرة: ١٥١]), and the author's characters are not changed. So never remark that the source has Western digits, and never suggest changing them — in verse references or anywhere else. Speak of digits only if you saw Western digits in Arabic text in the PDF pages of the visual check; judge by the rendered pages, never by `in.md`.
- Ready-made lines. Use them as written when the reply is in Arabic; for another language, say the same thing in it.
  - Always, with the files: «لعرض ملف Word بالخط الصحيح فكّ الملف المضغوط المرفق (خطوط-لملف-Word.zip) وثبّت الخطوط التي فيه. وملف PDF لا يحتاج شيئًا.»
  - The work has contents or indexes (with the files): «عند فتح ملف Word يسألك عن تحديث الحقول؛ وافق لتصحّ أرقام الصفحات في الفهارس على ترتيب Word نفسه.»
  - Opening the settings panel: «قرأتُ نصّك، وهذه إعدادات صفّه، ومعها ما أقترحه لكل واحد منها. اختر ما تريد، أو اكتب «موافق» لأعتمد المقترح كله:»
  - A citation style was chosen and `cite.py` printed `CITE` lines (put the lines after it): «لصفّ الإحالات بالنظام الذي اخترتَه تنقصني بيانات لم أجدها في بحثك، ولن أضع من عندي شيئًا. أرسلها إن كانت عندك، وما لم يصلني منها أتركه:»
  - `make.py` printed `INDEX لم تدخل` lines (put the verses after it): «هذه آيات لم أُدخلها فهرسَ الآيات لأني لم أستطع تحديد موضعها من المصحف، وهي في البحث كما كتبتَها:»
  - The user sent a PDF or an image: «لا أقبل ملفات PDF ولا الصور؛ لأن النص المستخرج منها تتلف حروفه، ولا أخمّن حروف الكاتب. أرسل الأصل: ملف Word أو النص نفسه.»
  - `to_md.py` reported `DAMAGED` (put two of the damaged words in the gaps): «يبدو أن هذا النص منسوخ من ملف PDF، فقد تلفت بعض حروفه، مثل «…» و«…». أرسل الأصل: ملف Word أو النص نفسه.»
  - `make.py` printed `THESIS` lines (put them after it, each on its own line): «هذه ملاحظات على رسالتك بحسب دليل الجامعة؛ ما ينقص منها أرسله إن أردتَ إكماله:»
  - A detail of the cover is missing (never invent it): «لم أجد في النص … فتركتُه؛ أرسله إن أردتَ إضافته.»
  - Signs of a symbol font whose meaning is unknown (copy them from the `SYMBOLS` line): «في ملف Word رموز مكتوبة بخطٍّ رمزي لا أعرف معناها، فتركتُها كما هي: …؛ أخبرني بما تعنيه لأضعها.»
  - `make.py` printed a `FONTS` line (copy the characters and pages from it): «في ملف PDF حروف ليست في خطوط المهارة فظهرت بخطٍّ آخر أو لم تظهر: … في الصفحة …؛ وهي في ملف Word كما كتبتَها.»
  - A short reference is split across two lines in the PDF: «انقسمت الإحالة «…» على سطرين في الصفحة … من PDF، وهذا حدٌّ معروف في محرّك PDF؛ وهي سليمة في ملف Word.»
  - The user asks why the footnote numbers look Western in Word: «في Word تتبع أرقام الحواشي إعداد «Numeral» عند القارئ؛ ولإظهارها مشرقية يُختار Context أو Hindi. وهي في PDF مشرقية دائمًا.»
  - The user wants to make the PDF from Word on a Mac: «الأصل أن يُستعمل PDF صفّاف. ومن يريد PDF من Word على الماك يصدّره من Print ← Save as PDF ليبقى الخط؛ فالتصدير المباشر (Save As › PDF) يستبدل بخط الملف خطًّا آخر لأن الملف لا يضمّن خطوطه.»

## Uthmani script (الرسم العثماني) — only on request
Off by default. Use it only when the user explicitly asks for the verses in Uthmani script / رسم المصحف (in the panel or in their message): add `--uthmani` to the `make.py` command. Hafs only (its script and its marks). Keep every verse, the marks around it and its reference exactly as the author wrote them in `in.md`: never retype, complete or correct a verse, and never add brackets or a reference the author did not write.
- **What is looked at:** only what the author marked as a verse — the text between ﴿ ﴾, and the text between quotation marks («» or "" or ()) right after a phrase that says so (قال تعالى، قوله تعالى، قال الله، وقال سبحانه…). The author's other words are never searched, even where they are the words of a verse. A reference with no verse text adds nothing.
- **How it is recognised:** by its letters alone. The author's vowel marks are ignored — none, some, or different from the Mushaf — and the same words are set from the Uthmani text with the Mushaf's own marks: a whole ayah, or just the part the author wrote. Ayah numbers the author wrote between ayahs, like `(١)`, become the Uthmani ayah marks.
- **Its place:** helped by the reference after it — `[البقرة: ١٤٣]`, a range `[الإخلاص: ١-٢]`, or the surah's name alone `[البقرة]` — or by «سورة …» right before it. With no reference, a wording found in several places is still converted when its Uthmani text is the same in all of them.
- **What stays as written:** a verse whose letters match no place in the Mushaf; a wording whose places differ in their Uthmani text when it has no reference or surah name; and a verse whose reference points to another place than the one its letters match (the letters decide, so the author must check).
- `make.py` prints lines starting with `QURAN`, already in Arabic for the reply: the count of verses converted and left, then each verse left as written and why — with both places when the reference disagrees. Put them all in the reply, without the word `QURAN`; nothing about them goes in the file.
- The index of verses uses the same recognition, and needs one place: a wording found in several places goes into it only with its reference or surah name (`INDEX لم تدخل` lines say which).
- In the visual check, look at a page with a converted verse.

## Known limits (tell the user when relevant, in the words of «The reply»)
- Lines are justified by the spaces between words. In the PDF, LibreOffice versions before 25 still lengthen some letters to fill a line; this belongs to that engine, and the fonts are never altered to prevent it. Do not mention lengthened letters in the reply — in the body text or in verses (the Mushaf itself is justified that way).
- Short references are glued with invisible aids (no-break spaces, word joiners) so Word keeps «(ت:٤٦٨)», «(٢/ ٦٥٣)», «[البقرة: ١٤٣]» on one line. LibreOffice (the PDF engine here) ignores the joiners and can still split a parenthesis from the number beside it; only spaces are protected there. For print, the PDF can be made from Word instead (see the note on Word for Mac below). In the visual check, look for a reference split across lines and mention it if found.
- In Word the footnote numbers follow the reader's «Numeral» setting (Context or Hindi shows them as ١٢٣); in the PDF they are always ١٢٣. The page number is always ١٢٣ in Word too: it is computed by fields.
- The PDF is exported from the delivered Word file itself, by LibreOffice, so both hold the same text, order and styles. Microsoft Word on the reader's computer lays the same file out with its own engine, and a page can end a few lines earlier or later there than in the PDF. The page numbers of the contents and the indexes are fields: each program computes its own, so they are right in each file (Word asks to update them when the file opens; their digits follow the reader's «Numeral» setting).
- The Word file does not embed Lotus Lotfi: Word shows the document in it only where the font is installed, hence the fonts zip. The Quran font is embedded, but Word for Mac ignores embedded fonts, so it is in the zip too whenever a verse was set in it.
- The basmalas of Lotus Lotfi sit at code points of another Unicode block (U+1EE00–U+1EE06): copied out of the PDF or Word file, the calligraphic basmala comes out as other characters, and it shows as itself only in Lotus Lotfi.
- The PDF to use is the skill's own. Word for Mac's direct export (Save As › PDF) swaps the document's font for another because the file does not embed its fonts; Print ← Save as PDF keeps it.

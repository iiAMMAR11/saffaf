"""What the assistant is asked, and the exact shape of its answer (JSON Schema, for structured outputs).
The paragraphs are sent numbered; the answer refers to them by number and character offsets, never by rewriting them."""
import json

KINDS_MARKABLE = ['حديث', 'أثر', 'علم', 'راو', 'نسب', 'غريب', 'شعر', 'مكان', 'مصطلح']

SYSTEM = (
    'You help typeset Arabic research papers. You never rewrite, correct, complete or translate the author\'s text, '
    'and you never add information that is not in it. You answer only with the JSON the schema asks for: numbers of '
    'paragraphs, roles, and character offsets into the paragraph text exactly as given (0-based, end exclusive, '
    'counting Unicode code points).')

def numbered(paragraphs):
    """paragraphs: [(i, text)] -> the user content: one JSON object per line."""
    return '\n'.join(json.dumps({'i': i, 'text': t}, ensure_ascii=False) for i, t in paragraphs)

STRUCTURE = dict(
    name='structure',
    effort='low',
    instructions=(
        'Each line below is one paragraph of an Arabic paper, in order. Give the role of every paragraph that is NOT an '
        'ordinary paragraph: "h1" for a main heading (المقدمة، المبحث، الفصل، الخاتمة، المصادر…, or the article\'s title), '
        '"h2" for a sub-heading (المطلب…), "h3" for a short bold lead-in that ends with a colon, "center" for a line set '
        'apart in the centre (the writer\'s name under the title). Leave ordinary paragraphs out.'),
    schema={'type': 'object', 'additionalProperties': False, 'required': ['labels'],
            'properties': {'labels': {'type': 'array', 'items': {
                'type': 'object', 'additionalProperties': False, 'required': ['i', 'role'],
                'properties': {'i': {'type': 'integer'}, 'role': {'type': 'string', 'enum': ['h1', 'h2', 'h3', 'center']}}}}}},
)

NOTES = dict(
    name='notes',
    effort='low',
    instructions=(
        'The text below was pasted with its footnotes as numbered lines (they may restart at (١) on every page). For '
        'every note line, give the paragraph and the offsets of the ONE number in the text that refers to it, '
        'exactly as written, e.g. «(٣)». Leave out any note whose place you cannot tell for certain.'),
    schema={'type': 'object', 'additionalProperties': False, 'required': ['pairs'],
            'properties': {'pairs': {'type': 'array', 'items': {
                'type': 'object', 'additionalProperties': False, 'required': ['note', 'i', 'start', 'end'],
                'properties': {'note': {'type': 'integer'}, 'i': {'type': 'integer'},
                               'start': {'type': 'integer'}, 'end': {'type': 'integer'}}}}}},
)

MARKS = dict(
    name='marks',
    effort='medium',
    instructions=(
        'Mark the entries of these indexes in the paragraphs below: ' + '، '.join(KINDS_MARKABLE) + '. '
        'For each occurrence give the paragraph, the offsets of the words exactly as the author wrote them, the kind, '
        'and — only when the index should list it under another form that the author also uses elsewhere in the text '
        '(شيخ الإسلام → ابن تيمية) — that form in "entry". For a saying (حديث، أثر) mark its opening words inside the '
        'author\'s quotation marks; for poetry the whole verse. Never mark a verse of the Quran.'),
    schema={'type': 'object', 'additionalProperties': False, 'required': ['marks'],
            'properties': {'marks': {'type': 'array', 'items': {
                'type': 'object', 'additionalProperties': False, 'required': ['i', 'start', 'end', 'kind', 'entry'],
                'properties': {'i': {'type': 'integer'}, 'start': {'type': 'integer'}, 'end': {'type': 'integer'},
                               'kind': {'type': 'string', 'enum': KINDS_MARKABLE},
                               'entry': {'type': 'string'}}}}}},
)

SOURCE_FIELDS = ['type', 'title', 'short', 'editor', 'translator', 'edition', 'volumes', 'place', 'publisher', 'year',
                 'journal', 'volume', 'issue', 'pages', 'container', 'degree', 'university', 'site', 'url', 'accessed',
                 'date', 'library', 'number']

SOURCES = dict(
    name='sources',
    effort='medium',
    instructions=(
        'The lines below are the footnotes of an Arabic paper, then its list of sources if it has one. Build the list of '
        'sources the notes cite, with ONLY the details written somewhere in these lines — leave a detail out rather than '
        'supply it from your own knowledge. Then, for each note, give the offsets of the reference to a source (the '
        'author\'s words that name the source and the place in it) and, separately, the place as written (e.g. «٣/ ٤٥»).'),
    schema={'type': 'object', 'additionalProperties': False, 'required': ['sources', 'cites'],
            'properties': {
                'sources': {'type': 'array', 'items': {
                    'type': 'object', 'additionalProperties': False, 'required': ['id', 'type', 'authors', 'title'],
                    'properties': dict({'id': {'type': 'string'},
                                        'authors': {'type': 'array', 'items': {'type': 'string'}}},
                                       **{f: {'type': 'string'} for f in SOURCE_FIELDS})}},
                'cites': {'type': 'array', 'items': {
                    'type': 'object', 'additionalProperties': False, 'required': ['note', 'start', 'end', 'id', 'place'],
                    'properties': {'note': {'type': 'integer'}, 'start': {'type': 'integer'}, 'end': {'type': 'integer'},
                                   'id': {'type': 'string'}, 'place': {'type': 'string'}}}}}},
)

TASKS = {t['name']: t for t in (STRUCTURE, NOTES, MARKS, SOURCES)}

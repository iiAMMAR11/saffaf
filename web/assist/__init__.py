"""The assistant (a language model) for what rules cannot settle: the structure of an unformatted text, the notes of a
pasted text, the marks of the indexes, the sources of a citation style.

Separate from the typesetting engine, and off unless the server is configured for it (see providers.py). The model
never writes the author's text: it answers with positions and labels only (a paragraph's number and role, a span's
start and end, a source's details), and every answer goes through validate.py before anything is applied — a span
must be the author's exact words, a detail of a source must stand in the author's text or come from the user, and
the text with the marks taken out must be the text as it was."""

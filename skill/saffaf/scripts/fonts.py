"""The body font asked for instead of Lotus Lotfi (on request only)."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))

def traditional_files():
    """The Traditional Arabic font, used only when the user asks for it: (family, regular file, bold file or None), read
    from the files in assets/traditional (SAFFAF_TRADITIONAL_DIR points elsewhere, for the tests). None when absent."""
    from fontTools.ttLib import TTFont
    d = os.environ.get('SAFFAF_TRADITIONAL_DIR') or os.path.join(HERE, "..", "assets", "traditional")
    files = sorted(os.path.join(d, f) for f in (os.listdir(d) if os.path.isdir(d) else []) if f.lower().endswith(('.ttf', '.otf')))
    reg = bold = None
    for f in files:
        sub = TTFont(f, lazy=True)['name'].getDebugName(2) or ''
        if 'bold' in sub.lower() and 'italic' not in sub.lower(): bold = bold or f
        elif sub.lower() in ('regular', 'normal', 'book', 'roman'): reg = reg or f
    if not reg: return None
    return TTFont(reg, lazy=True)['name'].getDebugName(1), reg, bold

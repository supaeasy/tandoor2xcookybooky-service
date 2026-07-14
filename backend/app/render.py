import re
from fractions import Fraction
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = "/app/templates"

_LATEX_SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# Vulgar fraction characters (e.g. from copy-pasted recipe text) have no glyph
# in the text fonts we use and make pdflatex abort with a fatal error - map
# them to \nicefrac{}{} instead, consistent with how numeric fractions are
# already rendered elsewhere.
_UNICODE_FRACTIONS = {
    "¼": (1, 4), "½": (1, 2), "¾": (3, 4),
    "⅓": (1, 3), "⅔": (2, 3),
    "⅕": (1, 5), "⅖": (2, 5), "⅗": (3, 5), "⅘": (4, 5),
    "⅙": (1, 6), "⅚": (5, 6),
    "⅐": (1, 7),
    "⅛": (1, 8), "⅜": (3, 8), "⅝": (5, 8), "⅞": (7, 8),
    "⅑": (1, 9),
    "⅒": (1, 10),
}

# Various invisible/exotic space characters (common in text copy-pasted from
# Word or web pages) have no glyph in our text fonts either and crash
# pdflatex just like the vulgar fractions did - normalize them to a plain
# ASCII space (or drop the truly zero-width ones). Built from codepoints
# rather than literal characters since these are invisible/indistinguishable
# from each other in an editor.
_SPACE_LIKE_CODEPOINTS = [
    0x00A0,  # no-break space
    0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005,  # en/em quad ... six-per-em space
    0x2006, 0x2007, 0x2008, 0x2009, 0x200A,  # figure/punctuation/thin/hair space
    0x202F,  # narrow no-break space
    0x2028, 0x2029,  # line/paragraph separator
]
_ZERO_WIDTH_CODEPOINTS = [
    0x200B,  # zero width space
    0xFEFF,  # zero width no-break space / BOM
]
_WHITESPACE_LIKE = {chr(cp): " " for cp in _SPACE_LIKE_CODEPOINTS}
_WHITESPACE_LIKE.update({chr(cp): "" for cp in _ZERO_WIDTH_CODEPOINTS})

_LATEX_ESCAPE_RE = re.compile(
    "|".join(re.escape(k) for k in {**_LATEX_SPECIAL_CHARS, **_UNICODE_FRACTIONS, **_WHITESPACE_LIKE})
)


def _latex_escape_one(match: re.Match) -> str:
    ch = match.group()
    if ch in _UNICODE_FRACTIONS:
        num, den = _UNICODE_FRACTIONS[ch]
        return f"\\nicefrac{{{num}}}{{{den}}}"
    if ch in _WHITESPACE_LIKE:
        return _WHITESPACE_LIKE[ch]
    return _LATEX_SPECIAL_CHARS[ch]


def latex_escape(value):
    if value is None:
        return ""
    value = str(value)
    value = _LATEX_ESCAPE_RE.sub(_latex_escape_one, value)
    # Last-resort safety net: any other character our text fonts can't
    # render (emoji, rare symbols, ...) would otherwise abort the whole
    # compile - including everyone else's recipes in a collected PDF - so
    # drop those instead of failing the entire document.
    return "".join(ch for ch in value if ord(ch) < 0x2100)


def decimal_to_nicefrac(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    if value.is_integer():
        return str(int(value))
    frac = Fraction(value).limit_denominator(8)
    if frac.numerator > frac.denominator:
        whole_number = frac.numerator // frac.denominator
        fraction_part = frac - whole_number
        return f"{whole_number}\\nicefrac{{{fraction_part.numerator}}}{{{fraction_part.denominator}}}"
    return f"\\nicefrac{{{frac.numerator}}}{{{frac.denominator}}}"


def replace_celsius(value):
    if not isinstance(value, str):
        return value
    return value.replace("°C", r"\textcelcius")


def replace_min_space(value):
    if isinstance(value, str):
        value = re.sub(r"(\d+)\s+Min\.", r"\1~Min.", value)
        value = re.sub(r"(\d+)\s+min\.", r"\1~min.", value)
        value = re.sub(r"(\d+)\s+Minuten", r"\1~Minuten", value)
    return value


def build_env():
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        block_start_string="<<%",
        block_end_string="%>>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<<#",
        comment_end_string="#>>",
    )
    env.filters["replace_celsius"] = replace_celsius
    env.filters["replace_min_space"] = replace_min_space
    env.filters["decimal_to_nicefrac"] = decimal_to_nicefrac
    env.filters["latex_escape"] = latex_escape
    return env


_env = build_env()


def render_preamble(babel_lang: str, pdf_author: str, pdf_title: str) -> str:
    template = _env.get_template("preamble.tex.j2")
    return template.render(babel_lang=babel_lang, pdf_author=pdf_author, pdf_title=pdf_title)


def render_document_start() -> str:
    return _env.get_template("document_start.tex.j2").render()


def render_document_end() -> str:
    return _env.get_template("document_end.tex.j2").render()


def render_recipe_fragment(recipe: dict, font_size_pt: float | None = None) -> str:
    """Renders a recipe. If font_size_pt is given, the ingredients list and
    the preparation steps (and only those - not the picture, title, meta
    line, or introduction) are set at that font size via \\changefontsizes,
    which - unlike relsize - actually recomputes \\Large/\\Huge/\\small etc.
    for that scope instead of just changing the current point size. This is
    used to shrink recipes that don't fit on a single page: xcookybooky's
    wrapfigure-based layout cannot break a recipe across pages, so a too-long
    recipe would otherwise push its trailing \\hint box onto an otherwise
    empty extra page."""
    # wrapfig (used internally by \ingredients for the wraptable) tries to
    # auto-detect the table's height if not told explicitly, which its own
    # documentation admits is unreliable for longer tables, so we pass an
    # explicit estimate instead. A plain row count undercounts badly: a note
    # wraps onto 2-3 lines in the narrow ingredients column (e.g. "Oberschale
    # in / Scheiben zu 180g"), leaving wrapfig's wrap-region shorter than the
    # table actually is, so normal-width preparation text bleeds back through
    # the tail of the still-continuing table. (An earlier attempt at this
    # weighting looked like it broke rendering entirely, but that was really
    # a separate, since-fixed bug where the font-size shrink had no effect at
    # all - now that it actually applies, retry a closer-to-reality estimate.)
    ingredient_count = sum(
        2 if ingredient.get("note") else 1
        for step in recipe.get("steps") or []
        for ingredient in step.get("ingredients") or []
    )
    template = _env.get_template("recipe_fragment.tex.j2")
    return template.render(recipe=recipe, font_size_pt=font_size_pt, ingredient_count=max(ingredient_count, 1))

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
_LATEX_SPECIAL_RE = re.compile("|".join(re.escape(k) for k in _LATEX_SPECIAL_CHARS))


def latex_escape(value):
    if value is None:
        return ""
    value = str(value)
    return _LATEX_SPECIAL_RE.sub(lambda m: _LATEX_SPECIAL_CHARS[m.group()], value)


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


def render_recipe_fragment(recipe: dict) -> str:
    template = _env.get_template("recipe_fragment.tex.j2")
    return template.render(recipe=recipe)

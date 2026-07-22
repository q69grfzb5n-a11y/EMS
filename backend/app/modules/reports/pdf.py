"""WeasyPrint PDF rendering — render only in-container (Pango/GTK system libs
aren't available bare on Windows; see docs/development.md). Fonts are vendored
into app/assets/fonts/ rather than relying on whatever happens to be on the
host, so PDF output is reproducible across environments."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_FONTS_DIR = Path(__file__).parent.parent.parent / "assets" / "fonts"

_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=select_autoescape())


def _font_face_css() -> str:
    naskh_regular = (_FONTS_DIR / "NotoNaskhArabic-Regular.ttf").as_uri()
    naskh_bold = (_FONTS_DIR / "NotoNaskhArabic-Bold.ttf").as_uri()
    sans_regular = (_FONTS_DIR / "NotoSans-Regular.ttf").as_uri()
    sans_bold = (_FONTS_DIR / "NotoSans-Bold.ttf").as_uri()
    return (
        f"@font-face {{ font-family: 'Noto Naskh Arabic'; src: url('{naskh_regular}'); "
        "font-weight: normal; }\n"
        f"@font-face {{ font-family: 'Noto Naskh Arabic'; src: url('{naskh_bold}'); "
        "font-weight: bold; }\n"
        f"@font-face {{ font-family: 'Noto Sans'; src: url('{sans_regular}'); "
        "font-weight: normal; }\n"
        f"@font-face {{ font-family: 'Noto Sans'; src: url('{sans_bold}'); font-weight: bold; }}\n"
    )


def render_pdf(template_name: str, context: dict[str, Any]) -> bytes:
    template = _env.get_template(template_name)
    html_str = template.render(font_face_css=_font_face_css(), **context)
    pdf_bytes: bytes = HTML(string=html_str, base_url=str(_TEMPLATES_DIR)).write_pdf()
    return pdf_bytes

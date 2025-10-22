from dataclasses import dataclass, field, asdict
from pathlib import Path
from jinja2 import Template

template_html_fp = Path(__file__).parent / "TemplatePage.html"
template_html = template_html_fp.read_text()
template = Template(template_html)


@dataclass
class Anchor:
    href: str
    content: str


@dataclass
class RenderingArg:
    url:str = ""
    has_meta: bool = False
    original_html_length: int = 0
    content_html_length: int = 0
    title: str = "TextBrowser"
    compression_rate: str = ""
    content_html: str = ""
    anchors: list[Anchor] = field(default_factory=list)
    uls:list[list[str]] = field(default_factory=list)
    ols:list[list[str]] = field(default_factory=list)


def render(arg: RenderingArg):
    return template.render(**asdict(arg))

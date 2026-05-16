from abc import ABC, abstractmethod
from pathlib import Path
import mimetypes
import os
import tempfile
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from bs4.element import Tag, PageElement
from pypdf import PdfReader
import requests
from renderer import RenderingArg, Anchor


def extract_li_list(element: Tag) -> list[str]:
    return [li.get_text(strip=True) for li in element.find_all("li")]


class ContentExtractor(ABC):
    @abstractmethod
    def extract(self, url: str) -> RenderingArg:
        raise NotImplementedError


class HtmlContentExtractor(ContentExtractor):
    def extract(self, url: str) -> RenderingArg:
        out = RenderingArg()
        extracted_texts = []

        def append_newline():
            if extracted_texts and extracted_texts[-1] != "":
                extracted_texts.append("")

        def tree(pe: PageElement):
            if pe is None:
                return
            name = str(pe.name)
            is_isolated_line = name in ["h1", "h2", "h3", "h4", "figure"]
            if is_isolated_line:
                append_newline()
            if not isinstance(pe, Tag):
                text = pe.get_text(strip=True)
                if text and text != "\n":
                    extracted_texts.append(text)
                return
            for c in pe.children:
                tree(c)
            if is_isolated_line:
                append_newline()

        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            response.encoding = response.encoding or "utf-8"

            soup = BeautifulSoup(response.text, "html.parser")

            title_element = soup.find("title")
            if title_element:
                out.title = title_element.get_text(strip=True)

            for anchor_element in soup.find_all("a"):
                out.anchors.append(
                    Anchor(
                        href=anchor_element.attrs.get("href"),
                        content=anchor_element.get_text(strip=True),
                    )
                )

            for tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
                tag.decompose()

            out.uls = [extract_li_list(ul) for ul in soup.find_all("ul")]
            out.ols = [extract_li_list(ol) for ol in soup.find_all("ol")]

            candidates = soup.find_all(["article", "main", "section", "div"])
            longest = max(
                candidates, key=lambda tag: len(tag.get_text(strip=True)), default=None
            )
            if longest is None:
                raise ValueError("No content found.")

            tree(longest)

            out.content_html = "".join(extracted_texts)
            out.has_meta = True
            out.original_html_length = len(response.text)
            out.content_html_length = len(out.content_html)
            out.compression_rate = (
                "?"
                if out.original_html_length == 0
                else f"{100 * out.content_html_length / out.original_html_length:.2f}%"
            )
            return out

        except Exception as e:
            out.content_html = str(e)
            return out


class PdfContentExtractor(ContentExtractor):
    def _safe_filename(self, url: str) -> str:
        parsed = urlparse(url)
        base = Path(parsed.path).name or "document.pdf"
        base = "".join(ch for ch in base if ch.isalnum() or ch in "._-")
        if not base.lower().endswith(".pdf"):
            base += ".pdf"
        return base[:120]

    def extract(self, url: str) -> RenderingArg:
        out = RenderingArg()
        out.url = url

        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=20, stream=True)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            if (
                "pdf" not in content_type
                and mimetypes.guess_type(url)[0] != "application/pdf"
            ):
                raise ValueError(
                    f"Not a PDF URL: {content_type or 'unknown content-type'}"
                )

            safe_name = self._safe_filename(url)
            with tempfile.TemporaryDirectory() as tmpdir:
                pdf_path = Path(tmpdir) / safe_name
                with open(pdf_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                reader = PdfReader(str(pdf_path))

                texts = []
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    if page_text:
                        texts.append(page_text)

                out.content_html = "\n\n".join(texts).strip()

                meta = reader.metadata
                if meta is not None:
                    out.has_meta = True
                    out.title = getattr(meta, "title", None) or out.title

                out.original_html_length = pdf_path.stat().st_size
                out.content_html_length = len(out.content_html)
                out.compression_rate = (
                    "?"
                    if out.original_html_length == 0
                    else f"{100 * out.content_html_length / out.original_html_length:.2f}%"
                )

            return out

        except Exception as e:
            out.content_html = str(e)
            return out


def extract_content(url: str) -> RenderingArg:
    if url.endswith(".pdf"):
        return PdfContentExtractor().extract(url)
    return HtmlContentExtractor().extract(url)


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser("TextBrowser Extractors")
    parser.add_argument("url", type=str)
    args = parser.parse_args()
    print(extract_content(args.url))

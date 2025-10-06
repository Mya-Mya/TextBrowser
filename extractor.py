import requests
from bs4 import BeautifulSoup
from bs4.element import Tag, PageElement
from renderer import RenderingArg, Anchor


def extract_li_list(element: Tag) -> list[str]:
    li_list = []
    for li_element in element.find_all("li"):
        li_list.append(li_element.get_text(strip=True))
    return li_list


def extract_content_html(url: str) -> RenderingArg:
    out = RenderingArg()
    out.url = url

    extracted_texts = []

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

    def append_newline():
        if extracted_texts and extracted_texts[-1] != "<br>":
            extracted_texts.append("<br>")

    try:
        # Fetch HTML
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        response.encoding = "utf-8"
        original_html = response.text

        soup = BeautifulSoup(original_html, "html.parser")

        # Extract Anchors
        for anchor_element in soup.find_all("a"):
            out.anchors.append(
                Anchor(href=anchor_element.attrs.get("href"), content=anchor_element.get_text(strip=True))
            )

        # Eliminate seemingly noisy tags
        for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            tag.decompose()

        # Extract Lists
        out.uls = [extract_li_list(ul) for ul in soup.find_all("ul")]
        out.ols = [extract_li_list(ol) for ol in soup.find_all("ol")]

        # Extract seemingly content tags
        candidates = soup.find_all(['article', 'main', 'section', 'div'])
        longest = max(candidates, key=lambda tag: len(tag.get_text(strip=True)), default=None)
        assert longest is not None, "No content found."

        # Extract content
        tree(longest)

        # Pack
        out.content_html = "".join(extracted_texts)
        out.has_meta = True
        out.original_html_length = len(original_html)
        out.content_html_length = len(out.content_html)
        out.compression_rate = \
            "?" if out.original_html_length == 0 \
                else f"{100 * out.content_html_length / out.original_html_length:.2f}%"

    except Exception as e:
        out.content_html = str(e)

    return out

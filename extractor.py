import requests
from bs4 import BeautifulSoup
from renderer import RenderingArg, Anchor


def extract_content_html(url: str) -> RenderingArg:
    out = RenderingArg()
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

        # Extract seemingly content tags
        candidates = soup.find_all(['article', 'main', 'section', 'div'])
        longest = max(candidates, key=lambda tag: len(tag.get_text(strip=True)), default=None)
        assert longest is not None, "No content found."

        # Pack
        out.content_html = longest.get_text(strip=True, separator="\n")
        out.has_meta = True
        out.original_html_length = len(original_html)
        out.content_html_length = len(out.content_html)
        out.compression_rate = \
            "?" if out.original_html_length == 0 \
                else f"{100 * out.content_html_length / out.original_html_length:.2f}%"

    except Exception as e:
        out.content_html = str(e)

    return out

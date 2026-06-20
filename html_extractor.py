import argparse
import sys
from pathlib import Path
from bs4 import BeautifulSoup, Comment
import requests


def fetch_html(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    response.encoding = response.encoding or response.apparent_encoding
    return response.text


def extract_as_html(url: str) -> dict:
    html = fetch_html(url)
    return extract_as_html_by_raw(html)


def extract_as_html_by_raw(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    # タイトル
    title = None
    title_element = soup.find("title")
    if title_element:
        title = title_element.get_text(strip=True)
    # 不要そうなタグを削除
    for tag in soup(
        ["script", "style", "header", "footer", "nav", "aside", "head", "button", "svg"]
    ):
        tag.extract()
    # コメントを削除
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment.extract()
    # レンダリング時に不要な装飾を避けるため、一部のタグをdivに変更
    for tag in soup(["article", "section"]):
        tag.name = "div"
    # 画像をアンカーに置き換え
    for img in soup("img"):
        src = str(img.attrs.get("src") or "")
        alt = str(img.attrs.get("alt") or "")
        kbd = soup.new_tag("kbd")
        kbd.string = "IMAGE"
        a = soup.new_tag("a")
        a.append(kbd)
        a.append(alt)
        a.attrs["href"] = src
        img.replace_with(a)
    # 属性を全削除
    for tag in soup.find_all(True):
        href_val = tag.attrs.get("href")
        tag.attrs.clear()
        if href_val is not None:
            tag.attrs["href"] = href_val
    # 空白のdivを削除
    for div in soup("div"):
        if div.get_text(strip=True) == "":
            div.extract()
    # さらに短く
    shorten_html = str(soup)
    shorten_html = shorten_html.replace("\n", "")

    return {"title": title, "html": shorten_html}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTML Extractor")
    parser.add_argument("input", help="URL or Local File")
    parser.add_argument("-o", "--output", default="out.html", help="Output File")
    args = parser.parse_args()

    try:
        if args.input.startswith("http://") or args.input.startswith("https://"):
            result = extract_as_html(args.input)
        else:
            raw_html = Path(args.input).read_text(encoding="utf-8")
            result = extract_as_html_by_raw(raw_html)
        print("Title:", result["title"])
        Path(args.output).write_text(result["html"], encoding="utf-8")
    except Exception as e:
        print(e, file=sys.stderr)

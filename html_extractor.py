import argparse
import sys
from pathlib import Path
from bs4 import BeautifulSoup, Comment
import requests
import re
from urllib.parse import urljoin

CANDIDATE_ENCODINGS = ["utf-8", "shift-jis", "euc_jp", "iso2022_jp", "cp932"]


def decode(raw: bytes):
    # 複数の文字コードでデコード
    success = []
    for encoding in CANDIDATE_ENCODINGS:
        try:
            text = raw.decode(encoding=encoding)
            success.append((encoding, text))
        except Exception as e:
            pass
    # 全滅したら
    if not success:
        raise UnicodeDecodeError("Failed to decode.")
    # 1つだけ成功したら
    if len(success) == 1:
        return success[0][1]

    # 複数成功したら
    detected_encoding = None
    # <meta charset="...">を抽出する
    try:
        head = raw[:8192].decode("ascii", errors="ignore")
        m = re.search(
            r"<meta[^>]+charset=[\"\']?([a-zA-Z0-9_\-]+)[\"\']?", head, re.IGNORECASE
        )
        if m:
            detected_encoding = m.group(1).lower()
    except Exception as e:
        pass
    if detected_encoding is not None:
        for encoding, text in success:
            if encoding == detected_encoding:
                return text
    return success[0][1]


def fetch_html(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return decode(response.content)


def extract_as_html(url: str) -> dict:
    html = fetch_html(url)
    return extract_as_html_by_raw(html, base_url=url)


def extract_as_html_by_raw(html: str, base_url:str="") -> dict:
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
    # 属性を全削除・リンクの絶対パスを作る
    for tag in soup.find_all(True):
        href_val = tag.attrs.get("href")
        tag.attrs.clear()
        if href_val is not None:
            tag.attrs["href"] = urljoin(base_url, href_val)
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

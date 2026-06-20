import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse
import mimetypes
import tempfile

import requests
from pypdf import PdfReader


def _safe_filename(url: str) -> str:
    parsed = urlparse(url)
    base = Path(parsed.path).name or "document.pdf"
    base = "".join(ch for ch in base if ch.isalnum() or ch in "._-")
    if not base.lower().endswith(".pdf"):
        base += ".pdf"
    return base[:120]


def fetch_pdf(url: str) -> tuple[Path, tempfile.TemporaryDirectory]:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=20, stream=True)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if "pdf" not in content_type and mimetypes.guess_type(url)[0] != "application/pdf":
        raise ValueError(f"Not a PDF URL: {content_type or 'unknown content-type'}")

    tmpdir = tempfile.TemporaryDirectory()
    pdf_path = Path(tmpdir.name) / _safe_filename(url)

    with open(pdf_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    # tmpdirごと返す（スコープ外で消えないように）
    return pdf_path, tmpdir


def extract_as_pdf(url: str) -> dict:
    pdf_path, tmpdir = fetch_pdf(url)
    try:
        return extract_as_pdf_by_file(pdf_path)
    finally:
        tmpdir.cleanup()


def extract_as_pdf_by_file(path: Path) -> dict:
    reader = PdfReader(str(path))

    texts = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text:
            texts.append(page_text)

    content = "\n\n".join(texts).strip()

    title = None
    meta = reader.metadata
    if meta is not None:
        title = getattr(meta, "title", None)

    return {"title": title, "text": content}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF Extractor")
    parser.add_argument("input", help="URL or Local File")
    parser.add_argument("-o", "--output", default="out.txt", help="Output File")
    args = parser.parse_args()

    try:
        if args.input.startswith("http://") or args.input.startswith("https://"):
            result = extract_as_pdf(args.input)
        else:
            result = extract_as_pdf_by_file(Path(args.input))

        print("Title:", result["title"])
        Path(args.output).write_text(result["text"])

    except Exception as e:
        print(e, file=sys.stderr)

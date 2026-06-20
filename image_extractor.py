import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse
import io

import requests
from PIL import Image

MAX_SIZE = 30 * 1024


def fetch_image(url: str) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if not content_type.startswith("image/"):
        raise ValueError(f"Not an image URL: {content_type or 'unknown'}")

    return response.content


def compress_image_to_limit(image_bytes: bytes, max_size: int = MAX_SIZE) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))

    # RGBへ（PNG対策）
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    quality = 85
    buffer = io.BytesIO()
    width, height = img.size

    # 品質とサイズを段階的に落とす
    while True:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)

        size = buffer.getbuffer().nbytes
        if size <= max_size or quality <= 10 or width <= 50 or height <= 50:
            break

        quality -= 5
        width = int(width * 0.9)
        height = int(height * 0.9)

        img = img.resize((width, height))

    return buffer.getvalue()


def extract_as_image(url: str) -> dict:
    raw = fetch_image(url)
    compressed = compress_image_to_limit(raw)

    parsed = urlparse(url)
    name = Path(parsed.path).name or "image.jpg"

    return {
        "filename": name,
        "size": len(compressed),
        "data": compressed,
    }


def extract_as_image_by_file(path: Path) -> dict:
    raw = path.read_bytes()
    compressed = compress_image_to_limit(raw)

    return {
        "filename": path.name,
        "size": len(compressed),
        "data": compressed,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image Extractor")
    parser.add_argument("input", help="Image URL or Local File")
    parser.add_argument("-o", "--output", default="out.jpg", help="Output file")
    args = parser.parse_args()

    try:
        if args.input.startswith("http://") or args.input.startswith("https://"):
            result = extract_as_image(args.input)
        else:
            result = extract_as_image_by_file(Path(args.input))

        print("Filename:", result["filename"])
        print("Size:", result["size"], "bytes")

        Path(args.output).write_bytes(result["data"])

    except Exception as e:
        print(e, file=sys.stderr)

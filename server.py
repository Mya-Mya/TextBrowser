from flask import Flask, request, render_template, make_response
from argparse import ArgumentParser
from html_extractor import extract_as_html
from pdf_extractor import extract_as_pdf
from image_extractor import extract_as_image
from http_utils import is_safe_url, sanitize_url


def parse_argument() -> dict:
    parser = ArgumentParser(prog="TextBrowser")
    parser.add_argument("--port", default=60000, required=False, type=int)
    args = parser.parse_args()
    return {"port": args.port}


def return_error_page(message: str):
    return render_template("error.html", message=message)


def handle_extraction_request(url: str, type: str):
    url = sanitize_url(url)
    if not is_safe_url(url):
        raise ValueError("Failed to fetch.")

    if type == "html":
        result = extract_as_html(url)
        return render_template("htmlpage.html", **result)
    if type == "pdf":
        result = extract_as_pdf(url)
        html = result["text"].replace("\n", "<br>")
        return render_template("htmlpage.html", title=result["title"], html=html)
    if type == "image":
        result = extract_as_image(url)
        response = make_response(result["data"])
        response.headers.set("Content-Type", "image/jpg")
        filename = result["filename"]
        response.headers.set("Content-Disposition", f"inline; filename=\"{filename}\"")
        return response
    return return_error_page(f"The page type {type} is not supported.")


if __name__ == "__main__":
    parser = ArgumentParser(prog="TextBrowser")
    parser.add_argument("--port", default=60000, required=False, type=int)
    args = parser.parse_args()

    app = Flask(import_name=__name__)

    @app.get("/")
    def handle():
        url = request.args.get("url")
        type = request.args.get("type")

        if url is not None and type is not None:
            try:
                return handle_extraction_request(url, type)
            except Exception as e:
                return return_error_page(str(e))
        return render_template("home.html")

    app.run(host="0.0.0.0", port=int(args.port), debug=False)

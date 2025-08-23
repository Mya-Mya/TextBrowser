from flask import Flask, make_response, request
from argparse import ArgumentParser
from urllib.parse import urlparse
import socket
import ipaddress
from extractor import extract_content_html
from renderer import RenderingArg, render


def parse_argument() -> dict:
    parser = ArgumentParser(prog="TextBrowser")
    parser.add_argument("--port", default=60000, required=False, type=int)
    args = parser.parse_args()
    return {
        "port": args.port
    }


def is_safe_url(url: str) -> bool:
    try:
        hostname = urlparse(url).hostname
        ip_address_str = socket.gethostbyname(hostname)
        ip_address = ipaddress.ip_address(ip_address_str)
        return not (
                ip_address.is_private or
                ip_address.is_loopback or
                ip_address.is_unspecified or
                ip_address.is_reserved or
                ip_address.is_link_local
        )
    except Exception as e:
        return False


if __name__ == "__main__":
    args = parse_argument()
    app = Flask(import_name=__name__)
    @app.route("/", methods=["GET", "POST"])
    def handle():
        rendering_arg = RenderingArg()
        if request.method == "POST":
            url = request.form.get("url")
            if is_safe_url(url):
                rendering_arg = extract_content_html(url)
        rendered_html = render(rendering_arg)
        return make_response(rendered_html)


    app.run(
        host="0.0.0.0",
        port=args["port"],
        debug=False
    )

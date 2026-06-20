from urllib.parse import urlparse
import socket
import ipaddress


def is_safe_url(url: str) -> bool:
    try:
        hostname = str(urlparse(url).hostname)
        ip_address_str = socket.gethostbyname(hostname)
        ip_address = ipaddress.ip_address(ip_address_str)
        return not (
            ip_address.is_private
            or ip_address.is_loopback
            or ip_address.is_unspecified
            or ip_address.is_reserved
            or ip_address.is_link_local
        )
    except Exception as e:
        return False


def sanitize_url(url: str) -> str:
    starts_with_http = url.startswith("http://")
    starts_with_https = url.startswith("https://")
    if (not starts_with_http) and (not starts_with_https):
        url = "https://" + url
    return url

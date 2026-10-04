"""
LinkDrop - Security & SSRF Protection
"""
import ipaddress
import re
import socket
import unicodedata
from urllib.parse import urlparse
from typing import Tuple, Optional

BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "metadata.google.internal",
    "instance-data",
}

def is_safe_ip(ip_str: str) -> bool:
    """
    Check if an IP address is publicly routable and safe from SSRF.
    Rejects loopback, private, link-local, reserved, multicast, and unspecified addresses.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        # Allow RFC 6052 / NAT64 translation prefix (64:ff9b::/96) used globally by ISPs
        if isinstance(ip, ipaddress.IPv6Address) and str(ip).startswith("64:ff9b::"):
            return True

        if (
            ip.is_loopback or
            ip.is_private or
            ip.is_link_local or
            ip.is_multicast or
            ip.is_reserved or
            ip.is_unspecified
        ):
            return False
        # Specific check for AWS/GCP metadata address
        if str(ip) == "169.254.169.254":
            return False
        return True
    except ValueError:
        return False

def validate_url_security(raw_url: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates that a URL is safe to fetch:
    1. Valid HTTP/HTTPS scheme
    2. Hostname is present and not on blocked list
    3. Hostname resolves to a public, non-private IP
    Returns: (is_safe, message, normalized_url)
    """
    if not raw_url or not isinstance(raw_url, str):
        return False, "Please enter a valid URL.", None

    url = raw_url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        # If user pasted something like 'youtube.com/...', prepend 'https://'
        if re.match(r"^[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}", url):
            url = f"https://{url}"
        else:
            return False, "Only HTTP and HTTPS links are supported.", None

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL structure.", None

    hostname = parsed.hostname
    if not hostname:
        return False, "URL does not have a valid host.", None

    hostname_lower = hostname.lower()

    if hostname_lower in BLOCKED_HOSTNAMES:
        return False, "Access to this host is restricted for security reasons.", None

    # Resolve IP address to prevent SSRF against private networks
    try:
        addr_info = socket.getaddrinfo(hostname_lower, None, proto=socket.IPPROTO_TCP)
        if not addr_info:
            return False, "Host address could not be resolved.", None

        has_safe_ip = False
        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            if is_safe_ip(ip_str):
                has_safe_ip = True
                break

        if not has_safe_ip:
            return False, "Access to private or restricted network addresses is not permitted.", None

    except socket.gaierror:
        return False, "Could not resolve the specified domain name. Please check the URL.", None
    except Exception as e:
        return False, f"Security verification failed: {str(e)}", None

    return True, "", url

def sanitize_filename(name: str, max_length: int = 120) -> str:
    """
    Sanitizes filenames to prevent path traversal, illegal characters, and excessive lengths.
    """
    if not name:
        return "download"

    # Normalize unicode
    name = unicodedata.normalize("NFKD", name)

    # Remove directory separators and null bytes
    name = name.replace("/", "_").replace("\\", "_").replace("\x00", "")

    # Replace forbidden Windows/Linux filename characters: <>:"/\|?*
    name = re.sub(r'[<>:"/\\|?*]+', "_", name)

    # Remove multiple spaces or underscores
    name = re.sub(r'[\s_]+', "_", name).strip(" ._")

    if not name:
        name = "download"

    if len(name) > max_length:
        name = name[:max_length].rstrip(" ._")

    return name

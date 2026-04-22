"""Web scraper for extracting product page content."""

import httpx
import subprocess
import time
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urlparse


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Safari bridge script path (relative to stonerOS root)
SAFARI_BRIDGE = Path(__file__).resolve().parent.parent.parent / "scripts" / "safari-bridge.sh"

# Minimum body text length to consider a scrape successful
MIN_TEXT_LENGTH = 200


def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    return domain.removeprefix("www.")


def normalize_url(url: str) -> str:
    """Ensure URL has scheme and strip trailing slash."""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def _scrape_safari(url: str) -> str:
    """Fallback: use Safari bridge ax-text to scrape JS-rendered pages.

    Opens the URL in Safari, waits for render, extracts all visible text
    via accessibility APIs. Returns extracted text or empty string on failure.
    """
    if not SAFARI_BRIDGE.exists():
        return ""

    bridge = str(SAFARI_BRIDGE)
    try:
        subprocess.run([bridge, "open", url], capture_output=True, timeout=10)
        time.sleep(3)
        result = subprocess.run(
            [bridge, "ax-text"], capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, OSError):
        return ""


def scrape_page(url: str) -> dict:
    """Scrape a product page and extract structured content.

    Tries httpx first. If the page returns minimal text (JS-rendered),
    automatically falls back to Safari bridge ax-text extraction.

    Returns dict with: url, domain, title, meta_description, body_text,
    disclaimers, raw_html_length, scrape_method
    """
    url = normalize_url(url)
    scrape_method = "httpx"
    html = ""
    title = ""
    meta_desc = ""
    body_text = ""
    lines = []

    # Try httpx first; fall through to Safari on HTTP errors
    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=20) as client:
            resp = client.get(url)
            resp.raise_for_status()
        html = resp.text
    except httpx.HTTPStatusError:
        html = ""
    except httpx.RequestError:
        html = ""

    if html:
        soup = BeautifulSoup(html, "html.parser")

        # Remove noise
        for tag in soup(["script", "style", "nav", "header", "footer", "iframe"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        body_text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in body_text.splitlines() if line.strip()]
        body_text = "\n".join(lines)

    # If httpx failed or returned minimal text, try Safari bridge
    if len(body_text) < MIN_TEXT_LENGTH:
        safari_text = _scrape_safari(url)
        if len(safari_text) > len(body_text):
            body_text = safari_text
            lines = [line.strip() for line in body_text.splitlines() if line.strip()]
            scrape_method = "safari-bridge"

    # Look for disclaimers
    disclaimers = []
    disclaimer_keywords = ["not a medical device", "fda", "disclaimer", "not intended to diagnose",
                           "not evaluated", "consult your doctor", "individual results may vary"]
    for line in lines:
        if any(kw in line.lower() for kw in disclaimer_keywords):
            disclaimers.append(line)

    return {
        "url": url,
        "domain": extract_domain(url),
        "title": title,
        "meta_description": meta_desc,
        "body_text": body_text[:15000],
        "disclaimers": disclaimers,
        "raw_html_length": len(html),
        "scrape_method": scrape_method,
    }

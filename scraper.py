"""Web scraper for extracting product page content."""

import httpx
from bs4 import BeautifulSoup
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


def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split("/")[0]
    return domain.removeprefix("www.")


def normalize_url(url: str) -> str:
    """Ensure URL has scheme and strip trailing slash."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def scrape_page(url: str) -> dict:
    """Scrape a product page and extract structured content.

    Returns dict with: url, domain, title, meta_description, body_text,
    disclaimers, links, raw_html_length
    """
    url = normalize_url(url)

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=20) as client:
        resp = client.get(url)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "nav", "header", "footer", "iframe"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_desc = meta_tag["content"].strip()

    # Extract visible text
    body_text = soup.get_text(separator="\n", strip=True)
    # Collapse excessive whitespace
    lines = [line.strip() for line in body_text.splitlines() if line.strip()]
    body_text = "\n".join(lines)

    # Look for disclaimers specifically
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
        "body_text": body_text[:15000],  # Cap for LLM context
        "disclaimers": disclaimers,
        "raw_html_length": len(resp.text),
    }

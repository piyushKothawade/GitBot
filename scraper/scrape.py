"""
scraper/scrape.py
-----------------
Crawls GitLab Handbook (handbook.gitlab.com) and Direction
(about.gitlab.com/direction) pages, extracts clean text, and saves
each page as a JSON file under data/raw/.

Run:
    python -m scraper.scrape
"""

import json
import time
import hashlib
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────

SEEDS = [
    "https://handbook.gitlab.com/",
    "https://about.gitlab.com/direction/",
]

ALLOWED_DOMAINS = {"handbook.gitlab.com", "about.gitlab.com"}

# Only crawl paths under /direction/ for about.gitlab.com
DOMAIN_PATH_PREFIX = {
    "about.gitlab.com": "/direction",
}

MAX_PAGES = 500          # Safety cap — raise if you want deeper crawl
REQUEST_DELAY = 0.5      # Seconds between requests (be polite)
REQUEST_TIMEOUT = 15
OUTPUT_DIR = Path("data/raw")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GitLabChatbotBot/1.0; "
        "+https://github.com/your-repo)"
    )
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Page:
    url: str
    title: str
    content: str          # Clean text, newline-separated sections
    source: str           # "handbook" | "direction"
    headings: list[str]   # H1-H3 headings found on the page


# ── Helpers ───────────────────────────────────────────────────────────────────

def url_id(url: str) -> str:
    """Stable short ID for a URL — used as filename."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def is_allowed(url: str) -> bool:
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain not in ALLOWED_DOMAINS:
        return False
    prefix = DOMAIN_PATH_PREFIX.get(domain)
    if prefix and not parsed.path.startswith(prefix):
        return False
    # Skip anchors, media, non-HTML
    if any(url.endswith(ext) for ext in (".png", ".jpg", ".svg", ".pdf", ".zip")):
        return False
    return True


def classify_source(url: str) -> str:
    return "handbook" if "handbook.gitlab.com" in url else "direction"


def extract_page(url: str, html: str) -> Page:
    """Parse HTML → clean Page object."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove noisy elements
    for tag in soup(["script", "style", "nav", "footer", "header",
                      "aside", "form", "svg", "img"]):
        tag.decompose()

    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url

    # Collect headings for metadata
    headings = [
        h.get_text(strip=True)
        for h in soup.find_all(["h1", "h2", "h3"])
    ]

    # Try to isolate the main content area
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(class_="content")
        or soup.body
    )

    # Walk block elements, preserving structure with newlines
    lines = []
    if main:
        for elem in main.find_all(
            ["h1", "h2", "h3", "h4", "p", "li", "td", "th", "blockquote"],
            recursive=True,
        ):
            text = elem.get_text(separator=" ", strip=True)
            if text and len(text) > 20:   # Skip trivial snippets
                lines.append(text)

    content = "\n\n".join(lines)

    return Page(
        url=url,
        title=title,
        content=content,
        source=classify_source(url),
        headings=headings[:30],   # Cap to keep JSON lean
    )


def collect_links(url: str, html: str) -> list[str]:
    """Extract all internal allowed links from a page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        # Strip fragment
        href = href.split("#")[0].rstrip("/")
        if href and is_allowed(href):
            links.append(href)
    return list(set(links))


# ── Crawler ───────────────────────────────────────────────────────────────────

def crawl() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    visited: set[str] = set()
    queue: list[str] = list(SEEDS)
    session = requests.Session()
    session.headers.update(HEADERS)

    saved = 0

    while queue and saved < MAX_PAGES:
        url = queue.pop(0)
        url = url.split("#")[0].rstrip("/")

        if url in visited:
            continue
        visited.add(url)

        try:
            log.info(f"[{saved+1}] Fetching: {url}")
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except Exception as e:
            log.warning(f"  ✗ Failed: {e}")
            continue

        if "text/html" not in resp.headers.get("Content-Type", ""):
            continue

        page = extract_page(url, resp.text)

        # Skip near-empty pages (likely 404 pages or redirects)
        if len(page.content) < 200:
            log.info(f"  ↷ Skipping (too short): {url}")
            continue

        # Save to disk
        out_path = OUTPUT_DIR / f"{url_id(url)}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(asdict(page), f, ensure_ascii=False, indent=2)

        saved += 1
        log.info(f"  ✓ Saved ({len(page.content)} chars, {len(page.headings)} headings)")

        # Discover new links
        new_links = collect_links(url, resp.text)
        for link in new_links:
            if link not in visited:
                queue.append(link)

        time.sleep(REQUEST_DELAY)

    log.info(f"\nDone. {saved} pages saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    crawl()
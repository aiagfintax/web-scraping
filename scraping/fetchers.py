"""Download pages: plain HTTP for static sites, headless Chromium for JavaScript sites."""
import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import httpx
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

_robots_cache = {}


def allowed_by_robots(url):
    if not settings.SCRAPER_RESPECT_ROBOTS:
        return True
    parts = urlparse(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if root not in _robots_cache:
        parser = urllib.robotparser.RobotFileParser()
        try:
            resp = httpx.get(urljoin(root, "/robots.txt"), timeout=10, follow_redirects=True,
                             headers={"User-Agent": settings.SCRAPER_USER_AGENT})
            parser.parse(resp.text.splitlines() if resp.status_code == 200 else [])
        except httpx.HTTPError:
            parser.parse([])
        _robots_cache[root] = parser
    return _robots_cache[root].can_fetch(settings.SCRAPER_USER_AGENT, url)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def fetch_static(url):
    resp = httpx.get(url, timeout=30, follow_redirects=True,
                     headers={"User-Agent": settings.SCRAPER_USER_AGENT})
    resp.raise_for_status()
    return str(resp.url), resp.text


class BrowserSession:
    """One headless Chromium instance reused for every page in a run."""

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True, args=["--no-sandbox"])
        self._page = self._browser.new_page(user_agent=settings.SCRAPER_USER_AGENT)
        return self

    def fetch(self, url):
        self._page.goto(url, wait_until="domcontentloaded", timeout=45000)
        try:
            self._page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass  # busy sites never go idle; use what has rendered
        # Scroll a few times so lazy-loaded content appears.
        for _ in range(3):
            self._page.mouse.wheel(0, 4000)
            self._page.wait_for_timeout(600)
        return self._page.url, self._page.content()

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()


def polite_pause():
    time.sleep(settings.SCRAPER_DELAY_SECONDS)

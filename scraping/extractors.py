"""Turn the fields a user typed into values pulled out of a page.

Field syntax (comma separated):
  emails, phones, title        built-in keywords (see BUILT_INS)
  name                         any other word: guessed from itemprop/class/id containing it
  price=.product-price         custom label = CSS selector (text)
  link=a.more@href             CSS selector @attribute
"""
import re
from io import StringIO
from urllib.parse import urljoin

from bs4 import BeautifulSoup

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
PRICE_RE = re.compile(r"(?:[$€£₹]\s?\d[\d,]*(?:\.\d{2})?|\d[\d,]*(?:\.\d{2})?\s?(?:USD|EUR|GBP|INR))")
SOCIAL_HOSTS = ("facebook.com", "twitter.com", "x.com", "linkedin.com", "instagram.com", "youtube.com", "tiktok.com")
JOIN = "; "
TABLES = "tables"


def _unique(values):
    seen, out = set(), []
    for v in values:
        v = (v or "").strip()
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _emails(node, base):
    found = [a["href"][7:].split("?")[0] for a in node.select('a[href^="mailto:"]')]
    found += EMAIL_RE.findall(node.get_text(" "))
    return JOIN.join(_unique(e.lower() for e in found
                             if not e.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif"))))


def _phones(node, base):
    found = [a["href"][4:] for a in node.select('a[href^="tel:"]')]
    found += PHONE_RE.findall(node.get_text(" "))
    return JOIN.join(_unique(found))


def _links(node, base):
    return JOIN.join(_unique(urljoin(base, a["href"]) for a in node.select("a[href]")
                             if not a["href"].startswith(("#", "javascript:", "mailto:", "tel:"))))


def _images(node, base):
    return JOIN.join(_unique(urljoin(base, i["src"]) for i in node.select("img[src]")))


def _social(node, base):
    return JOIN.join(_unique(a["href"] for a in node.select("a[href]")
                             if any(h in a["href"] for h in SOCIAL_HOSTS)))


def _prices(node, base):
    return JOIN.join(_unique(PRICE_RE.findall(node.get_text(" "))))


def _title(node, base):
    t = node.find("title") or node.find(["h1", "h2", "h3"])
    return _clean(t.get_text()) if t else ""


def _description(node, base):
    m = node.find("meta", attrs={"name": "description"}) or node.find("meta", attrs={"property": "og:description"})
    return _clean(m.get("content", "")) if m else ""


def _headings(node, base):
    return JOIN.join(_unique(_clean(h.get_text()) for h in node.find_all(["h1", "h2", "h3"])))


def _text(node, base):
    return _clean(node.get_text(" "))[:30000]


def _address(node, base):
    tag = node.find("address") or node.select_one('[itemprop="address"], [class*="address"]')
    return _clean(tag.get_text(" ")) if tag else ""


BUILT_INS = {
    "emails": _emails, "email": _emails,
    "phones": _phones, "phone": _phones,
    "links": _links, "images": _images, "social": _social,
    "prices": _prices, "price": _prices,
    "title": _title, "description": _description,
    "headings": _headings, "text": _text, "address": _address,
}


def parse_fields(raw):
    """'emails, name=h2, link=a@href' -> [(label, kind, selector, attr)]."""
    specs = []
    for part in [p.strip() for p in raw.split(",") if p.strip()]:
        if "=" in part:
            label, selector = [s.strip() for s in part.split("=", 1)]
            attr = None
            if "@" in selector:
                selector, attr = [s.strip() for s in selector.rsplit("@", 1)]
            specs.append((label, "css", selector, attr))
        elif part.lower() in BUILT_INS or part.lower() == TABLES:
            specs.append((part.lower(), "builtin", None, None))
        else:
            specs.append((part, "guess", None, None))
    return specs


def _css_value(node, selector, attr, base):
    values = []
    for h in node.select(selector):
        if attr:
            v = h.get(attr, "")
            values.append(urljoin(base, v) if attr in ("href", "src") else v)
        else:
            values.append(_clean(h.get_text(" ")))
    return JOIN.join(_unique(values))


def _guess_value(node, word, base):
    w = re.sub(r"[^a-z0-9_-]", "", word.lower())
    if not w:
        return ""
    selector = (f'[itemprop*="{w}" i], [class*="{w}" i], [id*="{w}" i], '
                f'[data-testid*="{w}" i], [aria-label*="{w}" i]')
    hits = node.select(selector)
    # Prefer the innermost matches so we don't return a whole container.
    leaves = [h for h in hits if not h.select(selector)]
    return JOIN.join(_unique(_clean(h.get_text(" ")) for h in leaves)[:5])


def extract(html, url, specs, item_selector=""):
    """Return (rows, tables). rows: list of dicts. tables: list of DataFrames."""
    soup = BeautifulSoup(html, "lxml")
    tables = []
    if any(s[0] == TABLES for s in specs):
        import pandas as pd
        try:
            tables = pd.read_html(StringIO(html))
        except ValueError:
            tables = []

    nodes = soup.select(item_selector) if item_selector else [soup]
    rows = []
    for node in nodes:
        row = {"source_url": url}
        for label, kind, selector, attr in specs:
            if label == TABLES:
                continue
            if kind == "builtin":
                row[label] = BUILT_INS[label](node, url)
            elif kind == "css":
                row[label] = _css_value(node, selector, attr, url)
            else:
                row[label] = _guess_value(node, label, url)
        if not item_selector or any(v for k, v in row.items() if k != "source_url"):
            rows.append(row)
    return rows, tables


def next_page_url(html, url, next_selector):
    if not next_selector:
        return None
    tag = BeautifulSoup(html, "lxml").select_one(next_selector)
    if tag and tag.get("href"):
        return urljoin(url, tag["href"])
    return None


def looks_empty(html):
    """Heuristic: a page with almost no visible text probably needs JavaScript."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    return len(soup.get_text(" ", strip=True)) < 300

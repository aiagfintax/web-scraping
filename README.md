# Web Scraper

A small Django app: type website URLs and the fields you want, and get an Excel file back.

- **Fetching:** `httpx` for static pages, **Playwright + headless Chromium** for JavaScript pages ("Auto" mode tries static first and switches to Chromium when the page is nearly empty).
- **Parsing:** BeautifulSoup + lxml, pandas for HTML tables.
- **Output:** formatted `.xlsx` (openpyxl): bold header, filters, frozen top row, one extra sheet per HTML table.
- **Front end:** plain HTML + CSS, no JavaScript.

## Run with Docker

```bash
cp .env.example .env        # set DJANGO_SECRET_KEY
docker compose up --build
```

Open http://localhost:8000. Data (SQLite DB and Excel files) lives in the `scraper_data` volume.

## Run without Docker

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt     # Windows; use .venv/bin/pip on macOS/Linux
.venv/Scripts/playwright install chromium
.venv/Scripts/python manage.py migrate
.venv/Scripts/python manage.py runserver
```

## Typing fields

Comma separated. Mix any of these:

| You type | You get |
|---|---|
| `emails`, `phones`, `title`, `description`, `headings`, `address`, `prices`, `links`, `images`, `social`, `text` | Ready-made extractors |
| `tables` | Every HTML `<table>` on the page as its own Excel sheet |
| `name`, `rating`, any word | Text of elements whose class / id / itemprop contains that word |
| `company=h2.title` | Text matched by a CSS selector, in a column called `company` |
| `website=a.visit@href` | An attribute of the matched element |

**Repeating item selector** (Advanced): e.g. `.listing-card`. Each match becomes one Excel row and fields are read inside it. Without it you get one row per page.

**Next page selector**: e.g. `a.next`. The scraper follows it up to "Max pages".

Example: a directory page with cards

- URL: `https://example.com/firms`
- Fields: `name, phones, emails, website=a.site@href`
- Item selector: `.firm-card`
- Next page: `a.next`, max pages `5`

## Finding selectors

Open the site in Chrome, right-click the value, Inspect, and read the class names. Claude Code with the Playwright MCP can do this for you: give it the URL and the fields and ask for the selectors.

## Settings (env vars)

| Variable | Default | Meaning |
|---|---|---|
| `SCRAPER_DELAY_SECONDS` | `1.5` | Pause between page requests |
| `SCRAPER_MAX_PAGES` | `20` | Hard cap on pages per URL |
| `SCRAPER_RESPECT_ROBOTS` | `1` | Skip URLs disallowed by `robots.txt` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Add your domain when deploying |

## Notes

- The scrape runs inside the web request (simple by design). Gunicorn's timeout is 10 minutes, so keep runs modest (≤ 50 URLs, ≤ 20 pages each).
- There is no login. Don't expose it on the public internet as is: anyone could use it to make your server fetch arbitrary URLs. Put it behind a VPN or add authentication first.
- Only scrape sites whose terms allow it. The scraper does not bypass logins or CAPTCHAs.

## Tests

```bash
python manage.py test
```

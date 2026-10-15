"""Run one scrape from start to finish."""
import traceback

from django.conf import settings

from . import extractors, fetchers
from .exporter import write_excel


def run_scrape(run):
    log = []
    specs = extractors.parse_fields(run.fields)
    all_rows, all_tables = [], []
    browser = None
    max_pages = max(1, min(run.max_pages, settings.SCRAPER_MAX_PAGES))

    def browser_fetch(url):
        nonlocal browser
        if browser is None:
            browser = fetchers.BrowserSession().__enter__()
        return browser.fetch(url)

    def get(url):
        if run.mode == "browser":
            return browser_fetch(url)
        final_url, html = fetchers.fetch_static(url)
        if run.mode == "auto" and extractors.looks_empty(html):
            log.append(f"{url}: little static content, retrying with Chromium")
            return browser_fetch(url)
        return final_url, html

    try:
        for start_url in run.url_list():
            url, page = start_url, 0
            while url and page < max_pages:
                page += 1
                if not fetchers.allowed_by_robots(url):
                    log.append(f"{url}: blocked by robots.txt, skipped")
                    break
                try:
                    final_url, html = get(url)
                except Exception as exc:  # one bad URL should not kill the run
                    log.append(f"{url}: fetch failed ({exc.__class__.__name__}: {exc})")
                    break
                rows, tables = extractors.extract(html, final_url, specs, run.item_selector)
                all_rows.extend(rows)
                all_tables.extend(tables)
                log.append(f"{final_url}: {len(rows)} row(s)" + (f", {len(tables)} table(s)" if tables else ""))
                url = extractors.next_page_url(html, final_url, run.next_selector)
                fetchers.polite_pause()

        name, count = write_excel(run.pk, all_rows, all_tables)
        run.excel_file = name
        run.row_count = count
        run.preview = all_rows[:20]
        run.status = "done"
    except Exception:
        log.append(traceback.format_exc())
        run.status = "failed"
    finally:
        if browser is not None:
            browser.__exit__(None, None, None)
        run.log = "\n".join(log)
        run.save()
    return run

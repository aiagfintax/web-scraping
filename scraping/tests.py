from django.test import TestCase

from .extractors import extract, next_page_url, parse_fields

PAGE = """
<html><head><title>Acme Directory</title>
<meta name="description" content="Local firms"></head>
<body>
  <div class="card"><h2 class="firm-name">Alpha CPA</h2>
    <a href="mailto:hello@alpha.com">Email</a> <span class="tel">(555) 123-4567</span>
    <a class="site" href="/alpha">Visit</a></div>
  <div class="card"><h2 class="firm-name">Beta Tax</h2>
    <p>Write to info@beta.com or call +1 555 987 6543</p>
    <a class="site" href="https://beta.example">Visit</a></div>
  <table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>
  <a class="next" href="?page=2">Next</a>
</body></html>
"""


class ExtractTests(TestCase):
    def test_page_level_builtins(self):
        rows, tables = extract(PAGE, "https://x.test/", parse_fields("title, description, emails, tables"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Acme Directory")
        self.assertEqual(rows[0]["description"], "Local firms")
        self.assertEqual(rows[0]["emails"], "hello@alpha.com; info@beta.com")
        self.assertEqual(len(tables), 1)

    def test_item_rows_with_css_guess_and_attr(self):
        specs = parse_fields("name, phones, emails, website=a.site@href")
        rows, _ = extract(PAGE, "https://x.test/", specs, item_selector=".card")
        self.assertEqual([r["name"] for r in rows], ["Alpha CPA", "Beta Tax"])
        self.assertEqual(rows[0]["website"], "https://x.test/alpha")
        self.assertEqual(rows[1]["emails"], "info@beta.com")
        self.assertIn("555 987 6543", rows[1]["phones"])

    def test_next_page(self):
        self.assertEqual(next_page_url(PAGE, "https://x.test/list", "a.next"), "https://x.test/list?page=2")
        self.assertIsNone(next_page_url(PAGE, "https://x.test/list", ""))


class FormTests(TestCase):
    def test_rejects_non_http_urls(self):
        resp = self.client.post("/", {"urls": "file:///etc/passwd", "fields": "text",
                                      "max_pages": 1, "mode": "static"})
        self.assertContains(resp, "Not a valid http(s) URL")

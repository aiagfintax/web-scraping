from django.db import models


class ScrapeRun(models.Model):
    MODES = [("auto", "Auto"), ("static", "Static (fast)"), ("browser", "Browser (JavaScript)")]
    STATUSES = [("running", "Running"), ("done", "Done"), ("failed", "Failed")]

    urls = models.TextField()
    fields = models.CharField(max_length=1000)
    item_selector = models.CharField(max_length=500, blank=True)
    next_selector = models.CharField(max_length=500, blank=True)
    max_pages = models.PositiveIntegerField(default=1)
    mode = models.CharField(max_length=10, choices=MODES, default="auto")
    status = models.CharField(max_length=10, choices=STATUSES, default="running")
    row_count = models.PositiveIntegerField(default=0)
    excel_file = models.CharField(max_length=300, blank=True)
    log = models.TextField(blank=True)
    preview = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Run {self.pk} ({self.status})"

    def url_list(self):
        return [u.strip() for u in self.urls.splitlines() if u.strip()]

    def preview_columns(self):
        return list(self.preview[0].keys()) if self.preview else []

    def preview_rows(self):
        cols = self.preview_columns()
        return [[str(r.get(c, ""))[:300] for c in cols] for r in self.preview]

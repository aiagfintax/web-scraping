from urllib.parse import urlparse

from django import forms

from .models import ScrapeRun


class ScrapeForm(forms.ModelForm):
    class Meta:
        model = ScrapeRun
        fields = ["urls", "fields", "item_selector", "next_selector", "max_pages", "mode"]
        widgets = {
            "urls": forms.Textarea(attrs={"rows": 4, "placeholder": "https://example.com/page-1\nhttps://example.com/page-2"}),
            "fields": forms.TextInput(attrs={"placeholder": "emails, phones, title, name=h2.title, website=a.site@href"}),
            "item_selector": forms.TextInput(attrs={"placeholder": "optional, e.g. .listing-card (one row per card)"}),
            "next_selector": forms.TextInput(attrs={"placeholder": "optional, e.g. a.next"}),
        }

    def clean_urls(self):
        urls = [u.strip() for u in self.cleaned_data["urls"].splitlines() if u.strip()]
        if not urls:
            raise forms.ValidationError("Enter at least one URL.")
        if len(urls) > 50:
            raise forms.ValidationError("At most 50 URLs per run.")
        for u in urls:
            p = urlparse(u)
            if p.scheme not in ("http", "https") or not p.netloc:
                raise forms.ValidationError(f"Not a valid http(s) URL: {u}")
        return "\n".join(urls)

    def clean_max_pages(self):
        return max(1, min(self.cleaned_data["max_pages"], 20))

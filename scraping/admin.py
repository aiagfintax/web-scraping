from django.contrib import admin

from .models import ScrapeRun


@admin.register(ScrapeRun)
class ScrapeRunAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "status", "mode", "row_count", "fields")
    list_filter = ("status", "mode")

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ScrapeForm
from .models import ScrapeRun
from .runner import run_scrape


def index(request):
    form = ScrapeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        run = form.save()
        run_scrape(run)
        return redirect("run_detail", pk=run.pk)
    return render(request, "scraping/index.html", {
        "form": form,
        "runs": ScrapeRun.objects.all()[:15],
    })


def run_detail(request, pk):
    run = get_object_or_404(ScrapeRun, pk=pk)
    return render(request, "scraping/run.html", {"run": run})


def download(request, pk):
    run = get_object_or_404(ScrapeRun, pk=pk)
    path = Path(settings.MEDIA_ROOT) / run.excel_file
    if not run.excel_file or not path.is_file():
        raise Http404("No Excel file for this run")
    return FileResponse(open(path, "rb"), as_attachment=True, filename=run.excel_file)

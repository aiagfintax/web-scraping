# Official Playwright image: Python + Chromium + all its system libraries.
# Keep the tag in step with the playwright version in requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN DJANGO_SECRET_KEY=build python manage.py collectstatic --noinput \
    && mkdir -p /data && chmod +x docker-entrypoint.sh

VOLUME ["/data"]
EXPOSE 8000
ENTRYPOINT ["./docker-entrypoint.sh"]
# Long timeout: a scrape runs inside the request.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "600"]

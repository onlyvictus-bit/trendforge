FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRENDFORGE_DB_PATH=/app/data/trendforge_research.db

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend
COPY config /app/config
COPY README.md AGENTS.md /app/

RUN addgroup --system trendforge \
    && adduser --system --ingroup trendforge trendforge \
    && mkdir -p /app/data \
    && chown -R trendforge:trendforge /app

USER trendforge
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

CMD ["python", "-m", "uvicorn", "trendforge_api.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]


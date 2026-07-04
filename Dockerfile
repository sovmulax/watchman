# --- build stage ---
FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 libffi-dev libcairo2 && rm -rf /var/lib/apt/lists/*
COPY requirements/ requirements/
RUN pip install --no-cache-dir --prefix=/install -r requirements/prod.txt

# --- runtime stage ---
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/install/bin:$PATH \
    PYTHONPATH=/install/lib/python3.12/site-packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser
COPY --from=builder /install /install
WORKDIR /app
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

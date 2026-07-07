# ============================================================
# Stage 1: Build dependencies
# ============================================================
FROM python:3.11-bullseye AS builder

WORKDIR /app

# System dependencies untuk mysqlclient dan cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    default-libmysqlclient-dev \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# Stage 2: Production image
# ============================================================
FROM python:3.11-slim-bullseye

WORKDIR /app

# Runtime dependencies (tanpa compiler)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev \
    libffi7 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages dari builder stage
COPY --from=builder /install /usr/local

# Buat non-root user
RUN useradd -m -r appuser && \
    mkdir -p /app/staticfiles /app/media && \
    chown -R appuser:appuser /app

# Copy source code
COPY --chown=appuser:appuser . .

# Collect static files (butuh SECRET_KEY dummy saat build)
RUN SECRET_KEY=build-placeholder \
    DEBUG=False \
    DB_ENGINE=django.db.backends.sqlite3 \
    DB_NAME=/tmp/db.sqlite3 \
    python manage.py collectstatic --noinput

# Switch ke non-root user
USER appuser

# Port yang diexpose
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/ppid/')" || exit 1

# Jalankan Gunicorn
CMD ["gunicorn", "core.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]

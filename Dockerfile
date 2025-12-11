FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Build cache bust argument: bump this to force pip reinstall during CI builds
ARG CACHEBUST=1

# Install system deps needed by some packages (Pillow, psycopg, weasyprint deps are heavy,
# keep minimal here; you may need to add more libs if build fails on Vercel)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    ca-certificates \
    # For weasyprint / rendering
    libcairo2 libcairo2-dev libpango-1.0-0 libpango1.0-dev libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 libgdk-pixbuf-xlib-2.0-dev libffi-dev \
    libxml2 libxml2-dev libxslt1.1 libxslt1-dev \
    shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

# Ensure the binary psycopg2 driver is installed even if cached layers persist
RUN pip install --upgrade pip && pip install --no-cache-dir psycopg2-binary==2.9.7
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Default port (platform provides $PORT at runtime)
ENV PORT 8080
EXPOSE 8080

# Run with gunicorn and bind to the platform provided $PORT
# Use 2 workers and a timeout to be more resilient in PaaS environments
CMD exec gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2 --timeout 120

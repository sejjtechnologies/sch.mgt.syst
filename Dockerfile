FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps needed by some packages (Pillow, psycopg, weasyprint deps are heavy,
# keep minimal here; you may need to add more libs if build fails on Vercel)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

# Default port (Vercel provides $PORT at runtime)
ENV PORT 8080
EXPOSE 8080

# Run with gunicorn and bind to the platform provided $PORT
CMD exec gunicorn app:app --bind 0.0.0.0:${PORT} --workers 1

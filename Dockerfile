# WUALT KWS collection server — lightweight (Flask + ffmpeg, no ML).
# Recordings are written to /data, which MUST be a persistent volume on the host
# so all data lives in the backend and survives restarts/redeploys.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

COPY collect_server.py tamil_keywords.py hindi_keywords.py ./

# Central storage lives here — mount a persistent volume at /data in production.
ENV STORAGE_DIR=/data \
    PORT=8080 \
    LANGS=ta,hi
RUN mkdir -p /data
EXPOSE 8080

# 2 workers is plenty for recording uploads; long timeout for the ffmpeg convert.
# Shell form so ${PORT} expands — Render (and most PaaS) inject the port to bind.
CMD gunicorn -w 2 -b 0.0.0.0:${PORT:-8080} --timeout 120 collect_server:app

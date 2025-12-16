# syntax=docker/dockerfile:1
# Highly specific Dockerfile for DailyAccomplishments

FROM python:3.12-slim

# Install system dependencies for matplotlib and Pillow
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libfreetype6-dev \
        libpng-dev \
        libjpeg-dev \
        libopenjp2-7-dev \
        libtiff5-dev \
        tcl8.6-dev tk8.6-dev \
        python3-tk \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy only necessary files for report generation and web serving
COPY tools/ ./tools/
COPY *.py ./
COPY *.json ./
COPY server.py ./server.py
COPY *.csv ./
COPY *.html ./
COPY favicon.ico ./
COPY dashboard/ ./dashboard/
COPY reports/ ./reports/
# Ensure the published dashboard from gh-pages is served from the static root
COPY gh-pages/dashboard.html ./dashboard.html
COPY railway-start.sh /app/railway-start.sh

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Expose a default port for local development; production platforms (e.g. Railway)
# usually provide the port to listen on via the $PORT environment variable.
EXPOSE 8000

# Default command: serve dashboard and reports. Use the PORT env var if present
# so the container will work correctly on platforms that set $PORT (Railway,
# Heroku-style platforms). Fall back to 8000 for local runs.
# Copy and use an entrypoint script that logs env and starts the server
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh /app/railway-start.sh

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]

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
COPY *.json ./
COPY *.csv ./
COPY *.md ./
COPY *.html ./

# Install Python dependencies
RUN pip install --no-cache-dir matplotlib pillow

# Expose a default port for local development; production platforms (e.g. Railway)
# usually provide the port to listen on via the $PORT environment variable.
EXPOSE 8000

# Default command: serve dashboard and reports. Use the PORT env var if present
# so the container will work correctly on platforms that set $PORT (Railway,
# Heroku-style platforms). Fall back to 8000 for local runs.
# Copy and use an entrypoint script that logs env and starts the server
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]

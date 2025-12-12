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

WORKDIR /app

# Copy the repo into the image (includes reports/, ActivityReport-*.json, tools/, scripts/, etc.)
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir matplotlib pillow

# Expose a default port for local development
EXPOSE 8000

# Use an entrypoint that respects $PORT when present
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
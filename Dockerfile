# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for DailyAccomplishments with React build + Flask static serving

FROM node:22-bookworm AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

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

# Copy application files
COPY tools/ ./tools/
COPY *.py ./
COPY *.json ./
COPY server.py ./server.py
COPY *.csv ./
COPY *.html ./
COPY favicon.ico ./
COPY dashboard/ ./dashboard/
COPY reports/ ./reports/
COPY gh-pages/dashboard.html ./dashboard.html
COPY railway-start.sh /app/railway-start.sh
COPY entrypoint.sh /app/entrypoint.sh

# Frontend build artifacts
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

RUN chmod +x /app/entrypoint.sh /app/railway-start.sh
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]

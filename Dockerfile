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

# Copy application files
# Note: Some files/directories may not exist yet in early development
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir matplotlib pillow

# Expose port for local web server
EXPOSE 8000

# Default command: serve dashboard and reports
CMD ["python3", "-m", "http.server", "8000"]

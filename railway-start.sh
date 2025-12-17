#!/bin/sh
set -eu

ROOT_DIR="$(pwd)"
SITE_DIR="${SITE_DIR:-site}"
PORT="${PORT:-8080}"
FRONTEND_DIST="${ROOT_DIR}/frontend/dist"

rm -rf "${SITE_DIR}"
mkdir -p "${SITE_DIR}"

if [ -d "${FRONTEND_DIST}" ]; then
  echo "Copying React build from ${FRONTEND_DIST}"
  cp -R "${FRONTEND_DIST}/". "${SITE_DIR}/"
fi

# Keep legacy dashboard available if present
if [ -f "${ROOT_DIR}/gh-pages/dashboard.html" ]; then
  cp -f "${ROOT_DIR}/gh-pages/dashboard.html" "${SITE_DIR}/dashboard.html"
elif [ -f "${ROOT_DIR}/dashboard.html" ]; then
  cp -f "${ROOT_DIR}/dashboard.html" "${SITE_DIR}/dashboard.html"
fi

# Copy dashboard assets (chart.min.js, etc.) for legacy dashboard
if [ -d "${ROOT_DIR}/dashboard" ]; then
  cp -R "${ROOT_DIR}/dashboard" "${SITE_DIR}/dashboard"
fi

if [ -f "${ROOT_DIR}/config.json" ]; then
  cp -f "${ROOT_DIR}/config.json" "${SITE_DIR}/config.json"
fi

if [ -d "${ROOT_DIR}/reports" ]; then
  rm -rf "${SITE_DIR}/reports"
  ln -s "${ROOT_DIR}/reports" "${SITE_DIR}/reports"
fi

set -- "${ROOT_DIR}"/ActivityReport-*.json
if [ -e "$1" ]; then
  for report in "$@"; do
    name="$(basename "${report}")"
    rm -f "${SITE_DIR}/${name}"
    ln -s "${report}" "${SITE_DIR}/${name}"
  done
fi

if [ -f "${ROOT_DIR}/favicon.ico" ]; then
  rm -f "${SITE_DIR}/favicon.ico"
  ln -s "${ROOT_DIR}/favicon.ico" "${SITE_DIR}/favicon.ico"
fi

# Ensure an index.html exists for Flask to serve
if [ ! -f "${SITE_DIR}/index.html" ]; then
  if [ -f "${ROOT_DIR}/index.html" ]; then
    cp -f "${ROOT_DIR}/index.html" "${SITE_DIR}/index.html"
  elif [ -f "${SITE_DIR}/dashboard.html" ]; then
    cp -f "${SITE_DIR}/dashboard.html" "${SITE_DIR}/index.html"
  else
    echo "ERROR: No index.html available for serving" >&2
    exit 1
  fi
fi

echo "Serving ${ROOT_DIR}/${SITE_DIR} on 0.0.0.0:${PORT}"

# Use a production WSGI server on Railway (the Flask dev server logs to stderr and
# is not recommended for production).
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
GUNICORN_THREADS="${GUNICORN_THREADS:-4}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-60}"

exec python3 -m gunicorn \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --threads "${GUNICORN_THREADS}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --access-logfile "-" \
  --error-logfile "-" \
  "server:app"

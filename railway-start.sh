#!/bin/sh
set -eu

ROOT_DIR="$(pwd)"
SITE_DIR="${SITE_DIR:-site}"
PORT="${PORT:-8000}"

mkdir -p "${SITE_DIR}"

# Always serve a single, consistent web root that contains:
# - dashboard.html
# - config.json
# - reports/ (symlinked)
# - ActivityReport-*.json (symlinked, if present)

rm -f "${SITE_DIR}/dashboard.html"
if [ -f "${ROOT_DIR}/gh-pages/dashboard.html" ]; then
  cp -f "${ROOT_DIR}/gh-pages/dashboard.html" "${SITE_DIR}/dashboard.html"
elif [ -f "${ROOT_DIR}/dashboard.html" ]; then
  cp -f "${ROOT_DIR}/dashboard.html" "${SITE_DIR}/dashboard.html"
else
  echo "ERROR: dashboard.html not found (expected gh-pages/dashboard.html or dashboard.html in ${ROOT_DIR})" >&2
  exit 1
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
if [ -f "${ROOT_DIR}/index.html" ]; then
  cp -f "${ROOT_DIR}/index.html" "${SITE_DIR}/index.html"
fi

echo "Serving ${ROOT_DIR}/${SITE_DIR} on 0.0.0.0:${PORT}"
cd "${SITE_DIR}"
exec python3 "${ROOT_DIR}/server.py"

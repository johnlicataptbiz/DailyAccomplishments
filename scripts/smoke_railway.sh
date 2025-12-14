#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-https://dailyaccomplishments.up.railway.app}}"

DATE_JSON="${DATE_JSON:-2025-12-08}"
DATE_NESTED="${DATE_NESTED:-2025-12-13}"
DATE_MISSING="${DATE_MISSING:-2025-12-14}"

check() {
  local path="$1"
  echo "--- ${BASE_URL}${path}"
  curl -sS -I "${BASE_URL}${path}" | head -n 5
  echo
}

check "/dashboard.html"
check "/config.json"
check "/reports/daily-report-${DATE_JSON}.json"
check "/reports/${DATE_NESTED}/ActivityReport-${DATE_NESTED}.json"
check "/ActivityReport-${DATE_NESTED}.json"
check "/reports/daily-report-${DATE_MISSING}.json"


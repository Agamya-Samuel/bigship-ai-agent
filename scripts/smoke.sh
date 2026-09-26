#!/usr/bin/env bash
# Smoke test: api health + web index + authme 401 shape. No secrets needed.
set -euo pipefail
API="${API_BASE:-http://localhost:8000}"
WEB="${WEB_BASE:-http://localhost:3000}"

echo "== api $API/health"
curl -fsS "$API/health" | grep -q '"status"'
echo ok

echo "== web $WEB/"
curl -fsS "$WEB/" | grep -qi '<div id="root"'
echo ok

echo "== auth guard $API/auth/me (expect 401/403)"
code=$(curl -s -o /dev/null -w "%{http_code}" "$API/auth/me")
if [[ "$code" != "401" && "$code" != "403" ]]; then
  echo "unexpected status $code" >&2; exit 1
fi
echo "ok ($code)"
echo ALL-SMOKE-OK

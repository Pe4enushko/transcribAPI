#!/usr/bin/env bash
set -euo pipefail

FILENAME="1776855364.1498403.mp3"
ENV_FILE="$(dirname "$0")/../.env"

env_value() {
  local key="$1"
  local default_value="$2"
  local line

  line="$(grep -m 1 "^${key}=" "$ENV_FILE" 2>/dev/null || true)"
  if [[ -n "$line" ]]; then
    printf '%s' "${line#*=}"
  else
    printf '%s' "$default_value"
  fi
}

APP_PORT="$(env_value APP_PORT 8000)"
USERNAME="$(env_value LOGIN_USERNAME admin)"
PASSWORD="$(env_value LOGIN_PASSWORD SafePass_2026)"
BASE_URL="http://localhost:${APP_PORT}"

LOGIN_BODY="$(
  USERNAME="$USERNAME" PASSWORD="$PASSWORD" python3 -c '
import json
import os

print(json.dumps({
    "username": os.environ["USERNAME"],
    "password": os.environ["PASSWORD"],
}))
'
)"

echo "Logging in to ${BASE_URL}/login as ${USERNAME}"
TOKEN="$(
  curl -sS -X POST "${BASE_URL}/login" \
    -H "Content-Type: application/json" \
    -d "$LOGIN_BODY" \
  | python3 -c '
import json
import sys

data = json.load(sys.stdin)
print(data["access_token"])
'
)"

echo "Querying filename: ${FILENAME}"
curl -sS -X GET "${BASE_URL}/query/${FILENAME}" \
  -H "Authorization: Bearer ${TOKEN}"
echo

#!/usr/bin/env bash
set -euo pipefail

ORG_ID="your-org-uuid-here"
DATE="2024-01-15"

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
import json, os
print(json.dumps({"username": os.environ["USERNAME"], "password": os.environ["PASSWORD"]}))
'
)"

echo "Logging in to ${BASE_URL}/login as ${USERNAME}"
TOKEN="$(
  curl -sS -X POST "${BASE_URL}/login" \
    -H "Content-Type: application/json" \
    -d "$LOGIN_BODY" \
  | python3 -c '
import json, sys
print(json.load(sys.stdin)["access_token"])
'
)"

echo "Querying /consultdata — org: ${ORG_ID}  date: ${DATE}"
curl -sS -X GET "${BASE_URL}/consultdata" \
  -G \
  --data-urlencode "organization_id=${ORG_ID}" \
  --data-urlencode "date=${DATE}" \
  -H "Authorization: Bearer ${TOKEN}" \
| python3 << 'EOF'
import json, sys
data = json.load(sys.stdin)
records = data.get("records", [])
print("organization_id :", data["organization_id"])
print("date            :", data["date"])
print("records found   :", len(records))
for i, r in enumerate(records, 1):
    print(f"\n--- record {i} ---")
    print("  id              :", r["id"])
    print("  conversation_id :", r["conversation_id"])
    print("  created_at      :", r["created_at"])
    dialog = r["dialog"]
    print("  dialog          :", dialog[:80] + ("..." if len(dialog) > 80 else ""))
    for name, val in r.items():
        if name.startswith("score_"):
            print(f"  {name:<45}: {val}")
EOF
echo

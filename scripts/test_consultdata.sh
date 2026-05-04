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
| python3 -c '
import json, sys
data = json.load(sys.stdin)
records = data.get("records", [])
print(f"organization_id : {data[\"organization_id\"]}")
print(f"date            : {data[\"date\"]}")
print(f"records found   : {len(records)}")
for i, r in enumerate(records, 1):
    print(f"\n--- record {i} ---")
    print(f"  id              : {r[\"id\"]}")
    print(f"  conversation_id : {r[\"conversation_id\"]}")
    print(f"  created_at      : {r[\"created_at\"]}")
    print(f"  dialog          : {r[\"dialog\"][:80]}{'..." if len(r["dialog"]) > 80 else ""}")
    scores = {k: v for k, v in r.items() if k.startswith("score_")}
    for name, val in scores.items():
        print(f"  {name:<45}: {val}")
'
echo

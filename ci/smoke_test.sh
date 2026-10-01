#!/bin/bash
# Post-deployment smoke test: is the environment really up and running the version we just built?
# Usage: bash ci/smoke_test.sh <frontend_url> <backend_url> <expected_version> [expected_mock_mode]
FRONTEND="$1"
BACKEND="$2"
EXPECTED="$3"
EXPECTED_MOCK="${4:-}"     # true (staging) / false (production); empty = not checked

echo "Smoke test: frontend=$FRONTEND backend=$BACKEND expected version=$EXPECTED"

# 1. Wait up to 60s for the backend health endpoint.
BODY=""
for _ in $(seq 1 30); do
    BODY=$(curl -fsS --max-time 3 "$BACKEND/api/health" 2>/dev/null) && break
    sleep 2
done
if [ -z "$BODY" ]; then
    echo "FAIL: backend /api/health did not respond within 60s"
    exit 1
fi
echo "  /api/health -> $BODY"

# 2. The running build must be the one we just deployed.
if ! echo "$BODY" | grep -q "\"version\":\"$EXPECTED\""; then
    echo "FAIL: backend is not running version $EXPECTED"
    exit 1
fi

# 3. Right data source: staging uses mock data, production must use the real API.
if [ -n "$EXPECTED_MOCK" ] && ! echo "$BODY" | grep -q "\"mock_mode\":$EXPECTED_MOCK"; then
    echo "FAIL: expected mock_mode=$EXPECTED_MOCK (production must not serve sample data)"
    exit 1
fi

# 4. Frontend page, the nginx -> backend proxy, and one real API route.
check() {
    if curl -fsS --max-time 10 "$1" | grep -q "$2"; then
        echo "  OK   $1"
    else
        echo "FAIL: $1 (expected to contain: $2)"
        exit 1
    fi
}
check "$FRONTEND/" '<div id="app">'
check "$FRONTEND/api/health" '"status":"ok"'
check "$FRONTEND/api/standings?league=39" '"response"'

echo "SMOKE TEST PASSED"

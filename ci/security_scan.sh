#!/bin/bash
# Security stage of the Jenkins pipeline.
# Runs 5 scans, saves every report to reports/security/, then applies the SECURITY GATE:
#
#   Scan                               Tool        Build fails when...
#   1. Python code (SAST)              Bandit      any MEDIUM or HIGH severity issue
#   2. Python dependencies (SCA)       pip-audit   any known vulnerability (CVE/PYSEC)
#   3. JavaScript dependencies (SCA)   npm audit   any HIGH or CRITICAL issue in production dependencies
#   4. Docker images (OS + libraries)  Trivy       any CRITICAL vulnerability that has a fix
#   5. Dockerfiles (misconfiguration)  Trivy       any HIGH or CRITICAL misconfiguration
#
# Every scan always runs (even if an earlier one fails) so the full picture is in the reports.

REPORTS="reports/security"
mkdir -p "$REPORTS"
FAILED=""
TRIVY_IMAGE="aquasec/trivy:0.74.0"

# Trivy runs in Docker: it reads local images through the Docker socket and caches its DB in a volume.
trivy() {
    docker run --rm \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v trivy-cache:/root/.cache \
        -v "$PWD":/src -w /src \
        "$TRIVY_IMAGE" "$@"
}

. .venv/bin/activate
python -m pip install -q bandit==1.9.4 pip-audit==2.10.1

echo "==================== 1/5 Bandit: Python code (SAST) ===================="
bandit -q -r backend -x backend/tests -f json -o "$REPORTS/bandit.json" || true
bandit -q -r backend -x backend/tests --severity-level medium || FAILED="$FAILED Bandit"

echo "==================== 2/5 pip-audit: Python dependencies ================"
# The lock file lists every package that goes into the image (including indirect dependencies).
pip-audit -r backend/requirements.lock --no-deps --disable-pip -f json -o "$REPORTS/pip-audit.json" || true
pip-audit -r backend/requirements.lock --no-deps --disable-pip || FAILED="$FAILED pip-audit"

echo "==================== 3/5 npm audit: JavaScript dependencies ============="
(cd frontend && npm audit --json > "../$REPORTS/npm-audit.json") || true
(cd frontend && npm audit) || true   # full list (including dev tools) for information
(cd frontend && npm audit --omit=dev --audit-level=high) || FAILED="$FAILED npm-audit"

echo "==================== 4/5 Trivy: Docker images =========================="
for IMAGE in "$BACKEND_IMAGE:$IMAGE_TAG" "$FRONTEND_IMAGE:$IMAGE_TAG"; do
    NAME=$(echo "$IMAGE" | cut -d: -f1)
    trivy image --quiet --scanners vuln --severity HIGH,CRITICAL --format json -o "$REPORTS/trivy-$NAME.json" "$IMAGE" || true
    trivy image --quiet --scanners vuln --severity HIGH,CRITICAL "$IMAGE" || true
    trivy image --quiet --scanners vuln --severity CRITICAL --ignore-unfixed --exit-code 1 "$IMAGE" \
        || FAILED="$FAILED trivy-$NAME"
done

echo "==================== 5/5 Trivy: Dockerfile misconfiguration ============="
for DOCKERFILE in backend/Dockerfile frontend/Dockerfile; do
    trivy config --quiet --severity HIGH,CRITICAL --exit-code 1 "$DOCKERFILE" \
        || FAILED="$FAILED config:$DOCKERFILE"
done

echo "========================================================================="
if [ -n "$FAILED" ]; then
    echo "SECURITY GATE FAILED:$FAILED"
    echo "Reports: $REPORTS/ (archived as build artifacts)"
    exit 1
fi
echo "SECURITY GATE PASSED - no findings above the thresholds."

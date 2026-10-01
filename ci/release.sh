#!/bin/bash
# Release stage: promote the tested images to PRODUCTION, with automatic ROLLBACK.
#   1. Remember which version is live now.
#   2. Deploy the new version with docker compose.
#   3. Smoke test production. If it fails, redeploy the previous version and fail the build.
# Needs IMAGE_TAG (from Jenkins). SIMULATE_BAD_RELEASE=true deploys with a broken setting on purpose
# (the backend listens on the wrong port), to demonstrate the rollback.

COMPOSE="docker compose -p fmh-prod --env-file deploy/prod.env -f deploy/docker-compose.yml"
FRONTEND_URL="http://localhost:8088"
BACKEND_URL="http://localhost:8002"
STATE_DIR="$HOME/.fmh-release"          # kept outside the workspace so it survives clean builds
mkdir -p "$STATE_DIR"

PREVIOUS=$(cat "$STATE_DIR/current" 2>/dev/null)
echo "Live production version before release: ${PREVIOUS:-none (first release)}"
echo "Releasing version: $IMAGE_TAG"

if [ "${SIMULATE_BAD_RELEASE:-false}" = "true" ]; then
    echo "!! SIMULATE_BAD_RELEASE=true: deploying with a wrong backend port to test the rollback"
    export BACKEND_INTERNAL_PORT=9999
fi

IMAGE_TAG="$IMAGE_TAG" $COMPOSE up -d --remove-orphans

if bash ci/smoke_test.sh "$FRONTEND_URL" "$BACKEND_URL" "$IMAGE_TAG"; then
    echo "$IMAGE_TAG" > "$STATE_DIR/current"
    [ -n "$PREVIOUS" ] && echo "$PREVIOUS" > "$STATE_DIR/previous"
    echo "RELEASE OK: production is now running $IMAGE_TAG ($FRONTEND_URL)"
    exit 0
fi

echo "RELEASE FAILED: production smoke test failed for $IMAGE_TAG"
$COMPOSE logs --tail=30 backend || true

if [ -n "$PREVIOUS" ]; then
    echo "ROLLING BACK production to $PREVIOUS ..."
    export BACKEND_INTERNAL_PORT=8000
    IMAGE_TAG="$PREVIOUS" $COMPOSE up -d --remove-orphans
    if bash ci/smoke_test.sh "$FRONTEND_URL" "$BACKEND_URL" "$PREVIOUS"; then
        echo "ROLLBACK OK: production restored to $PREVIOUS"
    else
        echo "ROLLBACK FAILED: manual action needed"
    fi
else
    echo "No previous version to roll back to; stopping the broken release."
    IMAGE_TAG="$IMAGE_TAG" $COMPOSE down
fi
exit 1

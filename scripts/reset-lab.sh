#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$ROOT_DIR/.docker"
ENV_FILE="$DOCKER_DIR/.env"

echo ""
echo "=============================================="
echo "  STARFALL DEFENCE CORPS ACADEMY"
echo "  Resetting the range..."
echo "=============================================="
echo ""

echo "  Tearing down the current range..."
docker compose -f "$DOCKER_DIR/docker-compose.yml" --env-file "$ENV_FILE" down -v 2>&1 \
    | sed 's/^/    /' || true

# Clear latched range state so the rebuild re-randomises cleanly.
rm -f "$ROOT_DIR/.lab/baseline.json" 2>/dev/null || true

echo ""
echo "  Rebuilding..."
bash "$SCRIPT_DIR/setup-lab.sh"

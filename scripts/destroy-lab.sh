#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$ROOT_DIR/.docker"
ENV_FILE="$DOCKER_DIR/.env"

echo ""
echo "=============================================="
echo "  STARFALL DEFENCE CORPS ACADEMY"
echo "  Full teardown"
echo "=============================================="
echo ""

echo "  Stopping and removing containers/images..."
docker compose -f "$DOCKER_DIR/docker-compose.yml" --env-file "$ENV_FILE" down -v --rmi local 2>&1 \
    | sed 's/^/    /' || true

echo "  Removing range state, keys, and Python env..."
rm -rf "$DOCKER_DIR/ssh-keys" "$ROOT_DIR/workspace/.ssh" "$ROOT_DIR/.lab" "$ROOT_DIR/venv"
rm -f "$ENV_FILE"

echo ""
echo "=============================================="
echo "  Range destroyed. Run 'make setup' to rebuild."
echo "=============================================="
echo ""

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Starting dufs via docker compose..."
docker compose -f docker-compose.test.yml up -d --wait

echo "==> Running integration tests..."
uv run pytest tests/integration/ -m dufs -v --no-cov || EXIT=$?

echo "==> Tearing down dufs..."
docker compose -f docker-compose.test.yml down -v

exit "${EXIT:-0}"

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Running unit tests with coverage..."
uv run pytest tests/unit/ -v

echo ""
echo "==> Starting dufs via docker compose..."
docker compose -f docker-compose.test.yml up -d --wait

echo "==> Running integration tests..."
uv run pytest tests/integration/ -m dufs -v --no-cov || EXIT_INT=$?

echo "==> Running e2e tests..."
uv run pytest tests/e2e/ -m dufs -v --no-cov || EXIT_E2E=$?

echo "==> Tearing down dufs..."
docker compose -f docker-compose.test.yml down -v

if [ "${EXIT_INT:-0}" -ne 0 ] || [ "${EXIT_E2E:-0}" -ne 0 ]; then
    echo "FAIL: Some tests failed."
    exit 1
fi

echo "ALL TESTS PASSED."

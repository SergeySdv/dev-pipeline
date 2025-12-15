#!/bin/bash
set -e

echo "=============================================="
echo "DevGodzilla Test Suite"
echo "=============================================="

cd "$(dirname "$0")/.."

echo ""
echo "[1/2] Running onboarding test..."
.venv/bin/python scripts/test_devgodzilla_onboard.py

echo ""
echo "[2/2] Running E2E test..."
.venv/bin/python scripts/test_devgodzilla_e2e.py

echo ""
echo "=============================================="
echo "All DevGodzilla tests passed!"
echo "=============================================="

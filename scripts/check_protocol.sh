#!/bin/bash
API_BASE="http://localhost"

TOKEN_RESPONSE=$(curl -s -X POST "${API_BASE}/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "changeme"}')
TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "=== Protocol Run 3 Details ==="
curl -s "${API_BASE}/protocols/3" -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Protocol Name: {data.get(\"protocol_name\")}')
print(f'Status: {data.get(\"status\")}')
print(f'Worktree Path: {data.get(\"worktree_path\")}')
print(f'Protocol Root: {data.get(\"protocol_root\")}')
"

echo ""
echo "=== Checking worktree inside container ==="
docker compose exec worker ls -la /app/worktrees/ 2>/dev/null || echo "No worktrees dir"
docker compose exec worker ls -la /app/worktrees/setup-3/.protocols/setup-3/ 2>/dev/null || echo "No protocols dir yet"

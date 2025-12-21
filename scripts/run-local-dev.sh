#!/bin/bash
# Local Development Script for DevGodzilla
# This script runs the backend API and frontend locally while using Docker for DB/Redis/Windmill

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== DevGodzilla Local Development ===${NC}"

# Check if Docker services are running
echo -e "${YELLOW}Checking Docker services...${NC}"
if ! docker ps | grep -q "dev-pipeline-db-1"; then
    echo -e "${RED}Database container not running. Starting infrastructure services...${NC}"
    docker compose -f docker-compose.devgodzilla.yml up -d db redis windmill windmill_worker windmill_worker_native lsp nginx
    echo "Waiting for database to be ready..."
    sleep 10
fi

# Export environment variables for local development
export DEVGODZILLA_DB_URL="postgresql://devgodzilla:changeme@localhost:5432/devgodzilla_db"
export DEVGODZILLA_LOG_LEVEL="DEBUG"
export DEVGODZILLA_WINDMILL_URL="http://localhost:8080"
export DEVGODZILLA_WINDMILL_WORKSPACE="demo1"
export DEVGODZILLA_PROJECTS_ROOT="$PROJECT_DIR/projects"

# Check for AI engine CLI tools
echo -e "${YELLOW}Checking AI engine CLI tools...${NC}"
if command -v opencode &> /dev/null; then
    echo -e "${GREEN}✓ opencode CLI found at: $(which opencode)${NC}"
else
    echo -e "${YELLOW}⚠ opencode CLI not found${NC}"
fi

if command -v gemini &> /dev/null; then
    echo -e "${GREEN}✓ gemini CLI found at: $(which gemini)${NC}"
else
    echo -e "${YELLOW}⚠ gemini CLI not found${NC}"
fi

if command -v claude &> /dev/null; then
    echo -e "${GREEN}✓ claude CLI found at: $(which claude)${NC}"
else
    echo -e "${YELLOW}⚠ claude CLI not found${NC}"
fi

# Make sure Postgres port is exposed
echo -e "${YELLOW}Exposing database port 5432...${NC}"
docker compose -f docker-compose.devgodzilla.yml stop devgodzilla-api frontend 2>/dev/null || true

# Check if DB port is accessible
if ! nc -z localhost 5432 2>/dev/null; then
    echo -e "${YELLOW}Mapping database port...${NC}"
    # Need to recreate db with port mapping
    docker compose -f docker-compose.local.yml up -d db redis
fi

echo ""
echo -e "${GREEN}=== Environment Ready ===${NC}"
echo ""
echo "To run the backend API locally:"
echo -e "${YELLOW}  cd $PROJECT_DIR${NC}"
echo -e "${YELLOW}  source .venv/bin/activate${NC}"
echo -e "${YELLOW}  uvicorn devgodzilla.api.app:app --host 0.0.0.0 --port 8000 --reload${NC}"
echo ""
echo "To run the frontend locally (in another terminal):"
echo -e "${YELLOW}  cd $PROJECT_DIR/frontend${NC}"
echo -e "${YELLOW}  pnpm dev${NC}"
echo ""
echo "Access points:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"  
echo "  - Frontend: http://localhost:3000"
echo "  - Windmill: http://localhost:8080"
echo ""

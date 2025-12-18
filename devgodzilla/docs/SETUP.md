# DevGodzilla Setup Guide

## Prerequisites

- **Python 3.12+**
- **PostgreSQL 14+** (for production) or SQLite (for development)
- **Git**

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourorg/dev-pipeline.git
cd dev-pipeline
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Database Setup

#### SQLite (Development)

DevGodzilla uses SQLite by default for development:

```bash
# Set environment variable
export DEVGODZILLA_DB_PATH=./devgodzilla.db

# Initialize database
python -c "from pathlib import Path; from devgodzilla.db.database import SQLiteDatabase; SQLiteDatabase(Path('devgodzilla.db')).init_schema()"
```

#### PostgreSQL (Production)

For production, use PostgreSQL:

```bash
# Set connection string
export DEVGODZILLA_DB_URL=postgresql://user:password@localhost:5432/devgodzilla

# Run Alembic migrations
cd devgodzilla
alembic upgrade head
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEVGODZILLA_DB_PATH` | SQLite database file path | `.devgodzilla.sqlite` |
| `DEVGODZILLA_DB_URL` | PostgreSQL connection string | None |
| `DEVGODZILLA_LOG_LEVEL` | Logging level | `INFO` |
| `DEVGODZILLA_API_HOST` | API host | `0.0.0.0` |
| `DEVGODZILLA_API_PORT` | API port | `8000` |
| `DEVGODZILLA_DEFAULT_ENGINE_ID` | Default engine ID for headless workflows | `opencode` |
| `DEVGODZILLA_OPENCODE_MODEL` | Default model for the `opencode` engine | `zai-coding-plan/glm-4.6` |
| `DEVGODZILLA_AUTO_GENERATE_PROTOCOL` | Auto-generate `.protocols/<name>/step-*.md` when missing | `true` |
| `DEVGODZILLA_DISCOVERY_TIMEOUT_SECONDS` | Timeout for headless repo discovery | `900` |
| `DEVGODZILLA_PROTOCOL_GENERATE_TIMEOUT_SECONDS` | Timeout for headless protocol generation | `900` |
| `DEVGODZILLA_WINDMILL_URL` | Windmill base URL (no `/api` suffix) | `http://localhost:8000` |
| `DEVGODZILLA_WINDMILL_TOKEN` | Windmill token (do not commit) | None |
| `DEVGODZILLA_WINDMILL_WORKSPACE` | Windmill workspace | `devgodzilla` |
| `DEVGODZILLA_WINDMILL_ENV_FILE` | Optional env file to source token/workspace/url | Auto-detected |

## Verify Installation

```bash
# Check CLI entrypoint
python -m devgodzilla.cli.main --help
```

## Running the API

```bash
# Development mode
python -m devgodzilla.api.app

# Or with uvicorn
uvicorn devgodzilla.api.app:app --reload --host 0.0.0.0 --port 8000
```

## Running Tests

```bash
# All DevGodzilla tests
pytest tests/test_devgodzilla_*.py -v

# Specific test file
pytest tests/test_devgodzilla_speckit.py -v

# With coverage
pytest tests/test_devgodzilla_*.py --cov=devgodzilla --cov-report=html
```

### E2E (real repo) tests

E2E tests are opt-in and clone a real public GitHub repo.

```bash
DEVGODZILLA_RUN_E2E=1 scripts/ci/test_e2e_real_repo.sh
```

To run the same tests against a real `opencode` installation (no stub), use:

```bash
DEVGODZILLA_RUN_E2E_REAL_AGENT=1 scripts/ci/test_e2e_real_agent.sh
```

## Windmill Integration

For full workflow orchestration, configure Windmill:

```bash
# Option A: set env vars explicitly
export DEVGODZILLA_WINDMILL_URL=http://localhost:8000
export DEVGODZILLA_WINDMILL_WORKSPACE=devgodzilla
export DEVGODZILLA_WINDMILL_TOKEN=your_token_here

# Option B (local dev): keep token in an env file and let DevGodzilla auto-load it
# (defaults to `windmill/apps/devgodzilla-react-app/.env.development` if present)
export DEVGODZILLA_WINDMILL_ENV_FILE=windmill/apps/devgodzilla-react-app/.env.development
```

## Next Steps

1. Initialize SpecKit: `python -m devgodzilla.cli.main spec init .`
2. Generate spec/plan/tasks: `python -m devgodzilla.cli.main spec specify "Your feature"`
3. Create protocol: `python -m devgodzilla.cli.main protocol create <project_id> <name>`

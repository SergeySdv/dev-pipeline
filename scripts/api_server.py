#!/usr/bin/env python3
"""
Run the DeksdenFlow orchestrator API (FastAPI + SQLite).

Install dependencies first:
  pip install fastapi uvicorn
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn  # noqa: E402


def main() -> None:
    host = os.environ.get("DEKSDENFLOW_API_HOST", "0.0.0.0")
    port = int(os.environ.get("DEKSDENFLOW_API_PORT", "8000"))
    uvicorn.run("deksdenflow.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()

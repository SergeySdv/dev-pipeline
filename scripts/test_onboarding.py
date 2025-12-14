#!/usr/bin/env python3
"""
Test script to run the full onboarding workflow for a project.
"""
import os
import sys
import shutil
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tasksgodzilla.storage import Database
from tasksgodzilla.services import OnboardingService
from tasksgodzilla.domain import ProtocolStatus
from tasksgodzilla.logging import init_cli_logging


def main():
    # Initialize logging
    init_cli_logging("INFO", json_output=False)
    
    # Set up environment for testing
    os.environ.setdefault("TASKSGODZILLA_AUTO_CLONE", "true")
    
    # Configure git identity
    os.environ.setdefault("GIT_AUTHOR_NAME", "TasksGodzilla")
    os.environ.setdefault("GIT_AUTHOR_EMAIL", "tasksgodzilla@example.com")
    os.environ.setdefault("GIT_COMMITTER_NAME", "TasksGodzilla")
    os.environ.setdefault("GIT_COMMITTER_EMAIL", "tasksgodzilla@example.com")
    
    # Set discovery timeout (opencode can be slow)
    os.environ.setdefault("TASKSGODZILLA_DISCOVERY_TIMEOUT", "300")
    
    # Create a test database
    db_path = Path("/tmp/tasksgodzilla-test.sqlite")
    if db_path.exists():
        db_path.unlink()
    
    db = Database(db_path)
    db.init_schema()
    
    # Create the project
    git_url = "https://github.com/ilyafedotov-ops/click"
    project = db.create_project(
        name="click",
        git_url=git_url,
        base_branch="main",
        ci_provider="github",
        default_models={"planning": "zai-coding-plan/glm-4.6"},
    )
    print(f"Created project: {project.id} - {project.name}")
    
    # Create a protocol run for setup
    run = db.create_protocol_run(
        project_id=project.id,
        protocol_name="setup-click",
        status=ProtocolStatus.PENDING,
        base_branch="main",
        worktree_path=None,
        protocol_root=None,
        description="setup",
    )
    print(f"Created protocol run: {run.id}")
    
    # Run the onboarding service
    service = OnboardingService(db=db)
    print("\n=== Starting Onboarding Workflow ===\n")
    
    try:
        service.run_project_setup_job(project.id, protocol_run_id=run.id)
        print("\n=== Onboarding Complete ===\n")
    except Exception as e:
        print(f"\n=== Onboarding Failed: {e} ===\n")
        import traceback
        traceback.print_exc()
    
    # Show the results
    run_after = db.get_protocol_run(run.id)
    print(f"Final status: {run_after.status}")
    
    # Show events
    events = db.list_events(run.id)
    print(f"\nEvents ({len(events)} total):")
    for event in events:
        print(f"  - {event.event_type}: {event.message}")
        if event.metadata:
            for k, v in event.metadata.items():
                if k not in ("path", "repo_root"):  # Skip verbose paths
                    print(f"      {k}: {v}")
    
    # Check if clarifications were generated
    clar_events = [e for e in events if e.event_type == "setup_clarifications"]
    if clar_events:
        print("\nClarification questions:")
        for clar in clar_events:
            if clar.metadata and "clarifications" in clar.metadata:
                for q in clar.metadata["clarifications"]:
                    print(f"  - {q}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

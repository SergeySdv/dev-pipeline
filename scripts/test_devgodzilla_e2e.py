#!/usr/bin/env python3
"""
End-to-end test for DevGodzilla.
Tests complete workflow: project creation → SpecKit → Planning → Orchestration
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_e2e_workflow():
    """Test the complete DevGodzilla workflow."""

    print("=" * 70)
    print("DevGodzilla End-to-End Test")
    print("=" * 70)

    test_repo_url = "https://github.com/ilyafedotov-ops/click"
    test_project_name = "click-e2e-test"

    test_dir = Path(tempfile.mkdtemp(prefix="devgodzilla_e2e_"))
    db_path = test_dir / "test_devgodzilla.sqlite"
    projects_dir = test_dir / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    os.chdir(test_dir)

    print(f"\nTest directory: {test_dir}")
    print(f"Database path: {db_path}")

    errors = []

    try:
        # Step 1: Initialize database and create context
        print("\n" + "=" * 50)
        print("[Step 1] Initialize database and services")
        print("=" * 50)

        from devgodzilla.db.database import SQLiteDatabase
        from devgodzilla.config import Config
        from devgodzilla.services.base import ServiceContext

        db = SQLiteDatabase(db_path)
        db.init_schema()
        print("  ✓ Database initialized")

        config = Config(db_path=db_path, environment="test")
        context = ServiceContext(config=config)
        print("  ✓ Service context created")

        # Step 2: Create project
        print("\n" + "=" * 50)
        print("[Step 2] Create project")
        print("=" * 50)

        project = db.create_project(
            name=test_project_name,
            git_url=test_repo_url,
            base_branch="main"
        )
        print(f"  ✓ Project created: ID={project.id}, Name={project.name}")

        # Step 3: Clone repository
        print("\n" + "=" * 50)
        print("[Step 3] Clone repository")
        print("=" * 50)

        from devgodzilla.services.git import GitService

        git_service = GitService(context)
        repo_path = git_service.resolve_repo_path(
            git_url=test_repo_url,
            project_name=test_project_name,
            local_path=None,
            project_id=project.id,
            clone_if_missing=True
        )

        db.update_project_local_path(project.id, str(repo_path))
        print(f"  ✓ Repository cloned: {repo_path}")

        # Step 4: Initialize SpecKit
        print("\n" + "=" * 50)
        print("[Step 4] Initialize SpecKit")
        print("=" * 50)

        from devgodzilla.services.specification import SpecificationService

        spec_service = SpecificationService(context, db)
        init_result = spec_service.init_project(str(repo_path), project_id=project.id)

        if init_result.success:
            print(f"  ✓ SpecKit initialized: {init_result.spec_path}")
        else:
            errors.append(f"SpecKit init failed: {init_result.error}")
            print(f"  ✗ {init_result.error}")

        # Step 5: Generate specification
        print("\n" + "=" * 50)
        print("[Step 5] Generate specification")
        print("=" * 50)

        spec_result = spec_service.run_specify(
            project_path=str(repo_path),
            description="Add a --dry-run flag to show what would be done without executing",
            feature_name="dry-run-flag",
            project_id=project.id
        )

        if spec_result.success:
            print(f"  ✓ Spec generated: #{spec_result.spec_number} {spec_result.feature_name}")
            print(f"    Path: {spec_result.spec_path}")
        else:
            errors.append(f"Spec generation failed: {spec_result.error}")
            print(f"  ✗ {spec_result.error}")

        # Step 6: Generate plan
        print("\n" + "=" * 50)
        print("[Step 6] Generate plan")
        print("=" * 50)

        plan_result = spec_service.run_plan(
            project_path=str(repo_path),
            spec_path=spec_result.spec_path,
            project_id=project.id
        )

        if plan_result.success:
            print(f"  ✓ Plan generated: {plan_result.plan_path}")
        else:
            errors.append(f"Plan generation failed: {plan_result.error}")
            print(f"  ✗ {plan_result.error}")

        # Step 7: Generate tasks
        print("\n" + "=" * 50)
        print("[Step 7] Generate tasks")
        print("=" * 50)

        tasks_result = spec_service.run_tasks(
            project_path=str(repo_path),
            plan_path=plan_result.plan_path,
            project_id=project.id
        )

        if tasks_result.success:
            print(f"  ✓ Tasks generated: {tasks_result.tasks_path}")
            print(f"    Total: {tasks_result.task_count}, Parallelizable: {tasks_result.parallelizable_count}")
        else:
            errors.append(f"Tasks generation failed: {tasks_result.error}")
            print(f"  ✗ {tasks_result.error}")

        # Step 8: Create protocol run
        print("\n" + "=" * 50)
        print("[Step 8] Create protocol run")
        print("=" * 50)

        from devgodzilla.services.orchestrator import OrchestratorService, OrchestratorMode
        from devgodzilla.services.planning import PlanningService

        # Create protocol root directory first
        protocol_name = "dry-run-feature"
        protocol_root = repo_path / ".protocols" / protocol_name
        protocol_root.mkdir(parents=True, exist_ok=True)

        planning_service = PlanningService(context, db, git_service=git_service)

        orchestrator = OrchestratorService(
            context, db,
            windmill_client=None,
            mode=OrchestratorMode.LOCAL,
            planning_service=planning_service,
            git_service=git_service,
        )

        protocol_run = orchestrator.create_protocol_run(
            project_id=project.id,
            protocol_name=protocol_name,
            base_branch="main",
            description="Implement dry-run flag feature",
            worktree_path=str(repo_path),
            protocol_root=str(protocol_root),
        )

        print(f"  ✓ Protocol run created: ID={protocol_run.id}, Name={protocol_run.protocol_name}")
        print(f"    Status: {protocol_run.status}")

        # Step 9: Test planning (local mode)
        print("\n" + "=" * 50)
        print("[Step 9] Test planning service")
        print("=" * 50)

        plan_md = protocol_root / "plan.md"
        plan_content = f"""# Protocol: {protocol_run.protocol_name}

## Description
{protocol_run.description}

## Steps

### Step 1: Add argument parser option
- Add --dry-run flag to argument parser
- Type: code_gen
- Agent: opencode

### Step 2: Implement dry-run logic
- Add conditional execution based on flag
- Type: code_gen
- Agent: opencode
- Depends: Step 1

### Step 3: Write tests
- Add unit tests for dry-run functionality
- Type: code_gen
- Agent: opencode
- Depends: Step 2
"""
        plan_md.write_text(plan_content)
        print(f"  ✓ Protocol plan created: {plan_md}")

        # Step 10: Start protocol
        print("\n" + "=" * 50)
        print("[Step 10] Start protocol run")
        print("=" * 50)

        start_result = orchestrator.start_protocol_run(protocol_run.id)

        if start_result.success:
            print(f"  ✓ Protocol started")
        else:
            if start_result.error:
                errors.append(f"Protocol start failed: {start_result.error}")
                print(f"  ⚠ {start_result.error}")
            else:
                print(f"  ✓ Protocol started (no planning service)")

        # Check protocol status
        updated_run = db.get_protocol_run(protocol_run.id)
        print(f"    Final status: {updated_run.status}")

        # Step 11: List specs and verify
        print("\n" + "=" * 50)
        print("[Step 11] Verify artifacts")
        print("=" * 50)

        specs = spec_service.list_specs(str(repo_path))
        print(f"  Specs found: {len(specs)}")
        for spec in specs:
            print(f"    - {spec['name']}: spec={spec['has_spec']}, plan={spec['has_plan']}, tasks={spec['has_tasks']}")

        projects = db.list_projects()
        print(f"\n  Projects in database: {len(projects)}")

        protocol_runs = db.list_protocol_runs(project.id)
        print(f"  Protocol runs for project: {len(protocol_runs)}")

        # Summary
        print("\n" + "=" * 70)
        if errors:
            print(f"TEST COMPLETED WITH {len(errors)} ERRORS:")
            for i, err in enumerate(errors, 1):
                print(f"  {i}. {err}")
            print("=" * 70)
            return False
        else:
            print("ALL TESTS PASSED!")
            print("=" * 70)
            return True

    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print(f"\n[Cleanup] Test directory preserved at: {test_dir}")


if __name__ == "__main__":
    success = test_e2e_workflow()
    sys.exit(0 if success else 1)

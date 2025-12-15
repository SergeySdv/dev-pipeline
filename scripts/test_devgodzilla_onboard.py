#!/usr/bin/env python3
"""
Test script for DevGodzilla onboarding and SpecKit integration.
Tests with real repository: https://github.com/ilyafedotov-ops/click
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_devgodzilla_onboard():
    """Test the DevGodzilla onboarding flow with a real repository."""

    print("=" * 60)
    print("DevGodzilla Onboarding Test")
    print("=" * 60)

    # Test repo URL
    test_repo_url = "https://github.com/ilyafedotov-ops/click"
    test_project_name = "click-test"

    # Use a temporary directory for testing
    test_dir = Path(tempfile.mkdtemp(prefix="devgodzilla_test_"))
    db_path = test_dir / "test_devgodzilla.sqlite"
    projects_dir = test_dir / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nTest directory: {test_dir}")
    print(f"Database path: {db_path}")

    try:
        # Step 1: Initialize database
        print("\n[1/6] Initializing database...")
        from devgodzilla.db.database import SQLiteDatabase

        db = SQLiteDatabase(db_path)
        db.init_schema()
        print("  ✓ Database initialized")

        # Step 2: Create service context
        print("\n[2/6] Creating service context...")
        from devgodzilla.config import Config
        from devgodzilla.services.base import ServiceContext

        config = Config(
            db_path=db_path,
            environment="test"
        )
        context = ServiceContext(config=config)
        print("  ✓ Service context created")

        # Step 3: Create project
        print("\n[3/6] Creating project...")
        project = db.create_project(
            name=test_project_name,
            git_url=test_repo_url,
            base_branch="main"
        )
        print(f"  ✓ Project created: ID={project.id}, Name={project.name}")

        # Step 4: Clone repository using GitService
        print("\n[4/6] Cloning repository...")
        from devgodzilla.services.git import GitService

        git_service = GitService(context)
        repo_path = git_service.resolve_repo_path(
            git_url=test_repo_url,
            project_name=test_project_name,
            local_path=None,
            project_id=project.id,
            clone_if_missing=True
        )

        # Update project with local path
        db.update_project_local_path(project.id, str(repo_path))
        print(f"  ✓ Repository cloned to: {repo_path}")

        # Step 5: Initialize SpecKit
        print("\n[5/6] Initializing SpecKit...")
        from devgodzilla.services.specification import SpecificationService

        spec_service = SpecificationService(context, db)
        init_result = spec_service.init_project(
            project_path=str(repo_path),
            project_id=project.id
        )

        if init_result.success:
            print(f"  ✓ SpecKit initialized")
            print(f"    - Spec path: {init_result.spec_path}")
            print(f"    - Constitution hash: {init_result.constitution_hash}")
            if init_result.artifacts:
                for name, path in init_result.artifacts.items():
                    print(f"    - {name}: {path}")
        else:
            print(f"  ✗ SpecKit initialization failed: {init_result.error}")
            return False

        # Step 6: Test spec generation
        print("\n[6/6] Testing spec generation...")
        spec_result = spec_service.run_specify(
            project_path=str(repo_path),
            description="Add a new command-line option --verbose to enable detailed logging output",
            feature_name="verbose-logging",
            project_id=project.id
        )

        if spec_result.success:
            print(f"  ✓ Spec generated")
            print(f"    - Spec path: {spec_result.spec_path}")
            print(f"    - Spec number: {spec_result.spec_number}")
            print(f"    - Feature name: {spec_result.feature_name}")

            # Read and display the generated spec
            if spec_result.spec_path and Path(spec_result.spec_path).exists():
                content = Path(spec_result.spec_path).read_text()
                print(f"\n  Generated spec preview (first 500 chars):")
                print("  " + "-" * 40)
                for line in content[:500].split('\n'):
                    print(f"  | {line}")
                print("  " + "-" * 40)
        else:
            print(f"  ✗ Spec generation failed: {spec_result.error}")
            return False

        # Test plan generation
        print("\n[Bonus] Testing plan generation...")
        plan_result = spec_service.run_plan(
            project_path=str(repo_path),
            spec_path=spec_result.spec_path,
            project_id=project.id
        )

        if plan_result.success:
            print(f"  ✓ Plan generated: {plan_result.plan_path}")
        else:
            print(f"  ✗ Plan generation failed: {plan_result.error}")

        # Test tasks generation
        print("\n[Bonus] Testing tasks generation...")
        tasks_result = spec_service.run_tasks(
            project_path=str(repo_path),
            plan_path=plan_result.plan_path,
            project_id=project.id
        )

        if tasks_result.success:
            print(f"  ✓ Tasks generated: {tasks_result.tasks_path}")
            print(f"    - Task count: {tasks_result.task_count}")
            print(f"    - Parallelizable: {tasks_result.parallelizable_count}")
        else:
            print(f"  ✗ Tasks generation failed: {tasks_result.error}")

        # List all specs
        print("\n[Summary] Listing all specs...")
        specs = spec_service.list_specs(str(repo_path))
        for spec in specs:
            print(f"  - {spec['name']}: spec={spec['has_spec']}, plan={spec['has_plan']}, tasks={spec['has_tasks']}")

        # Test constitution
        print("\n[Summary] Constitution content:")
        constitution = spec_service.get_constitution(str(repo_path))
        if constitution:
            print("  " + "-" * 40)
            for line in constitution[:300].split('\n'):
                print(f"  | {line}")
            print("  " + "-" * 40)

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        print(f"\n[Cleanup] Test directory: {test_dir}")
        print("  Note: Directory preserved for inspection. Remove manually if needed.")


if __name__ == "__main__":
    success = test_devgodzilla_onboard()
    sys.exit(0 if success else 1)

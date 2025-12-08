# Services Migration Guide for Contributors

## Overview

TasksGodzilla is migrating to a **service-oriented architecture** to improve testability, maintainability, and clear separation of concerns. This guide helps contributors understand how to use the new services layer instead of reaching directly into workers or low-level helpers.

## Key Principle

**Use services, not workers.**

When adding new features or modifying existing code, prefer calling service methods over directly invoking worker functions or database operations.

## Services Directory Structure

```
tasksgodzilla/services/
├── __init__.py                    # Exports all services
├── orchestrator.py                # OrchestratorService
├── execution.py                   # ExecutionService
├── quality.py                     # QualityService
├── onboarding.py                  # OnboardingService
├── spec.py                        # SpecService
├── decomposition.py               # DecompositionService
├── prompts.py                     # PromptService
└── platform/
    ├── queue.py                   # QueueService
    ├── telemetry.py               # TelemetryService
    └── storage.py                 # (future) Repository layer
```

## Migration Patterns

### ❌ Old Pattern: Direct Worker Calls

```python
# Don't do this
from tasksgodzilla.workers.codex_worker import handle_execute_step

def my_endpoint(step_run_id: int, db: BaseDatabase):
    handle_execute_step(step_run_id, db)
```

### ✅ New Pattern: Service Layer

```python
# Do this instead
from tasksgodzilla.services import ExecutionService

def my_endpoint(step_run_id: int, db: BaseDatabase):
    executor = ExecutionService(db=db)
    executor.execute_step(step_run_id)
```

### ❌ Old Pattern: Direct Database Operations

```python
# Don't do this
def create_and_start_protocol(project_id: int, name: str, db: BaseDatabase, queue: BaseQueue):
    run = db.create_protocol_run(project_id, name, ProtocolStatus.PENDING, "main", None, None, None)
    db.update_protocol_status(run.id, ProtocolStatus.PLANNING)
    queue.enqueue("plan_protocol_job", {"protocol_run_id": run.id})
```

### ✅ New Pattern: Orchestrator Service

```python
# Do this instead
from tasksgodzilla.services import OrchestratorService

def create_and_start_protocol(project_id: int, name: str, db: BaseDatabase, queue: BaseQueue):
    orchestrator = OrchestratorService(db=db)
    run = orchestrator.create_protocol_run(project_id, name, ProtocolStatus.PENDING, "main")
    orchestrator.start_protocol_run(run.id, queue)
```

## Service Usage Examples

### Protocol Lifecycle

```python
from tasksgodzilla.services import OrchestratorService

orchestrator = OrchestratorService(db=db)

# Create protocol
run = orchestrator.create_protocol_run(
    project_id=1,
    protocol_name="feature-auth",
    status=ProtocolStatus.PENDING,
    base_branch="main"
)

# Start planning
job = orchestrator.start_protocol_run(run.id, queue)

# Enqueue next step
step, job = orchestrator.enqueue_next_step(run.id, queue)

# Pause/resume/cancel
orchestrator.pause_protocol(run.id)
orchestrator.resume_protocol(run.id)
orchestrator.cancel_protocol(run.id)
```

### Spec Management

```python
from tasksgodzilla.services import SpecService

spec_service = SpecService(db=db)

# Build spec from protocol files
spec = spec_service.build_from_protocol_files(run.id, protocol_root)

# Validate and update meta
errors = spec_service.validate_and_update_meta(run.id, protocol_root)

# Create step runs from spec
created_count = spec_service.ensure_step_runs(run.id)

# Get individual step spec
step_spec = spec_service.get_step_spec(run.id, "step-1")
```

### Quality Assurance

```python
from tasksgodzilla.services import QualityService

qa_service = QualityService(db=db)

# Run QA for a step run (orchestrated)
qa_service.run_for_step_run(step_run_id, job_id="job-123")

# Direct evaluation
result = qa_service.evaluate_step(
    protocol_root=protocol_root,
    step_filename="01-setup.md",
    sandbox="read-only"
)
```

### Project Onboarding

```python
from tasksgodzilla.services import OnboardingService

onboarding = OnboardingService(db=db)

# Register project
project = onboarding.register_project(
    name="my-app",
    git_url="https://github.com/org/repo",
    base_branch="main",
    ci_provider="github"
)

# Ensure workspace
onboarding.ensure_workspace(
    project_id=project.id,
    clone_if_missing=True,
    run_discovery_pass=True
)
```

### Queue Operations

```python
from tasksgodzilla.services.platform import QueueService

queue_service = QueueService(queue=redis_queue)

# Enqueue jobs
job = queue_service.enqueue_plan_protocol(protocol_run_id=1)
job = queue_service.enqueue_execute_step(step_run_id=5)
job = queue_service.enqueue_run_quality(step_run_id=5)
job = queue_service.enqueue_project_setup(project_id=1)
job = queue_service.enqueue_open_pr(protocol_run_id=1)
```

## API Integration

When adding new API endpoints, use dependency injection to get services:

```python
from fastapi import Depends
from tasksgodzilla.services import OrchestratorService, OnboardingService

def get_orchestrator(db: BaseDatabase = Depends(get_db)) -> OrchestratorService:
    return OrchestratorService(db=db)

def get_onboarding_service(db: BaseDatabase = Depends(get_db)) -> OnboardingService:
    return OnboardingService(db=db)

@app.post("/protocols/{id}/actions/start")
def start_protocol(
    id: int,
    orchestrator: OrchestratorService = Depends(get_orchestrator),
    queue: BaseQueue = Depends(get_queue)
):
    job = orchestrator.start_protocol_run(id, queue)
    return {"job_id": job.job_id}
```

## Worker Integration

Workers should delegate to services:

```python
def process_job(job: Job, db: BaseDatabase) -> None:
    if job.job_type == "execute_step_job":
        executor = ExecutionService(db=db)
        executor.execute_step(job.payload["step_run_id"], job_id=job.job_id)
    
    elif job.job_type == "run_quality_job":
        qa_service = QualityService(db=db)
        qa_service.run_for_step_run(job.payload["step_run_id"], job_id=job.job_id)
    
    # ... etc
```

## Testing

When writing tests, use services for cleaner, more maintainable tests:

```python
def test_protocol_lifecycle(tmp_path):
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    # Use services instead of raw DB calls
    orchestrator = OrchestratorService(db=db)
    
    project = db.create_project("test", "https://github.com/test/repo", "main", "github", {})
    run = orchestrator.create_protocol_run(project.id, "test-protocol", ProtocolStatus.PENDING, "main")
    
    mock_queue = Mock()
    job = orchestrator.start_protocol_run(run.id, queue=mock_queue)
    
    assert job is not None
    mock_queue.enqueue.assert_called_once()
```

## Benefits of Using Services

1. **Testability**: Services can be tested in isolation with mocks
2. **Maintainability**: Clear boundaries make refactoring safer
3. **Consistency**: Single source of truth for business logic
4. **Evolution**: Services can evolve without breaking callers
5. **Documentation**: Service methods are self-documenting contracts

## What About Legacy Code?

Legacy worker functions (`tasksgodzilla/workers/codex_worker.py`, etc.) are still used internally by services. They will be gradually refactored as services mature. For now:

- **New code**: Always use services
- **Existing code**: Migrate opportunistically when touching related areas
- **Workers**: Keep as thin adapters that delegate to services

## Questions?

See:
- `docs/services-architecture.md` - Detailed architecture and design
- `docs/services-status.md` - Implementation status and roadmap
- `tests/test_*service*.py` - Service usage examples

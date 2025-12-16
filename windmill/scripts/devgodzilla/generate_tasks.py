"""
Generate Tasks Script

Generates a task breakdown with dependencies from an implementation plan.

Args:
    project_path: Path to the project directory
    plan_path: Path to the implementation plan (relative to project)

Returns:
    tasks_path: Path to generated tasks file
    tasks: List of parsed tasks
    dag: Dependency graph for execution
"""

import re
from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Any

# Import DevGodzilla services if available
try:
    from devgodzilla.services import PlanningService
    from devgodzilla.windmill.flow_generator import DAGBuilder, DAG
    from devgodzilla.db import get_database
    DEVGODZILLA_AVAILABLE = True
except ImportError:
    DEVGODZILLA_AVAILABLE = False


def parse_task_line(line: str) -> Dict[str, Any] | None:
    """Parse a task line like '- [ ] T001: Description [DEPENDS: T000] [PARALLEL]'."""
    
    # Match task pattern
    pattern = r'^-\s*\[([ x/])\]\s*(T\d+):\s*(.+?)(?:\s*\[DEPENDS:\s*([^\]]+)\])?(?:\s*\[PARALLEL\])?\s*$'
    match = re.match(pattern, line.strip())
    
    if not match:
        return None
    
    status_char, task_id, description, depends = match.groups()
    
    status = "pending"
    if status_char == "x":
        status = "completed"
    elif status_char == "/":
        status = "in_progress"
    
    depends_on = []
    if depends:
        depends_on = [d.strip() for d in depends.split(',')]
    
    parallel = "[PARALLEL]" in line
    
    return {
        "id": task_id,
        "description": description.strip(),
        "status": status,
        "depends_on": depends_on,
        "parallel": parallel,
    }


def main(
    project_path: str,
    plan_path: str,
) -> dict:
    """Generate task breakdown from implementation plan."""
    
    path = Path(project_path)
    
    # Resolve plan path
    if not plan_path.startswith('/'):
        full_plan_path = path / plan_path
    else:
        full_plan_path = Path(plan_path)
    
    if not full_plan_path.exists():
        return {"error": f"Plan not found: {plan_path}"}
    
    # Read plan
    plan_content = full_plan_path.read_text()
    
    # Determine output directory (same as plan)
    plan_dir = full_plan_path.parent
    tasks_path = plan_dir / "tasks.md"
    
    # Generate tasks using DevGodzilla if available
    if DEVGODZILLA_AVAILABLE:
        try:
            db = get_database()
            planning_service = PlanningService(db)
            result = planning_service.generate_tasks(
                plan=plan_content,
                project_path=str(path),
            )
            tasks_content = result.content if hasattr(result, 'content') else str(result)
        except Exception as e:
            tasks_content = _generate_fallback_tasks(plan_content)
    else:
        tasks_content = _generate_fallback_tasks(plan_content)
    
    # Write tasks
    tasks_path.write_text(tasks_content)
    
    # Parse tasks for DAG
    tasks = []
    current_phase = ""
    
    for line in tasks_content.split('\n'):
        if line.startswith('## Phase'):
            current_phase = line[3:].strip()
        elif line.strip().startswith('- ['):
            task = parse_task_line(line)
            if task:
                task['phase'] = current_phase
                tasks.append(task)
    
    # Build DAG
    dag = build_dag(tasks)
    
    # Update context
    runtime_dir = plan_dir / "_runtime"
    context_path = runtime_dir / "context.json"
    if context_path.exists():
        context = json.loads(context_path.read_text())
    else:
        context = {}
    
    context["tasks_generated_at"] = datetime.now().isoformat()
    context["task_count"] = len(tasks)
    
    runtime_dir.mkdir(exist_ok=True)
    context_path.write_text(json.dumps(context, indent=2))
    
    # Save DAG for later use
    dag_path = runtime_dir / "dag.json"
    dag_path.write_text(json.dumps(dag, indent=2))
    
    return {
        "tasks_path": str(tasks_path),
        "tasks": tasks,
        "dag": dag,
        "task_count": len(tasks),
    }


def build_dag(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build DAG structure from tasks."""
    
    nodes = {}
    edges = []
    
    for task in tasks:
        nodes[task["id"]] = {
            "id": task["id"],
            "description": task["description"],
            "status": task["status"],
            "parallel": task.get("parallel", True),
            "phase": task.get("phase", ""),
        }
        
        for dep in task.get("depends_on", []):
            if dep and dep != "none":
                edges.append([dep, task["id"]])
    
    # Compute levels for parallel execution
    levels = []
    remaining = set(nodes.keys())
    completed = set()
    
    while remaining:
        # Find tasks with all dependencies satisfied
        ready = [
            task_id for task_id in remaining
            if all(d in completed for d in _get_deps(task_id, tasks))
        ]
        
        if not ready:
            # Handle cycles or orphans
            ready = list(remaining)[:1]
        
        levels.append(ready)
        completed.update(ready)
        remaining -= set(ready)
    
    return {
        "nodes": nodes,
        "edges": edges,
        "levels": levels,
    }


def _get_deps(task_id: str, tasks: List[Dict[str, Any]]) -> List[str]:
    """Get dependencies for a task."""
    for task in tasks:
        if task["id"] == task_id:
            deps = task.get("depends_on", [])
            return [d for d in deps if d and d != "none"]
    return []


def _generate_fallback_tasks(plan_content: str) -> str:
    """Generate a basic task breakdown without AI."""
    
    # Extract title from plan
    lines = plan_content.split('\n')
    title = "Feature"
    for line in lines:
        if line.startswith('# '):
            title = line[2:].replace("Implementation Plan:", "").strip()
            break
    
    return f"""# Task Breakdown: {title}

## Phase 1: Setup
- [ ] T001: Review existing codebase and identify integration points [DEPENDS: none]
- [ ] T002: Set up development environment and dependencies [DEPENDS: T001]

## Phase 2: Core Implementation
- [ ] T003: Implement core feature logic [DEPENDS: T002]
- [ ] T004: Implement supporting utilities [DEPENDS: T002] [PARALLEL]
- [ ] T005: Integrate with existing components [DEPENDS: T003, T004]

## Phase 3: Testing
- [ ] T006: Write unit tests for core logic [DEPENDS: T003] [PARALLEL]
- [ ] T007: Write integration tests [DEPENDS: T005] [PARALLEL]
- [ ] T008: Run full test suite and fix issues [DEPENDS: T006, T007]

## Phase 4: Documentation & Cleanup
- [ ] T009: Update documentation [DEPENDS: T008]
- [ ] T010: Code review and cleanup [DEPENDS: T008] [PARALLEL]
- [ ] T011: Final verification [DEPENDS: T009, T010]

---

## Task Legend
- `[DEPENDS: Txxx]` - Task depends on specified task(s)
- `[PARALLEL]` - Task can run in parallel with siblings
- `[ ]` - Pending
- `[/]` - In Progress  
- `[x]` - Completed

---
*Generated by DevGodzilla SpecKit*
"""

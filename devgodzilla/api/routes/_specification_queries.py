from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException

from devgodzilla.db.database import Database


def spec_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def spec_key(item: Any, resolved_spec_id: int) -> str:
    spec_run_id = spec_value(item, "spec_run_id", None) or spec_value(item, "id", None)
    if spec_run_id is not None:
        return f"run:{spec_run_id}"
    spec_path_value = str(spec_value(item, "path", "") or "")
    spec_slug = Path(spec_path_value).name if spec_path_value else str(resolved_spec_id)
    return f"slug:{spec_slug}"


def build_filters_applied(
    *,
    project_id: Optional[int],
    sprint_id: Optional[int],
    status: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    has_plan: Optional[bool],
    has_tasks: Optional[bool],
    search: Optional[str],
) -> dict[str, Any]:
    filters = {
        "project_id": project_id,
        "sprint_id": sprint_id,
        "status": status,
        "date_from": date_from,
        "date_to": date_to,
        "has_plan": has_plan,
        "has_tasks": has_tasks,
        "search": search,
    }
    return {key: value for key, value in filters.items() if value is not None and value != ""}


@dataclass
class ProjectSpecificationContext:
    project: Any
    tasks_by_slug: dict[str, list[Any]]
    sprints: dict[int, Any]
    spec_links: dict[str, int]


def list_specification_items(
    *,
    db: Database,
    service: Any,
    project_id: Optional[int],
    sprint_id: Optional[int],
    status: Optional[str],
    date_from: Optional[str],
    date_to: Optional[str],
    has_plan: Optional[bool],
    has_tasks: Optional[bool],
    search: Optional[str],
) -> list[dict[str, Any]]:
    projects, sprint_project_filter = resolve_projects(db, project_id=project_id, sprint_id=sprint_id)
    from_date = parse_filter_date(date_from)
    to_date = parse_filter_date(date_to)
    all_specifications: list[dict[str, Any]] = []
    spec_id = 0

    for project in projects:
        if not project or not project.local_path:
            continue
        if sprint_project_filter is not None and project.id != sprint_project_filter:
            continue

        try:
            specs = service.list_specs(project.local_path, project_id=project.id)
            context = load_project_specification_context(db, project)
        except Exception:
            continue

        for spec in specs:
            spec_id += 1
            payload = build_specification_payload(
                project=project,
                spec=spec,
                context=context,
                fallback_spec_id=spec_id,
                sprint_id=sprint_id,
                status=status,
                from_date=from_date,
                to_date=to_date,
                has_plan=has_plan,
                has_tasks=has_tasks,
                search=search,
            )
            if payload is not None:
                all_specifications.append(payload)

    return all_specifications


def resolve_projects(
    db: Database,
    *,
    project_id: Optional[int],
    sprint_id: Optional[int],
) -> tuple[list[Any], Optional[int]]:
    if project_id is not None:
        try:
            project = db.get_project(project_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found") from exc
        projects = [project] if project else []
    else:
        projects = db.list_projects()[:100]

    sprint_project_filter = None
    if sprint_id is not None:
        try:
            sprint = db.get_sprint(sprint_id)
        except Exception as exc:
            raise HTTPException(status_code=404, detail=f"Sprint {sprint_id} not found") from exc
        sprint_project_filter = sprint.project_id

    return projects, sprint_project_filter


def load_project_specification_context(db: Database, project: Any) -> ProjectSpecificationContext:
    project_tasks = db.list_tasks(project_id=project.id, limit=500)
    project_sprints = {sprint.id: sprint for sprint in db.list_sprints(project_id=project.id)}
    try:
        project_spec_links = db.list_spec_sprint_links(project.id)
    except Exception:
        project_spec_links = {}
    return ProjectSpecificationContext(
        project=project,
        tasks_by_slug=build_spec_task_map(project_tasks),
        sprints=project_sprints,
        spec_links=project_spec_links,
    )


def build_spec_task_map(tasks: list[Any]) -> dict[str, list[Any]]:
    spec_task_map: dict[str, list[Any]] = {}
    for task in tasks:
        spec_label = next((label for label in task.labels if label.startswith("spec:")), None)
        if not spec_label:
            continue
        spec_slug = spec_label.split(":", 1)[1]
        spec_task_map.setdefault(spec_slug, []).append(task)
    return spec_task_map


def build_specification_payload(
    *,
    project: Any,
    spec: Any,
    context: ProjectSpecificationContext,
    fallback_spec_id: int,
    sprint_id: Optional[int],
    status: Optional[str],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    has_plan: Optional[bool],
    has_tasks: Optional[bool],
    search: Optional[str],
) -> Optional[dict[str, Any]]:
    resolved_spec_id = spec_value(spec, "spec_run_id", None) or spec_value(spec, "id", None) or fallback_spec_id
    spec_status, has_plan_value, has_tasks_value = resolve_spec_status(spec)
    if status and spec_status != status:
        return None
    if has_plan is not None and has_plan_value != has_plan:
        return None
    if has_tasks is not None and has_tasks_value != has_tasks:
        return None

    title = spec_title(spec)
    spec_path_value = str(spec_value(spec, "path", ""))
    if not matches_search(search, title, spec_path_value):
        return None

    spec_created_at = specification_created_at(project.local_path, spec)
    if not matches_date_filters(spec_created_at, from_date=from_date, to_date=to_date):
        return None

    spec_slug = Path(spec_path_value).name
    spec_tasks = context.tasks_by_slug.get(spec_slug, [])
    linked_tasks = len(spec_tasks)
    completed_tasks = sum(1 for task in spec_tasks if task.board_status == "done")
    story_points = sum(task.story_points or 0 for task in spec_tasks)
    spec_ref_key = spec_key(spec, resolved_spec_id)
    sprint_info = resolve_spec_sprint_info(
        spec_tasks=spec_tasks,
        sprint_id=sprint_id,
        spec_ref_key=spec_ref_key,
        project_sprints=context.sprints,
        project_spec_links=context.spec_links,
    )
    if sprint_info is None:
        return None

    return {
        "id": resolved_spec_id,
        "spec_run_id": spec_value(spec, "spec_run_id", None) or spec_value(spec, "id", None),
        "path": spec_path_value,
        "spec_path": spec_value(spec, "spec_path"),
        "plan_path": spec_value(spec, "plan_path"),
        "tasks_path": spec_value(spec, "tasks_path"),
        "checklist_path": spec_value(spec, "checklist_path"),
        "analysis_path": spec_value(spec, "analysis_path"),
        "implement_path": spec_value(spec, "implement_path"),
        "title": title,
        "project_id": project.id,
        "project_name": project.name,
        "status": spec_status,
        "created_at": spec_created_at,
        "worktree_path": spec_value(spec, "worktree_path"),
        "branch_name": spec_value(spec, "branch_name"),
        "base_branch": spec_value(spec, "base_branch"),
        "feature_name": spec_value(spec, "feature_name"),
        "spec_number": spec_value(spec, "spec_number"),
        "tasks_generated": has_tasks_value,
        "linked_tasks": linked_tasks,
        "completed_tasks": completed_tasks,
        "story_points": story_points,
        "has_plan": has_plan_value,
        "has_tasks": has_tasks_value,
        "sprint_id": sprint_info["sprint_id"],
        "sprint_name": sprint_info["sprint_name"],
    }


def resolve_spec_status(spec: Any) -> tuple[str, bool, bool]:
    has_tasks_value = bool(spec_value(spec, "has_tasks", False))
    has_plan_value = bool(spec_value(spec, "has_plan", False))
    has_spec_value = bool(spec_value(spec, "has_spec", False))
    status_override = spec_value(spec, "status", None)
    if status_override in ("cleaned", "failed"):
        return status_override, has_plan_value, has_tasks_value
    if has_tasks_value:
        return "completed", has_plan_value, has_tasks_value
    if has_plan_value:
        return "in-progress", has_plan_value, has_tasks_value
    if has_spec_value:
        return "draft", has_plan_value, has_tasks_value
    return "", has_plan_value, has_tasks_value


def spec_title(spec: Any) -> str:
    title = spec_value(spec, "name", "spec").replace("-", " ").replace("_", " ").title()
    if title.startswith("Feature "):
        return title[8:]
    return title


def matches_search(search: Optional[str], title: str, spec_path_value: str) -> bool:
    if not search:
        return True
    search_lower = search.lower()
    return search_lower in title.lower() or search_lower in spec_path_value.lower()


def specification_created_at(project_local_path: str, spec: Any) -> Optional[str]:
    try:
        spec_dir = Path(spec_value(spec, "path", ""))
        if not spec_dir.is_absolute():
            spec_dir = Path(project_local_path) / spec_dir
        spec_file = spec_dir / "spec.md"
        if not spec_file.exists():
            return None
        stat = spec_file.stat()
        return datetime.fromtimestamp(stat.st_mtime).isoformat()
    except Exception:
        return None


def parse_filter_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def matches_date_filters(
    spec_created_at: Optional[str],
    *,
    from_date: Optional[datetime],
    to_date: Optional[datetime],
) -> bool:
    if spec_created_at is None:
        return True
    try:
        spec_date = datetime.fromisoformat(spec_created_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if from_date is not None and spec_date < from_date:
        return False
    if to_date is not None and spec_date > to_date:
        return False
    return True


def resolve_spec_sprint_info(
    *,
    spec_tasks: list[Any],
    sprint_id: Optional[int],
    spec_ref_key: str,
    project_sprints: dict[int, Any],
    project_spec_links: dict[str, int],
) -> Optional[dict[str, Any]]:
    spec_sprint_ids = {task.sprint_id for task in spec_tasks if task.sprint_id}
    linked_sprint_id = project_spec_links.get(spec_ref_key)
    if linked_sprint_id is not None:
        spec_sprint_ids.add(linked_sprint_id)

    resolved_sprint_id = None
    resolved_sprint_name = None
    if linked_sprint_id is not None:
        resolved_sprint_id = linked_sprint_id
        sprint = project_sprints.get(resolved_sprint_id)
        resolved_sprint_name = sprint.name if sprint else None
    elif len(spec_sprint_ids) == 1:
        resolved_sprint_id = next(iter(spec_sprint_ids))
        sprint = project_sprints.get(resolved_sprint_id)
        resolved_sprint_name = sprint.name if sprint else None
    elif len(spec_sprint_ids) > 1:
        resolved_sprint_name = "Multiple"

    if sprint_id is None:
        return {"sprint_id": resolved_sprint_id, "sprint_name": resolved_sprint_name}
    if sprint_id not in spec_sprint_ids:
        return None
    sprint = project_sprints.get(sprint_id)
    return {
        "sprint_id": sprint_id,
        "sprint_name": sprint.name if sprint else resolved_sprint_name,
    }


def specification_content_payload(project_local_path: str, spec_path: str) -> dict[str, Optional[str]]:
    spec_dir = Path(spec_path)
    if not spec_dir.is_absolute():
        spec_dir = Path(project_local_path) / spec_path
    return {
        "spec_content": read_optional_text(spec_dir / "spec.md"),
        "plan_content": read_optional_text(spec_dir / "plan.md"),
        "tasks_content": read_optional_text(spec_dir / "tasks.md"),
        "checklist_content": read_optional_text(spec_dir / "checklist.md"),
        "analysis_content": read_optional_text(spec_dir / "analysis.md"),
    }


def read_optional_text(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None

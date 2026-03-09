from __future__ import annotations

from typing import Iterable, List, TypeVar

from devgodzilla.db.database import Database

RunT = TypeVar("RunT")


def enrich_run_with_agile_context(db: Database, run: RunT) -> RunT:
    step_run_id = getattr(run, "step_run_id", None)
    protocol_run_id = getattr(run, "protocol_run_id", None)
    task = None

    if step_run_id is not None:
        tasks = db.list_tasks(step_run_id=step_run_id, limit=1)
        if tasks:
            task = tasks[0]

    if task is None and protocol_run_id is not None:
        tasks = db.list_tasks(protocol_run_id=protocol_run_id, limit=1)
        if tasks:
            task = tasks[0]

    if task is None:
        return run

    run.task_id = task.id
    run.task_title = task.title
    run.task_board_status = task.board_status
    run.sprint_id = task.sprint_id

    if task.sprint_id is not None:
        try:
            sprint = db.get_sprint(task.sprint_id)
        except KeyError:
            sprint = None
        if sprint is not None:
            run.sprint_name = sprint.name
            run.sprint_status = sprint.status

    return run


def enrich_runs_with_agile_context(db: Database, runs: Iterable[RunT]) -> List[RunT]:
    return [enrich_run_with_agile_context(db, run) for run in runs]

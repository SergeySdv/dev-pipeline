from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from devgodzilla.api.dependencies import get_windmill_client
from devgodzilla.windmill.client import WindmillClient

router = APIRouter(tags=["Windmill"])


@router.get("/flows")
def list_flows(
    prefix: Optional[str] = Query(None, description="Optional flow path prefix"),
    windmill: WindmillClient = Depends(get_windmill_client),
) -> List[Dict[str, Any]]:
    flows = windmill.list_flows(prefix=prefix)
    return [{"path": f.path, "name": f.name, "summary": f.summary} for f in flows]


@router.get("/flows/{flow_path:path}/runs")
def list_flow_runs(
    flow_path: str,
    per_page: int = 50,
    page: int = 1,
    windmill: WindmillClient = Depends(get_windmill_client),
) -> List[Dict[str, Any]]:
    try:
        return windmill.list_flow_runs(flow_path, per_page=per_page, page=page)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Windmill error: {e}")


@router.get("/flows/{flow_path:path}")
def get_flow(
    flow_path: str,
    windmill: WindmillClient = Depends(get_windmill_client),
) -> Dict[str, Any]:
    try:
        flow = windmill.get_flow(flow_path)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Windmill error: {e}")
    return {"path": flow.path, "name": flow.name, "summary": flow.summary, "schema": flow.schema}


@router.get("/jobs")
def list_jobs(
    per_page: int = 50,
    page: int = 1,
    job_kinds: Optional[str] = Query(None, description="Comma-separated: preview,script,dependencies,flow"),
    script_path_exact: Optional[str] = Query(None, description="Exact runnable path filter (script/flow)"),
    windmill: WindmillClient = Depends(get_windmill_client),
) -> List[Dict[str, Any]]:
    try:
        return windmill.list_jobs(
            per_page=per_page,
            page=page,
            job_kinds=job_kinds,
            script_path_exact=script_path_exact,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Windmill error: {e}")


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    windmill: WindmillClient = Depends(get_windmill_client),
) -> Dict[str, Any]:
    try:
        job = windmill.get_job(job_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Windmill error: {e}")
    return {
        "id": job.id,
        "status": job.status.value,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "result": job.result,
        "error": job.error,
    }


@router.get("/jobs/{job_id}/logs")
def get_job_logs(
    job_id: str,
    windmill: WindmillClient = Depends(get_windmill_client),
) -> Dict[str, Any]:
    try:
        logs = windmill.get_job_logs(job_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Windmill error: {e}")
    return {"job_id": job_id, "logs": logs}

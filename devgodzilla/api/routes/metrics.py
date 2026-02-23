"""
DevGodzilla Prometheus Metrics Endpoint

Provides Prometheus-compatible metrics for observability.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from devgodzilla.api.dependencies import get_db
from devgodzilla.db.database import Database
from devgodzilla.logging import get_logger

# Try to import prometheus_client, provide stub if not available
try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Stubs
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

router = APIRouter(tags=["Metrics"])
logger = get_logger(__name__)


# ==================== JSON Summary Models ====================

class JobTypeMetric(BaseModel):
    job_type: str
    count: int
    avg_duration_seconds: Optional[float] = None


class EndpointMetric(BaseModel):
    path: str
    calls: int
    avg_ms: Optional[float] = None


class MetricsSummary(BaseModel):
    total_events: int
    total_protocol_runs: int
    total_step_runs: int
    total_job_runs: int
    active_projects: int
    success_rate: float
    job_type_metrics: list[JobTypeMetric]
    recent_events_count: int
    degraded: bool = False
    errors: list[str] = Field(default_factory=list)


@router.get("/metrics/summary", response_model=MetricsSummary)
def metrics_summary(
    hours: int = 24,
    db: Database = Depends(get_db),
):
    """
    JSON metrics summary for the frontend dashboard.
    
    Returns aggregated stats from the database.
    """
    errors: list[str] = []

    # Get basic counts
    try:
        projects = db.list_projects()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Failed to load projects for metrics: {exc}")

    active_projects = len([p for p in projects if p.status != "archived"])
    
    # Get protocol runs across all projects
    all_protocol_runs = []
    for project in projects:
        try:
            runs = db.list_protocol_runs(project.id)
            all_protocol_runs.extend(runs)
        except Exception as exc:
            errors.append(f"protocol_runs_unavailable: project_id={project.id} error={exc}")
            logger.warning("metrics_protocol_runs_unavailable", extra={"project_id": project.id, "error": str(exc)})
    total_protocol_runs = len(all_protocol_runs)
    
    # Calculate success rate
    completed = [r for r in all_protocol_runs if r.status in ("completed", "passed")]
    failed = [r for r in all_protocol_runs if r.status in ("failed", "error")]
    total_finished = len(completed) + len(failed)
    if total_finished > 0:
        success_rate = len(completed) / total_finished * 100
    else:
        success_rate = 0.0 if errors else 100.0
    
    # Get step runs across all protocol runs
    total_step_runs = 0
    for pr in all_protocol_runs:
        try:
            steps = db.list_step_runs(pr.id)
            total_step_runs += len(steps)
        except Exception as exc:
            errors.append(f"step_runs_unavailable: protocol_run_id={pr.id} error={exc}")
            logger.warning("metrics_step_runs_unavailable", extra={"protocol_run_id": pr.id, "error": str(exc)})
    
    # Get job runs (this method supports limit directly)
    try:
        job_runs = db.list_job_runs(limit=1000)
    except Exception as exc:
        errors.append(f"job_runs_unavailable: error={exc}")
        logger.warning("metrics_job_runs_unavailable", extra={"error": str(exc)})
        job_runs = []
    total_job_runs = len(job_runs)
    
    # Aggregate job runs by type
    job_type_counts: dict[str, list] = {}
    def _parse_ts(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    for jr in job_runs:
        jt = jr.job_type or "unknown"
        if jt not in job_type_counts:
            job_type_counts[jt] = []
        # Calculate duration if we have start/end times
        duration = None
        started_at = _parse_ts(jr.started_at)
        finished_at = _parse_ts(jr.finished_at)
        if started_at and finished_at:
            duration = (finished_at - started_at).total_seconds()
        job_type_counts[jt].append(duration)
    
    job_type_metrics = []
    for jt, durations in job_type_counts.items():
        valid_durations = [d for d in durations if d is not None]
        avg_dur = sum(valid_durations) / len(valid_durations) if valid_durations else None
        job_type_metrics.append(JobTypeMetric(
            job_type=jt,
            count=len(durations),
            avg_duration_seconds=avg_dur,
        ))
    
    # Sort by count descending
    job_type_metrics.sort(key=lambda x: x.count, reverse=True)
    
    # Get recent events count
    try:
        recent_events = db.list_recent_events(limit=500)
    except Exception as exc:
        errors.append(f"events_unavailable: error={exc}")
        logger.warning("metrics_events_unavailable", extra={"error": str(exc)})
        recent_events = []
    recent_events_count = len(recent_events)
    total_events = recent_events_count  # This is approximate
    
    return MetricsSummary(
        total_events=total_events,
        total_protocol_runs=total_protocol_runs,
        total_step_runs=total_step_runs,
        total_job_runs=total_job_runs,
        active_projects=active_projects,
        success_rate=round(success_rate, 1),
        job_type_metrics=job_type_metrics,
        recent_events_count=recent_events_count,
        degraded=len(errors) > 0,
        errors=errors,
    )



# ==================== Metrics Definitions ====================

# Protocol metrics
PROTOCOL_RUNS_TOTAL = Counter(
    "devgodzilla_protocol_runs_total",
    "Total number of protocol runs",
    ["status"],
)

PROTOCOL_DURATION_SECONDS = Histogram(
    "devgodzilla_protocol_duration_seconds",
    "Protocol run duration in seconds",
    buckets=[60, 300, 600, 1800, 3600, 7200],
)

# Step metrics
STEP_RUNS_TOTAL = Counter(
    "devgodzilla_step_runs_total",
    "Total number of step runs",
    ["step_type", "status"],
)

STEP_DURATION_SECONDS = Histogram(
    "devgodzilla_step_duration_seconds",
    "Step run duration in seconds",
    ["step_type"],
    buckets=[5, 15, 30, 60, 120, 300],
)

STEP_RETRIES_TOTAL = Counter(
    "devgodzilla_step_retries_total",
    "Total step retries",
    ["step_type", "agent_id"],
)

# QA metrics
QA_EVALUATIONS_TOTAL = Counter(
    "devgodzilla_qa_evaluations_total",
    "Total number of QA evaluations",
    ["verdict"],
)

QA_FINDINGS_TOTAL = Counter(
    "devgodzilla_qa_findings_total",
    "Total number of QA findings",
    ["severity"],
)

QA_DURATION_SECONDS = Histogram(
    "devgodzilla_qa_duration_seconds",
    "QA check duration in seconds",
    ["gate_id"],
    buckets=[1, 5, 10, 30, 60, 120],
)

# Agent metrics
AGENT_EXECUTIONS_TOTAL = Counter(
    "devgodzilla_agent_executions_total",
    "Total executions per agent",
    ["agent_id", "status"],
)

AGENT_TOKENS_TOTAL = Counter(
    "devgodzilla_agent_tokens_total",
    "Total tokens used by agents",
    ["agent_id"],
)

AGENT_AVAILABILITY = Gauge(
    "devgodzilla_agent_availability",
    "Agent availability status (1=available, 0=unavailable)",
    ["agent_id", "agent_kind"],
)

# Queue metrics
QUEUE_DEPTH = Gauge(
    "devgodzilla_queue_depth",
    "Current queue depth",
    ["queue_name", "priority"],
)

# Feedback loop metrics
FEEDBACK_LOOPS_TOTAL = Counter(
    "devgodzilla_feedback_loops_total",
    "Total feedback loops triggered",
    ["action_taken", "error_type"],
)

# Active gauges
ACTIVE_PROTOCOL_RUNS = Gauge(
    "devgodzilla_active_protocol_runs",
    "Number of currently running protocols",
)

ACTIVE_STEP_RUNS = Gauge(
    "devgodzilla_active_step_runs",
    "Number of currently running steps",
)

# ==================== Endpoints ====================

@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format.
    """
    if not PROMETHEUS_AVAILABLE:
        return Response(
            content=(
                "# devgodzilla metrics disabled\n"
                "# reason: prometheus_client not installed\n"
            ),
            media_type="text/plain",
        )
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# ==================== Helper Functions ====================

def record_protocol_started():
    """Record a protocol run started."""
    PROTOCOL_RUNS_TOTAL.labels(status="started").inc()
    ACTIVE_PROTOCOL_RUNS.set(ACTIVE_PROTOCOL_RUNS._value.get() + 1 if hasattr(ACTIVE_PROTOCOL_RUNS, '_value') else 1)


def record_protocol_completed(status: str, duration_seconds: float):
    """Record a protocol run completed."""
    PROTOCOL_RUNS_TOTAL.labels(status=status).inc()
    PROTOCOL_DURATION_SECONDS.observe(duration_seconds)
    ACTIVE_PROTOCOL_RUNS.set(max(0, ACTIVE_PROTOCOL_RUNS._value.get() - 1 if hasattr(ACTIVE_PROTOCOL_RUNS, '_value') else 0))


def record_step_started(step_type: str):
    """Record a step run started."""
    STEP_RUNS_TOTAL.labels(step_type=step_type, status="started").inc()
    ACTIVE_STEP_RUNS.set(ACTIVE_STEP_RUNS._value.get() + 1 if hasattr(ACTIVE_STEP_RUNS, '_value') else 1)


def record_step_completed(step_type: str, status: str, duration_seconds: float):
    """Record a step run completed."""
    STEP_RUNS_TOTAL.labels(step_type=step_type, status=status).inc()
    STEP_DURATION_SECONDS.labels(step_type=step_type).observe(duration_seconds)
    ACTIVE_STEP_RUNS.set(max(0, ACTIVE_STEP_RUNS._value.get() - 1 if hasattr(ACTIVE_STEP_RUNS, '_value') else 0))


def record_step_retry(step_type: str, agent_id: str):
    """Record a step retry."""
    STEP_RETRIES_TOTAL.labels(step_type=step_type, agent_id=agent_id).inc()


def record_qa_evaluation(verdict: str, findings_by_severity: dict):
    """Record a QA evaluation."""
    QA_EVALUATIONS_TOTAL.labels(verdict=verdict).inc()
    for severity, count in findings_by_severity.items():
        for _ in range(count):
            QA_FINDINGS_TOTAL.labels(severity=severity).inc()


def record_qa_duration(gate_id: str, duration_seconds: float):
    """Record QA gate duration."""
    QA_DURATION_SECONDS.labels(gate_id=gate_id).observe(duration_seconds)


def record_agent_execution(agent_id: str, status: str, tokens: int = 0):
    """Record an agent execution."""
    AGENT_EXECUTIONS_TOTAL.labels(agent_id=agent_id, status=status).inc()
    if tokens > 0:
        AGENT_TOKENS_TOTAL.labels(agent_id=agent_id).inc(tokens)


def record_feedback_loop(action_taken: str, error_type: str):
    """Record a feedback loop triggered."""
    FEEDBACK_LOOPS_TOTAL.labels(action_taken=action_taken, error_type=error_type).inc()


def update_queue_metrics(db: Database):
    """
    Update queue depth metrics.
    
    Queries pending steps grouped by priority and updates the gauge.
    """
    try:
        # Get all projects
        projects = db.list_projects()
        
        # Count pending steps by queue (protocol) and priority
        queue_counts: dict[tuple[str, str], int] = {}
        
        for project in projects:
            if project.status == "archived":
                continue
            protocol_runs = db.list_protocol_runs(project.id)
            for pr in protocol_runs:
                if pr.status not in ("pending", "planning", "running"):
                    continue
                steps = db.list_step_runs(pr.id)
                for step in steps:
                    if step.status == "pending":
                        queue_name = pr.protocol_name or "default"
                        priority = str(getattr(step, "priority", "normal") or "normal")
                        key = (queue_name, priority)
                        queue_counts[key] = queue_counts.get(key, 0) + 1
        
        # Update gauges
        for (queue_name, priority), count in queue_counts.items():
            QUEUE_DEPTH.labels(queue_name=queue_name, priority=priority).set(count)
            
    except Exception as exc:
        logger.warning(
            "update_queue_metrics_failed",
            extra={"error": str(exc)},
        )


def update_agent_metrics(registry):
    """
    Update agent availability metrics.
    
    Checks each agent and updates the availability gauge.
    
    Args:
        registry: EngineRegistry instance to check agent availability
    """
    try:
        availability = registry.check_all_available()
        for engine in registry.list_all():
            agent_id = engine.metadata.id
            agent_kind = engine.metadata.kind.value if hasattr(engine.metadata.kind, "value") else str(engine.metadata.kind)
            available = availability.get(agent_id, False)
            AGENT_AVAILABILITY.labels(agent_id=agent_id, agent_kind=agent_kind).set(1 if available else 0)
    except Exception as exc:
        logger.warning(
            "update_agent_metrics_failed",
            extra={"error": str(exc)},
        )

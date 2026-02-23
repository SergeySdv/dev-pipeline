"""
CLI Execution Tracking Service

Provides in-memory tracking of CLI executions (discovery, code generation, etc.)
with real-time log streaming and status updates.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import deque

from devgodzilla.logging import get_logger

logger = get_logger(__name__)


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class LogEntry:
    timestamp: datetime
    level: str  # info, debug, warn, error
    message: str
    source: Optional[str] = None  # e.g., "opencode", "discovery", "stdout", "stderr"
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CLIExecution:
    """Represents an in-progress or completed CLI execution."""
    execution_id: str
    execution_type: str  # discovery, code_gen, qa, etc.
    engine_id: str
    project_id: Optional[int] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    command: Optional[str] = None
    working_dir: Optional[str] = None
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    logs: deque = field(default_factory=lambda: deque(maxlen=10000))  # Keep last 10k log entries
    
    def add_log(self, level: str, message: str, source: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            message=message,
            source=source,
            metadata=metadata,
        )
        self.logs.append(entry)
        
    def to_dict(self, include_logs: bool = False, log_limit: int = 100) -> Dict[str, Any]:
        result = {
            "execution_id": self.execution_id,
            "execution_type": self.execution_type,
            "engine_id": self.engine_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": (
                (self.finished_at or datetime.now(timezone.utc)) - self.started_at
            ).total_seconds() if self.started_at else None,
            "command": self.command,
            "working_dir": self.working_dir,
            "pid": self.pid,
            "exit_code": self.exit_code,
            "error": self.error,
            "metadata": self.metadata,
            "log_count": len(self.logs),
        }
        if include_logs:
            # Return last N logs
            logs_list = list(self.logs)[-log_limit:]
            result["logs"] = [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "level": log.level,
                    "message": log.message,
                    "source": log.source,
                    "metadata": log.metadata,
                }
                for log in logs_list
            ]
        return result


class CLIExecutionTracker:
    """
    Singleton tracker for CLI executions.
    Provides thread-safe tracking of in-progress executions with log streaming.
    """
    _instance: Optional["CLIExecutionTracker"] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._executions: Dict[str, CLIExecution] = {}
        self._execution_lock = threading.Lock()
        self._subscribers: Dict[str, List[Callable[[LogEntry], None]]] = {}
        self._max_completed = 100  # Keep last 100 completed executions
        self._initialized = True
        logger.info("cli_execution_tracker_initialized")
    
    def start_execution(
        self,
        execution_type: str,
        engine_id: str,
        project_id: Optional[int] = None,
        command: Optional[str] = None,
        working_dir: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CLIExecution:
        """Start tracking a new CLI execution."""
        execution_id = str(uuid.uuid4())
        execution = CLIExecution(
            execution_id=execution_id,
            execution_type=execution_type,
            engine_id=engine_id,
            project_id=project_id,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            command=command,
            working_dir=working_dir,
            metadata=metadata or {},
        )
        
        with self._execution_lock:
            self._executions[execution_id] = execution
            
        execution.add_log("info", f"Started {execution_type} with engine {engine_id}", source="tracker")
        logger.info(
            "cli_execution_started",
            extra={
                "execution_id": execution_id,
                "execution_type": execution_type,
                "engine_id": engine_id,
                "project_id": project_id,
            },
        )
        return execution
    
    def log(
        self,
        execution_id: str,
        level: str,
        message: str,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add a log entry to an execution."""
        with self._execution_lock:
            execution = self._executions.get(execution_id)
            if not execution:
                return
            execution.add_log(level, message, source, metadata)
            
        # Notify subscribers
        subscribers = self._subscribers.get(execution_id, [])
        entry = execution.logs[-1] if execution.logs else None
        if entry:
            for callback in subscribers:
                try:
                    callback(entry)
                except Exception as e:
                    logger.warning("subscriber_callback_failed", extra={"error": str(e)})
    
    def set_pid(self, execution_id: str, pid: int):
        """Set the process ID for an execution."""
        with self._execution_lock:
            execution = self._executions.get(execution_id)
            if execution:
                execution.pid = pid
                execution.add_log("debug", f"Process started with PID {pid}", source="tracker")
    
    def complete(
        self,
        execution_id: str,
        success: bool,
        exit_code: Optional[int] = None,
        error: Optional[str] = None,
    ):
        """Mark an execution as completed."""
        with self._execution_lock:
            execution = self._executions.get(execution_id)
            if not execution:
                return
            if execution.status == ExecutionStatus.CANCELLED:
                # Preserve user-initiated cancellation if the process exits later.
                execution.exit_code = exit_code
                if error:
                    execution.error = error
                if execution.finished_at is None:
                    execution.finished_at = datetime.now(timezone.utc)
                execution.add_log(
                    "debug",
                    "Execution completion received after cancellation; preserving cancelled status",
                    source="tracker",
                )
                self._cleanup_old_executions()
                return
            execution.status = ExecutionStatus.SUCCEEDED if success else ExecutionStatus.FAILED
            execution.finished_at = datetime.now(timezone.utc)
            execution.exit_code = exit_code
            execution.error = error
            
            status_msg = "completed successfully" if success else f"failed: {error or 'unknown error'}"
            execution.add_log("info", f"Execution {status_msg}", source="tracker")
            
            # Cleanup old completed executions
            self._cleanup_old_executions()
            
        logger.info(
            "cli_execution_completed",
            extra={
                "execution_id": execution_id,
                "success": success,
                "exit_code": exit_code,
                "duration": (
                    (execution.finished_at - execution.started_at).total_seconds()
                    if execution.started_at and execution.finished_at
                    else None
                ),
            },
        )
    
    def cancel(self, execution_id: str):
        """Mark an execution as cancelled."""
        with self._execution_lock:
            execution = self._executions.get(execution_id)
            if not execution:
                return
            execution.status = ExecutionStatus.CANCELLED
            execution.finished_at = datetime.now(timezone.utc)
            execution.add_log("warn", "Execution cancelled", source="tracker")
    
    def get_execution(self, execution_id: str) -> Optional[CLIExecution]:
        """Get an execution by ID."""
        with self._execution_lock:
            return self._executions.get(execution_id)
    
    def list_executions(
        self,
        execution_type: Optional[str] = None,
        project_id: Optional[int] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 50,
    ) -> List[CLIExecution]:
        """List executions with optional filters."""
        with self._execution_lock:
            executions = list(self._executions.values())
            
        # Apply filters
        if execution_type:
            executions = [e for e in executions if e.execution_type == execution_type]
        if project_id is not None:
            executions = [e for e in executions if e.project_id == project_id]
        if status:
            executions = [e for e in executions if e.status == status]
            
        # Sort by started_at descending
        executions.sort(key=lambda e: e.started_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        
        return executions[:limit]
    
    def list_active(self, limit: int = 50) -> List[CLIExecution]:
        """List currently running executions."""
        return self.list_executions(status=ExecutionStatus.RUNNING, limit=limit)
    
    def subscribe(self, execution_id: str, callback: Callable[[LogEntry], None]):
        """Subscribe to log updates for an execution."""
        with self._execution_lock:
            if execution_id not in self._subscribers:
                self._subscribers[execution_id] = []
            self._subscribers[execution_id].append(callback)
    
    def unsubscribe(self, execution_id: str, callback: Callable[[LogEntry], None]):
        """Unsubscribe from log updates."""
        with self._execution_lock:
            if execution_id in self._subscribers:
                try:
                    self._subscribers[execution_id].remove(callback)
                except ValueError:
                    pass
    
    def _cleanup_old_executions(self):
        """Remove old completed executions to prevent memory bloat."""
        completed = [
            e for e in self._executions.values()
            if e.status in (ExecutionStatus.SUCCEEDED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED)
        ]
        completed.sort(key=lambda e: e.finished_at or datetime.min.replace(tzinfo=timezone.utc))
        
        # Remove oldest if we have too many
        while len(completed) > self._max_completed:
            oldest = completed.pop(0)
            del self._executions[oldest.execution_id]
            # Clean up subscribers
            self._subscribers.pop(oldest.execution_id, None)


# Global singleton accessor
def get_execution_tracker() -> CLIExecutionTracker:
    return CLIExecutionTracker()

"""
DevGodzilla Health Checking Service

Comprehensive health checking for database, Windmill, and agents.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import asyncio
import time

from devgodzilla.logging import get_logger

logger = get_logger(__name__)

__version__ = "0.1.0"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: str  # "ok", "degraded", "error"
    message: Optional[str] = None
    latency_ms: Optional[int] = None
    details: dict = field(default_factory=dict)


@dataclass
class HealthStatus:
    """Overall health status."""
    status: str  # "ok", "degraded", "error"
    version: str
    timestamp: datetime
    components: Dict[str, ComponentHealth]
    checks_passed: int
    checks_failed: int


@dataclass
class AgentHealthSummary:
    """Summary of agent health check results."""
    total: int
    available: int
    unavailable: int
    details: List[Dict[str, Any]] = field(default_factory=list)


class HealthChecker:
    """
    Comprehensive health checking service.
    
    Provides health checks for:
    - Database connectivity
    - Windmill connectivity
    - Agent availability
    
    Example:
        checker = HealthChecker(db, windmill_client, agent_registry)
        status = await checker.check_all()
        print(status.status)  # "ok", "degraded", or "error"
    """
    
    def __init__(
        self,
        db: Any,
        windmill: Any,
        agent_registry: Any,
        *,
        db_timeout_ms: int = 5000,
        windmill_timeout_ms: int = 5000,
        agent_timeout_ms: int = 2000,
    ) -> None:
        self.db = db
        self.windmill = windmill
        self.agent_registry = agent_registry
        self.db_timeout_ms = db_timeout_ms
        self.windmill_timeout_ms = windmill_timeout_ms
        self.agent_timeout_ms = agent_timeout_ms
    
    async def check_all(self) -> HealthStatus:
        """Run all health checks."""
        components: Dict[str, ComponentHealth] = {}
        
        # Run checks concurrently
        db_task = asyncio.create_task(self._check_database())
        windmill_task = asyncio.create_task(self._check_windmill())
        agents_task = asyncio.create_task(self._check_agents())
        
        components["database"] = await db_task
        components["windmill"] = await windmill_task
        components["agents"] = await agents_task
        
        # Determine overall status
        all_ok = all(c.status == "ok" for c in components.values())
        any_error = any(c.status == "error" for c in components.values())
        
        status = "ok" if all_ok else ("error" if any_error else "degraded")
        
        return HealthStatus(
            status=status,
            version=__version__,
            timestamp=datetime.now(timezone.utc),
            components=components,
            checks_passed=sum(1 for c in components.values() if c.status == "ok"),
            checks_failed=sum(1 for c in components.values() if c.status == "error"),
        )
    
    async def _check_database(self) -> ComponentHealth:
        """Check database connectivity."""
        start = time.perf_counter()
        try:
            # Simple query to verify connectivity
            self.db.list_projects()
            latency_ms = int((time.perf_counter() - start) * 1000)
            
            return ComponentHealth(
                name="database",
                status="ok",
                latency_ms=latency_ms,
                details={"driver": "sqlite"},
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.error(
                "health_check_database_failed",
                extra={"error": str(exc)},
            )
            return ComponentHealth(
                name="database",
                status="error",
                message=str(exc),
                latency_ms=latency_ms,
            )
    
    async def _check_windmill(self) -> ComponentHealth:
        """Check Windmill connectivity."""
        if self.windmill is None:
            return ComponentHealth(
                name="windmill",
                status="ok",
                message="disabled",
                details={"enabled": False},
            )
        
        start = time.perf_counter()
        try:
            available = self.windmill.health_check()
            latency_ms = int((time.perf_counter() - start) * 1000)
            
            if available:
                return ComponentHealth(
                    name="windmill",
                    status="ok",
                    latency_ms=latency_ms,
                    details={"enabled": True},
                )
            else:
                return ComponentHealth(
                    name="windmill",
                    status="error",
                    message="health_check returned false",
                    latency_ms=latency_ms,
                    details={"enabled": True},
                )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.warning(
                "health_check_windmill_failed",
                extra={"error": str(exc)},
            )
            return ComponentHealth(
                name="windmill",
                status="error",
                message=str(exc),
                latency_ms=latency_ms,
                details={"enabled": True},
            )
    
    async def _check_agents(self) -> ComponentHealth:
        """Check agent availability and return summary."""
        if self.agent_registry is None:
            return ComponentHealth(
                name="agents",
                status="ok",
                message="no_registry",
                details={"total": 0, "available": 0, "unavailable": 0},
            )
        
        start = time.perf_counter()
        try:
            availability = self.agent_registry.check_all_available()
            engines = self.agent_registry.list_all()
            
            total = len(engines)
            available_count = sum(1 for v in availability.values() if v)
            unavailable_count = total - available_count
            
            latency_ms = int((time.perf_counter() - start) * 1000)
            
            details = [
                {
                    "agent_id": e.metadata.id,
                    "kind": e.metadata.kind.value if hasattr(e.metadata.kind, "value") else str(e.metadata.kind),
                    "available": availability.get(e.metadata.id, False),
                }
                for e in engines
            ]
            
            # Status is ok if all agents available, degraded if some unavailable, error if none
            if total == 0:
                status = "ok"
            elif available_count == total:
                status = "ok"
            elif available_count > 0:
                status = "degraded"
            else:
                status = "error"
            
            return ComponentHealth(
                name="agents",
                status=status,
                latency_ms=latency_ms,
                details={
                    "total": total,
                    "available": available_count,
                    "unavailable": unavailable_count,
                    "agents": details,
                },
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            logger.warning(
                "health_check_agents_failed",
                extra={"error": str(exc)},
            )
            return ComponentHealth(
                name="agents",
                status="error",
                message=str(exc),
                latency_ms=latency_ms,
            )
    
    async def check_agent(self, agent_id: str) -> ComponentHealth:
        """Check specific agent availability."""
        if self.agent_registry is None:
            return ComponentHealth(
                name=f"agent:{agent_id}",
                status="error",
                message="no_registry",
            )
        
        start = time.perf_counter()
        try:
            engine = self.agent_registry.get(agent_id)
            available = engine.check_availability()
            latency_ms = int((time.perf_counter() - start) * 1000)
            
            return ComponentHealth(
                name=f"agent:{agent_id}",
                status="ok" if available else "error",
                message=None if available else "unavailable",
                latency_ms=latency_ms,
                details={
                    "agent_id": agent_id,
                    "kind": engine.metadata.kind.value if hasattr(engine.metadata.kind, "value") else str(engine.metadata.kind),
                },
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ComponentHealth(
                name=f"agent:{agent_id}",
                status="error",
                message=str(exc),
                latency_ms=latency_ms,
            )
    
    def check_all_sync(self) -> HealthStatus:
        """
        Synchronous version of check_all for use in non-async contexts.
        
        This runs all health checks sequentially.
        """
        components: Dict[str, ComponentHealth] = {}
        
        # Database check
        components["database"] = self._check_database_sync()
        
        # Windmill check
        components["windmill"] = self._check_windmill_sync()
        
        # Agents check
        components["agents"] = self._check_agents_sync()
        
        # Determine overall status
        all_ok = all(c.status == "ok" for c in components.values())
        any_error = any(c.status == "error" for c in components.values())
        
        status = "ok" if all_ok else ("error" if any_error else "degraded")
        
        return HealthStatus(
            status=status,
            version=__version__,
            timestamp=datetime.now(timezone.utc),
            components=components,
            checks_passed=sum(1 for c in components.values() if c.status == "ok"),
            checks_failed=sum(1 for c in components.values() if c.status == "error"),
        )
    
    def _check_database_sync(self) -> ComponentHealth:
        """Synchronous database check."""
        start = time.perf_counter()
        try:
            self.db.list_projects()
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ComponentHealth(
                name="database",
                status="ok",
                latency_ms=latency_ms,
                details={"driver": "sqlite"},
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ComponentHealth(
                name="database",
                status="error",
                message=str(exc),
                latency_ms=latency_ms,
            )
    
    def _check_windmill_sync(self) -> ComponentHealth:
        """Synchronous Windmill check."""
        if self.windmill is None:
            return ComponentHealth(
                name="windmill",
                status="ok",
                message="disabled",
                details={"enabled": False},
            )
        
        start = time.perf_counter()
        try:
            available = self.windmill.health_check()
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ComponentHealth(
                name="windmill",
                status="ok" if available else "error",
                message=None if available else "health_check returned false",
                latency_ms=latency_ms,
                details={"enabled": True},
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ComponentHealth(
                name="windmill",
                status="error",
                message=str(exc),
                latency_ms=latency_ms,
                details={"enabled": True},
            )
    
    def _check_agents_sync(self) -> ComponentHealth:
        """Synchronous agents check."""
        if self.agent_registry is None:
            return ComponentHealth(
                name="agents",
                status="ok",
                message="no_registry",
                details={"total": 0, "available": 0, "unavailable": 0},
            )
        
        start = time.perf_counter()
        try:
            availability = self.agent_registry.check_all_available()
            engines = self.agent_registry.list_all()
            
            total = len(engines)
            available_count = sum(1 for v in availability.values() if v)
            unavailable_count = total - available_count
            
            latency_ms = int((time.perf_counter() - start) * 1000)
            
            if total == 0:
                status = "ok"
            elif available_count == total:
                status = "ok"
            elif available_count > 0:
                status = "degraded"
            else:
                status = "error"
            
            details = [
                {
                    "agent_id": e.metadata.id,
                    "kind": e.metadata.kind.value if hasattr(e.metadata.kind, "value") else str(e.metadata.kind),
                    "available": availability.get(e.metadata.id, False),
                }
                for e in engines
            ]
            
            return ComponentHealth(
                name="agents",
                status=status,
                latency_ms=latency_ms,
                details={
                    "total": total,
                    "available": available_count,
                    "unavailable": unavailable_count,
                    "agents": details,
                },
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - start) * 1000)
            return ComponentHealth(
                name="agents",
                status="error",
                message=str(exc),
                latency_ms=latency_ms,
            )


def health_status_to_dict(status: HealthStatus) -> Dict[str, Any]:
    """Convert HealthStatus to a JSON-serializable dict."""
    return {
        "status": status.status,
        "version": status.version,
        "timestamp": status.timestamp.isoformat(),
        "checks_passed": status.checks_passed,
        "checks_failed": status.checks_failed,
        "components": {
            name: {
                "name": comp.name,
                "status": comp.status,
                "message": comp.message,
                "latency_ms": comp.latency_ms,
                "details": comp.details,
            }
            for name, comp in status.components.items()
        },
    }

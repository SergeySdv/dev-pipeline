"""Service-layer facades for the Tasksgodzilla orchestrator.

These modules provide thin wrappers around the existing implementation so that
API/CLI/TUI callers can migrate toward a clearer services API incrementally.

The initial versions intentionally delegate most work to the current workers and
helpers; behaviour should remain unchanged while call sites are updated.
"""

from .execution import ExecutionService
from .onboarding import OnboardingService
from .quality import QualityService
from .spec import SpecService
from .orchestrator import OrchestratorService

__all__ = [
    "ExecutionService",
    "OnboardingService",
    "QualityService",
    "SpecService",
    "OrchestratorService",
]


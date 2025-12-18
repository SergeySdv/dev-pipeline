"""Platform-level service facades (queue, telemetry, etc.)."""

from .queue import QueueService
from .telemetry import TelemetryService

__all__ = ["QueueService", "TelemetryService"]


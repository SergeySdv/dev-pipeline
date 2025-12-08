from __future__ import annotations

from dataclasses import dataclass

from tasksgodzilla.metrics import metrics


@dataclass
class TelemetryService:
    """Thin wrapper over the shared metrics helpers.

    This makes it easier to swap or augment metrics collection without changing
    upstream services.
    """

    def observe_tokens(self, phase: str, model: str, tokens: int) -> None:
        """Record estimated token usage for a given phase/model."""
        metrics.observe_tokens(phase, model, tokens)


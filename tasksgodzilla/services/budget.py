from dataclasses import dataclass
from typing import Optional

from tasksgodzilla.codex import enforce_token_budget, estimate_tokens
from tasksgodzilla.metrics import metrics


@dataclass
class BudgetService:
    """Service for managing token budgets and tracking usage."""

    def check_and_track(
        self,
        prompt_text: str,
        model: str,
        phase: str,
        budget_mode: str,
        max_tokens: Optional[int],
    ) -> int:
        """
        Enforce configured token budgets and record estimated usage for observability.
        Returns the estimated token count for the prompt.
        
        Raises:
            BudgetExceededError: If the estimated tokens exceed the max_tokens limit
                               and budget_mode is 'strict'.
        """
        enforce_token_budget(prompt_text, max_tokens, phase, mode=budget_mode)
        estimated = estimate_tokens(prompt_text)
        metrics.observe_tokens(phase, model, estimated)
        return estimated

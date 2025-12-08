
import pytest
from unittest.mock import MagicMock, call

from tasksgodzilla.services.budget import BudgetService


@pytest.fixture
def service():
    return BudgetService()


def test_check_and_track_strict_ok(service, monkeypatch):
    mock_enforce = MagicMock()
    mock_estimate = MagicMock(return_value=100)
    mock_metrics = MagicMock()
    
    monkeypatch.setattr("tasksgodzilla.services.budget.enforce_token_budget", mock_enforce)
    monkeypatch.setattr("tasksgodzilla.services.budget.estimate_tokens", mock_estimate)
    monkeypatch.setattr("tasksgodzilla.services.budget.metrics.observe_tokens", mock_metrics)

    tokens = service.check_and_track("prompt", "model-x", "exec", "strict", 500)
    
    assert tokens == 100
    mock_enforce.assert_called_once_with("prompt", 500, "exec", mode="strict")
    mock_metrics.assert_called_once_with("exec", "model-x", 100)


def test_check_and_track_raises_on_enforce_failure(service, monkeypatch):
    def fake_enforce(*args, **kwargs):
        raise ValueError("Budget exceeded")

    mock_estimate = MagicMock(return_value=600)
    mock_metrics = MagicMock()

    monkeypatch.setattr("tasksgodzilla.services.budget.enforce_token_budget", fake_enforce)
    monkeypatch.setattr("tasksgodzilla.services.budget.estimate_tokens", mock_estimate)
    monkeypatch.setattr("tasksgodzilla.services.budget.metrics.observe_tokens", mock_metrics)

    with pytest.raises(ValueError):
        service.check_and_track("prompt", "model-x", "exec", "strict", 500)
    
    # Validation happens before tracking in the implementation order
    # enforce_token_budget -> estimate -> observe. 
    # Wait, enforce usually calls estimate internally? 
    # In budget.py: enforce...; estimate...; observe...
    # So if enforce raises, estimate/observe after are not called.
    mock_metrics.assert_not_called()

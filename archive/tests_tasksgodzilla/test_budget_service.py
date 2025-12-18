
import pytest
from unittest.mock import MagicMock, call

from tasksgodzilla.services.budget import BudgetService
from tasksgodzilla.errors import BudgetExceededError


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


def test_check_protocol_budget_no_limit(service):
    """Test that check_protocol_budget allows unlimited tokens when max_protocol_tokens is None."""
    # Should not raise with no limit
    service.check_protocol_budget(
        protocol_run_id=1,
        estimated_tokens=10000,
        max_protocol_tokens=None,
        budget_mode="strict"
    )
    # Usage should not be tracked when no limit
    assert service._protocol_token_usage.get(1, 0) == 0


def test_check_protocol_budget_off_mode(service):
    """Test that check_protocol_budget allows any usage when budget_mode is 'off'."""
    # Should not raise even with limit when mode is off
    service.check_protocol_budget(
        protocol_run_id=1,
        estimated_tokens=10000,
        max_protocol_tokens=5000,
        budget_mode="off"
    )
    # Usage should not be tracked when mode is off
    assert service._protocol_token_usage.get(1, 0) == 0


def test_check_protocol_budget_within_limit(service):
    """Test that check_protocol_budget tracks usage when within limit."""
    protocol_id = 1
    
    # First call: 100 tokens
    service.check_protocol_budget(
        protocol_run_id=protocol_id,
        estimated_tokens=100,
        max_protocol_tokens=1000,
        budget_mode="strict"
    )
    assert service._protocol_token_usage[protocol_id] == 100
    
    # Second call: 200 more tokens
    service.check_protocol_budget(
        protocol_run_id=protocol_id,
        estimated_tokens=200,
        max_protocol_tokens=1000,
        budget_mode="strict"
    )
    assert service._protocol_token_usage[protocol_id] == 300
    
    # Third call: 500 more tokens (total 800, still under 1000)
    service.check_protocol_budget(
        protocol_run_id=protocol_id,
        estimated_tokens=500,
        max_protocol_tokens=1000,
        budget_mode="strict"
    )
    assert service._protocol_token_usage[protocol_id] == 800


def test_check_protocol_budget_exceeds_limit_strict(service):
    """Test that check_protocol_budget raises BudgetExceededError in strict mode."""
    protocol_id = 1
    
    # First call: 600 tokens
    service.check_protocol_budget(
        protocol_run_id=protocol_id,
        estimated_tokens=600,
        max_protocol_tokens=1000,
        budget_mode="strict"
    )
    assert service._protocol_token_usage[protocol_id] == 600
    
    # Second call: 500 more tokens would exceed limit (1100 > 1000)
    with pytest.raises(BudgetExceededError) as exc_info:
        service.check_protocol_budget(
            protocol_run_id=protocol_id,
            estimated_tokens=500,
            max_protocol_tokens=1000,
            budget_mode="strict"
        )
    
    # Verify error message contains useful information
    error = exc_info.value
    assert "1100" in str(error)  # projected usage
    assert "1000" in str(error)  # max limit
    assert "600" in str(error)   # current usage
    assert "500" in str(error)   # estimated additional
    
    # Verify metadata
    assert error.metadata["protocol_run_id"] == protocol_id
    assert error.metadata["current_usage"] == 600
    assert error.metadata["estimated_tokens"] == 500
    assert error.metadata["projected_usage"] == 1100
    assert error.metadata["max_protocol_tokens"] == 1000
    
    # Usage should not be updated when budget exceeded
    assert service._protocol_token_usage[protocol_id] == 600


def test_check_protocol_budget_exceeds_limit_warn(service, monkeypatch):
    """Test that check_protocol_budget logs warning in warn mode but doesn't raise."""
    protocol_id = 1
    mock_log = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.budget.log.warning", mock_log)
    
    # First call: 600 tokens
    service.check_protocol_budget(
        protocol_run_id=protocol_id,
        estimated_tokens=600,
        max_protocol_tokens=1000,
        budget_mode="warn"
    )
    assert service._protocol_token_usage[protocol_id] == 600
    
    # Second call: 500 more tokens would exceed limit, but should only warn
    service.check_protocol_budget(
        protocol_run_id=protocol_id,
        estimated_tokens=500,
        max_protocol_tokens=1000,
        budget_mode="warn"
    )
    
    # Should have logged a warning
    mock_log.assert_called_once()
    call_args = mock_log.call_args
    assert "Protocol budget exceeded" in call_args[0][0]
    
    # Usage should not be updated when budget exceeded in warn mode
    assert service._protocol_token_usage[protocol_id] == 600


def test_check_protocol_budget_multiple_protocols(service):
    """Test that check_protocol_budget tracks usage separately for different protocols."""
    # Protocol 1: 300 tokens
    service.check_protocol_budget(
        protocol_run_id=1,
        estimated_tokens=300,
        max_protocol_tokens=1000,
        budget_mode="strict"
    )
    
    # Protocol 2: 500 tokens
    service.check_protocol_budget(
        protocol_run_id=2,
        estimated_tokens=500,
        max_protocol_tokens=1000,
        budget_mode="strict"
    )
    
    # Protocol 1: 400 more tokens
    service.check_protocol_budget(
        protocol_run_id=1,
        estimated_tokens=400,
        max_protocol_tokens=1000,
        budget_mode="strict"
    )
    
    # Verify separate tracking
    assert service._protocol_token_usage[1] == 700
    assert service._protocol_token_usage[2] == 500


def test_check_protocol_budget_exact_limit(service):
    """Test that check_protocol_budget allows usage exactly at the limit."""
    protocol_id = 1
    
    # Use exactly the limit
    service.check_protocol_budget(
        protocol_run_id=protocol_id,
        estimated_tokens=1000,
        max_protocol_tokens=1000,
        budget_mode="strict"
    )
    assert service._protocol_token_usage[protocol_id] == 1000
    
    # One more token should fail
    with pytest.raises(BudgetExceededError):
        service.check_protocol_budget(
            protocol_run_id=protocol_id,
            estimated_tokens=1,
            max_protocol_tokens=1000,
            budget_mode="strict"
        )


def test_check_step_budget_no_limit(service):
    """Test that check_step_budget allows unlimited tokens when max_step_tokens is None."""
    # Should not raise with no limit
    service.check_step_budget(
        step_run_id=1,
        estimated_tokens=10000,
        max_step_tokens=None,
        budget_mode="strict"
    )
    # Usage should not be tracked when no limit
    assert service._step_token_usage.get(1, 0) == 0


def test_check_step_budget_off_mode(service):
    """Test that check_step_budget allows any usage when budget_mode is 'off'."""
    # Should not raise even with limit when mode is off
    service.check_step_budget(
        step_run_id=1,
        estimated_tokens=10000,
        max_step_tokens=5000,
        budget_mode="off"
    )
    # Usage should not be tracked when mode is off
    assert service._step_token_usage.get(1, 0) == 0


def test_check_step_budget_within_limit(service):
    """Test that check_step_budget tracks usage when within limit."""
    step_id = 1
    
    # First call: 100 tokens
    service.check_step_budget(
        step_run_id=step_id,
        estimated_tokens=100,
        max_step_tokens=1000,
        budget_mode="strict"
    )
    assert service._step_token_usage[step_id] == 100
    
    # Second call: 200 more tokens
    service.check_step_budget(
        step_run_id=step_id,
        estimated_tokens=200,
        max_step_tokens=1000,
        budget_mode="strict"
    )
    assert service._step_token_usage[step_id] == 300
    
    # Third call: 500 more tokens (total 800, still under 1000)
    service.check_step_budget(
        step_run_id=step_id,
        estimated_tokens=500,
        max_step_tokens=1000,
        budget_mode="strict"
    )
    assert service._step_token_usage[step_id] == 800


def test_check_step_budget_exceeds_limit_strict(service):
    """Test that check_step_budget raises BudgetExceededError in strict mode."""
    step_id = 1
    
    # First call: 600 tokens
    service.check_step_budget(
        step_run_id=step_id,
        estimated_tokens=600,
        max_step_tokens=1000,
        budget_mode="strict"
    )
    assert service._step_token_usage[step_id] == 600
    
    # Second call: 500 more tokens would exceed limit (1100 > 1000)
    with pytest.raises(BudgetExceededError) as exc_info:
        service.check_step_budget(
            step_run_id=step_id,
            estimated_tokens=500,
            max_step_tokens=1000,
            budget_mode="strict"
        )
    
    # Verify error message contains useful information
    error = exc_info.value
    assert "1100" in str(error)  # projected usage
    assert "1000" in str(error)  # max limit
    assert "600" in str(error)   # current usage
    assert "500" in str(error)   # estimated additional
    
    # Verify metadata
    assert error.metadata["step_run_id"] == step_id
    assert error.metadata["current_usage"] == 600
    assert error.metadata["estimated_tokens"] == 500
    assert error.metadata["projected_usage"] == 1100
    assert error.metadata["max_step_tokens"] == 1000
    
    # Usage should not be updated when budget exceeded
    assert service._step_token_usage[step_id] == 600


def test_check_step_budget_exceeds_limit_warn(service, monkeypatch):
    """Test that check_step_budget logs warning in warn mode but doesn't raise."""
    step_id = 1
    mock_log = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.budget.log.warning", mock_log)
    
    # First call: 600 tokens
    service.check_step_budget(
        step_run_id=step_id,
        estimated_tokens=600,
        max_step_tokens=1000,
        budget_mode="warn"
    )
    assert service._step_token_usage[step_id] == 600
    
    # Second call: 500 more tokens would exceed limit, but should only warn
    service.check_step_budget(
        step_run_id=step_id,
        estimated_tokens=500,
        max_step_tokens=1000,
        budget_mode="warn"
    )
    
    # Should have logged a warning
    mock_log.assert_called_once()
    call_args = mock_log.call_args
    assert "Step budget exceeded" in call_args[0][0]
    
    # Usage should not be updated when budget exceeded in warn mode
    assert service._step_token_usage[step_id] == 600


def test_check_step_budget_multiple_steps(service):
    """Test that check_step_budget tracks usage separately for different steps."""
    # Step 1: 300 tokens
    service.check_step_budget(
        step_run_id=1,
        estimated_tokens=300,
        max_step_tokens=1000,
        budget_mode="strict"
    )
    
    # Step 2: 500 tokens
    service.check_step_budget(
        step_run_id=2,
        estimated_tokens=500,
        max_step_tokens=1000,
        budget_mode="strict"
    )
    
    # Step 1: 400 more tokens
    service.check_step_budget(
        step_run_id=1,
        estimated_tokens=400,
        max_step_tokens=1000,
        budget_mode="strict"
    )
    
    # Verify separate tracking
    assert service._step_token_usage[1] == 700
    assert service._step_token_usage[2] == 500


def test_check_step_budget_exact_limit(service):
    """Test that check_step_budget allows usage exactly at the limit."""
    step_id = 1
    
    # Use exactly the limit
    service.check_step_budget(
        step_run_id=step_id,
        estimated_tokens=1000,
        max_step_tokens=1000,
        budget_mode="strict"
    )
    assert service._step_token_usage[step_id] == 1000
    
    # One more token should fail
    with pytest.raises(BudgetExceededError):
        service.check_step_budget(
            step_run_id=step_id,
            estimated_tokens=1,
            max_step_tokens=1000,
            budget_mode="strict"
        )


def test_record_usage_basic(service, monkeypatch):
    """Test that record_usage updates cumulative totals and records metrics."""
    mock_metrics = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.budget.metrics.observe_tokens", mock_metrics)
    
    protocol_id = 1
    step_id = 10
    
    # Record usage for a step
    service.record_usage(
        protocol_run_id=protocol_id,
        step_run_id=step_id,
        phase="exec",
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50
    )
    
    # Verify cumulative totals updated
    assert service._protocol_token_usage[protocol_id] == 150
    assert service._step_token_usage[step_id] == 150
    
    # Verify metrics recorded
    mock_metrics.assert_called_once_with("exec", "gpt-4", 150)


def test_record_usage_protocol_level(service, monkeypatch):
    """Test that record_usage works for protocol-level operations without step_run_id."""
    mock_metrics = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.budget.metrics.observe_tokens", mock_metrics)
    
    protocol_id = 1
    
    # Record usage for protocol-level operation (e.g., planning)
    service.record_usage(
        protocol_run_id=protocol_id,
        step_run_id=None,
        phase="planning",
        model="zai-coding-plan/glm-4.6",
        prompt_tokens=500,
        completion_tokens=200
    )
    
    # Verify protocol cumulative updated
    assert service._protocol_token_usage[protocol_id] == 700
    
    # Verify no step usage tracked
    assert len(service._step_token_usage) == 0
    
    # Verify metrics recorded
    mock_metrics.assert_called_once_with("planning", "zai-coding-plan/glm-4.6", 700)


def test_record_usage_cumulative(service, monkeypatch):
    """Test that record_usage accumulates tokens across multiple calls."""
    mock_metrics = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.budget.metrics.observe_tokens", mock_metrics)
    
    protocol_id = 1
    step_id = 10
    
    # First call
    service.record_usage(
        protocol_run_id=protocol_id,
        step_run_id=step_id,
        phase="exec",
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50
    )
    
    # Second call
    service.record_usage(
        protocol_run_id=protocol_id,
        step_run_id=step_id,
        phase="exec",
        model="gpt-4",
        prompt_tokens=200,
        completion_tokens=100
    )
    
    # Third call
    service.record_usage(
        protocol_run_id=protocol_id,
        step_run_id=step_id,
        phase="qa",
        model="gpt-4",
        prompt_tokens=50,
        completion_tokens=25
    )
    
    # Verify cumulative totals
    assert service._protocol_token_usage[protocol_id] == 525  # 150 + 300 + 75
    assert service._step_token_usage[step_id] == 525
    
    # Verify metrics called for each phase
    assert mock_metrics.call_count == 3


def test_record_usage_multiple_steps_same_protocol(service, monkeypatch):
    """Test that record_usage tracks multiple steps within same protocol correctly."""
    mock_metrics = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.budget.metrics.observe_tokens", mock_metrics)
    
    protocol_id = 1
    
    # Step 1
    service.record_usage(
        protocol_run_id=protocol_id,
        step_run_id=10,
        phase="exec",
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50
    )
    
    # Step 2
    service.record_usage(
        protocol_run_id=protocol_id,
        step_run_id=20,
        phase="exec",
        model="gpt-4",
        prompt_tokens=200,
        completion_tokens=100
    )
    
    # Verify protocol cumulative includes both steps
    assert service._protocol_token_usage[protocol_id] == 450  # 150 + 300
    
    # Verify steps tracked separately
    assert service._step_token_usage[10] == 150
    assert service._step_token_usage[20] == 300


def test_record_usage_different_models(service, monkeypatch):
    """Test that record_usage correctly tracks different models."""
    mock_metrics = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.budget.metrics.observe_tokens", mock_metrics)
    
    protocol_id = 1
    
    # Planning with one model
    service.record_usage(
        protocol_run_id=protocol_id,
        step_run_id=None,
        phase="planning",
        model="zai-coding-plan/glm-4.6",
        prompt_tokens=500,
        completion_tokens=200
    )
    
    # Execution with different model
    service.record_usage(
        protocol_run_id=protocol_id,
        step_run_id=10,
        phase="exec",
        model="zai-coding-plan/glm-4.6",
        prompt_tokens=300,
        completion_tokens=150
    )
    
    # Verify protocol cumulative includes both
    assert service._protocol_token_usage[protocol_id] == 1150  # 700 + 450
    
    # Verify metrics called with correct models
    assert mock_metrics.call_count == 2
    calls = mock_metrics.call_args_list
    assert calls[0] == call("planning", "zai-coding-plan/glm-4.6", 700)
    assert calls[1] == call("exec", "zai-coding-plan/glm-4.6", 450)


def test_record_usage_zero_tokens(service, monkeypatch):
    """Test that record_usage handles zero token usage correctly."""
    mock_metrics = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.budget.metrics.observe_tokens", mock_metrics)
    
    protocol_id = 1
    step_id = 10
    
    # Record zero usage
    service.record_usage(
        protocol_run_id=protocol_id,
        step_run_id=step_id,
        phase="exec",
        model="gpt-4",
        prompt_tokens=0,
        completion_tokens=0
    )
    
    # Verify cumulative totals updated (even with zero)
    assert service._protocol_token_usage[protocol_id] == 0
    assert service._step_token_usage[step_id] == 0
    
    # Verify metrics recorded
    mock_metrics.assert_called_once_with("exec", "gpt-4", 0)


def test_record_usage_integration_with_check_budget(service, monkeypatch):
    """Test that record_usage works correctly after check_protocol_budget/check_step_budget."""
    mock_metrics = MagicMock()
    monkeypatch.setattr("tasksgodzilla.services.budget.metrics.observe_tokens", mock_metrics)
    
    protocol_id = 1
    step_id = 10
    
    # Check budget first (estimates)
    service.check_protocol_budget(
        protocol_run_id=protocol_id,
        estimated_tokens=200,
        max_protocol_tokens=1000,
        budget_mode="strict"
    )
    
    service.check_step_budget(
        step_run_id=step_id,
        estimated_tokens=200,
        max_step_tokens=500,
        budget_mode="strict"
    )
    
    # Now record actual usage (which might differ from estimate)
    service.record_usage(
        protocol_run_id=protocol_id,
        step_run_id=step_id,
        phase="exec",
        model="gpt-4",
        prompt_tokens=100,
        completion_tokens=50
    )
    
    # Verify cumulative totals reflect both check and record
    # check_protocol_budget added 200, record_usage added 150
    assert service._protocol_token_usage[protocol_id] == 350
    # check_step_budget added 200, record_usage added 150
    assert service._step_token_usage[step_id] == 350

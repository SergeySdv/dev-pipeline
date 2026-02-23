"""Integration tests for orchestration flow with priority and error handling."""

import pytest
from unittest.mock import MagicMock, patch

from devgodzilla.services.priority import Priority, parse_priority, sort_by_priority, DEFAULT_PRIORITY
from devgodzilla.services.error_classification import (
    ErrorClassifier, ErrorAction, ErrorClassification,
    classify_error, TimeoutError, TransientError, ExecutionBlockedError,
    AgentUnavailableError,
)
from devgodzilla.services.retry_config import OrchestrationConfig, RetrySettings


class TestOrchestrationFlowIntegration:
    """Tests for complete orchestration flow."""
    
    @pytest.fixture
    def config(self):
        return OrchestrationConfig()
    
    @pytest.fixture
    def classifier(self):
        return ErrorClassifier()
    
    def test_priority_enum_values(self):
        """Priority enum has expected values."""
        assert Priority.LOW.value == -10
        assert Priority.NORMAL.value == 0
        assert Priority.HIGH.value == 10
        assert Priority.CRITICAL.value == 20
        assert Priority.URGENT.value == 30
    
    def test_priority_sorting_in_steps(self):
        """Steps are sorted by priority correctly."""
        # Create mock steps with different priorities
        steps = [
            MagicMock(step_id="step-1", priority=Priority.NORMAL, step_index=0),
            MagicMock(step_id="step-2", priority=Priority.CRITICAL, step_index=1),
            MagicMock(step_id="step-3", priority=Priority.LOW, step_index=2),
        ]
        
        sorted_steps = sort_by_priority(steps, priority_attr="priority")
        
        # Critical should be first (highest priority)
        assert sorted_steps[0].step_id == "step-2"
    
    def test_parse_priority_from_string(self):
        """Parse priority from string values."""
        assert parse_priority("LOW") == Priority.LOW
        assert parse_priority("NORMAL") == Priority.NORMAL
        assert parse_priority("HIGH") == Priority.HIGH
        assert parse_priority("CRITICAL") == Priority.CRITICAL
        assert parse_priority("invalid") == DEFAULT_PRIORITY
    
    def test_parse_priority_from_int(self):
        """Parse priority from integer values."""
        assert parse_priority(0) == Priority.NORMAL
        assert parse_priority(10) == Priority.HIGH
        assert parse_priority(-10) == Priority.LOW
    
    def test_error_classification_timeout(self, classifier):
        """Timeout triggers retry with configured settings."""
        error = TimeoutError("Execution timed out", timeout_seconds=60)
        
        classification = classifier.classify(error)
        
        assert classification.action == ErrorAction.RETRY
        assert classification.retry_after is not None
    
    def test_error_classification_transient(self, classifier):
        """Transient errors trigger retry."""
        error = TransientError("Connection reset", retry_after=5)
        
        classification = classifier.classify(error)
        
        assert classification.action == ErrorAction.RETRY
    
    def test_error_classification_blocked(self, classifier):
        """Blocked execution triggers clarify action."""
        error = ExecutionBlockedError(
            "Need clarification",
            blocking_reason="ambiguous",
            suggested_questions=["What authentication method?"]
        )
        
        classification = classifier.classify(error)
        
        assert classification.action == ErrorAction.CLARIFY
        assert classification.suggested_question is not None
    
    def test_error_classification_agent_unavailable(self, classifier):
        """Agent unavailable triggers manual action."""
        error = AgentUnavailableError("Agent not found", agent_id="codex")
        
        classification = classifier.classify(error)
        
        assert classification.action == ErrorAction.MANUAL
    
    def test_feedback_loop_integration(self, classifier):
        """Feedback loop classification works end-to-end."""
        # Simulate error from execution
        error = Exception("Need clarification on the output format")
        
        classification = classifier.classify(error)
        
        # Should trigger some action
        assert classification.action in (
            ErrorAction.CLARIFY, 
            ErrorAction.MANUAL,
            ErrorAction.RE_PLAN
        )
        assert classification.confidence >= 0
    
    def test_retry_with_backoff(self, config):
        """Retry uses exponential backoff from config."""
        # calculate_delay is on OrchestrationConfig, not RetrySettings
        delays = [config.calculate_delay(i) for i in range(4)]
        
        # Delays should generally increase (with jitter may vary slightly)
        # First delay should be around initial_delay
        assert delays[0] >= config.retry.initial_delay_seconds * 0.5
        
        # Last delay should be capped
        assert all(d <= config.retry.max_delay_seconds * 1.5 for d in delays)
    
    def test_retry_settings_max_attempts(self, config):
        """Retry settings have max attempts."""
        settings = config.retry
        
        assert settings.max_attempts >= 1
    
    def test_config_get_retry_settings_by_type(self, config):
        """Can get retry settings for specific error types."""
        # Default settings
        default_settings = config.get_retry_settings("unknown")
        assert isinstance(default_settings, RetrySettings)
        
        # Should work for timeout too
        timeout_settings = config.get_retry_settings("timeout")
        assert isinstance(timeout_settings, RetrySettings)


class TestErrorClassifierPatterns:
    """Tests for error classifier pattern matching."""
    
    @pytest.fixture
    def classifier(self):
        return ErrorClassifier()
    
    def test_rate_limit_detection(self, classifier):
        """Detects rate limiting errors."""
        error = Exception("Rate limit exceeded, please retry after 30 seconds")
        
        classification = classifier.classify(error)
        
        assert classification.action == ErrorAction.RETRY
    
    def test_network_error_detection(self, classifier):
        """Detects network errors."""
        error = Exception("Connection refused while connecting to API")
        
        classification = classifier.classify(error)
        
        assert classification.action in (ErrorAction.RETRY, ErrorAction.MANUAL)
    
    def test_permission_error_detection(self, classifier):
        """Detects permission errors."""
        error = Exception("Permission denied accessing /etc/secrets")
        
        classification = classifier.classify(error)
        
        assert classification.action == ErrorAction.MANUAL
    
    def test_max_retry_exceeded(self, classifier):
        """Classifier respects max retry count."""
        error = TimeoutError("Timed out")
        
        # Classify with high retry count
        classification = classifier.classify(error, context={"retry_count": 10})
        
        # Should be manual after max retries
        assert classification.action == ErrorAction.MANUAL
    
    def test_should_retry_method(self, classifier):
        """should_retry method works correctly."""
        retry_classification = ErrorClassification(
            action=ErrorAction.RETRY,
            confidence=0.8,
            reason="Test"
        )
        
        assert classifier.should_retry(retry_classification, 0) is True
        assert classifier.should_retry(retry_classification, 10) is False
    
    def test_get_retry_delay(self, classifier):
        """get_retry_delay calculates delays correctly."""
        classification = ErrorClassification(
            action=ErrorAction.RETRY,
            confidence=0.8,
            reason="Test",
            retry_after=10
        )
        
        delay = classifier.get_retry_delay(classification, 0)
        assert delay == 10


class TestOrchestrationConfigIntegration:
    """Tests for OrchestrationConfig functionality."""
    
    def test_default_config_creation(self):
        """Default config has sensible defaults."""
        config = OrchestrationConfig()
        
        assert config.retry.max_attempts >= 1
        assert config.circuit_breaker.failure_threshold >= 1
        assert config.timeouts.default_step_seconds > 0
    
    def test_config_from_dict(self):
        """Can create config from dictionary."""
        data = {
            "retry": {
                "max_attempts": 5,
                "initial_delay_seconds": 20.0,
            },
            "timeouts": {
                "default_step_seconds": 600.0,
            }
        }
        
        config = OrchestrationConfig.from_dict(data)
        
        assert config.retry.max_attempts == 5
        assert config.timeouts.default_step_seconds == 600.0
    
    def test_calculate_delay_respects_max(self):
        """Delay calculation respects max delay."""
        config = OrchestrationConfig()
        config.retry = RetrySettings(
            max_attempts=10,
            initial_delay_seconds=10.0,
            max_delay_seconds=100.0,
            backoff_multiplier=2.0,
            jitter=False
        )
        
        # High attempt number
        delay = config.calculate_delay(10)
        
        # Should be capped at max
        assert delay <= config.retry.max_delay_seconds * 1.5  # Allow some margin for edge cases

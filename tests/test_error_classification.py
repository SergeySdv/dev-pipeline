"""Tests for ErrorClassification service."""

import pytest
from devgodzilla.services.error_classification import (
    ErrorClassifier, ErrorClassification, ErrorAction,
    AgentUnavailableError, ExecutionBlockedError, TimeoutError,
    TransientError, classify_error, get_classifier
)


class TestErrorTypes:
    def test_agent_unavailable_error_creation(self):
        """AgentUnavailableError can be created."""
        error = AgentUnavailableError("Agent codex not found", agent_id="codex")
        assert str(error) == "Agent codex not found"
        assert error.agent_id == "codex"
        assert error.retryable is False
    
    def test_execution_blocked_error_creation(self):
        """ExecutionBlockedError can be created."""
        error = ExecutionBlockedError(
            "Need clarification",
            blocking_reason="ambiguous requirements",
            suggested_questions=["What did you mean?"],
            options=["Option A", "Option B"]
        )
        assert error.blocking_reason == "ambiguous requirements"
        assert len(error.suggested_questions) == 1
        assert len(error.options) == 2
    
    def test_timeout_error_creation(self):
        """TimeoutError can be created."""
        error = TimeoutError("Step timed out", timeout_seconds=300, step_id=123)
        assert error.timeout_seconds == 300
        assert error.step_id == 123
        assert error.retryable is True
    
    def test_transient_error_creation(self):
        """TransientError can be created."""
        error = TransientError(
            "Network error",
            retry_after=5,
            is_rate_limit=True
        )
        assert error.retry_after == 5
        assert error.is_rate_limit is True
        assert error.retryable is True
    
    def test_all_error_types_exist(self):
        """All error types can be instantiated."""
        AgentUnavailableError("test")
        ExecutionBlockedError("blocked")
        TimeoutError("timed out")
        TransientError("transient")


class TestErrorClassification:
    def test_error_classification_creation(self):
        """ErrorClassification can be created."""
        classification = ErrorClassification(
            action=ErrorAction.RETRY,
            confidence=0.9,
            reason="Network error"
        )
        assert classification.action == ErrorAction.RETRY
        assert classification.confidence == 0.9
        assert classification.reason == "Network error"
    
    def test_error_classification_with_metadata(self):
        """ErrorClassification can have metadata."""
        classification = ErrorClassification(
            action=ErrorAction.CLARIFY,
            confidence=0.8,
            reason="Ambiguous request",
            suggested_question="What did you mean?",
            options=["A", "B"],
            metadata={"key": "value"}
        )
        assert classification.suggested_question == "What did you mean?"
        assert classification.options == ["A", "B"]
        assert classification.metadata == {"key": "value"}


class TestErrorClassifier:
    @pytest.fixture
    def classifier(self):
        return ErrorClassifier()
    
    def test_classify_agent_unavailable(self, classifier):
        """AgentUnavailableError gets correct classification."""
        error = AgentUnavailableError("codex", agent_id="codex")
        result = classifier.classify(error)
        
        assert result.action == ErrorAction.MANUAL
        assert result.confidence > 0
    
    def test_classify_timeout(self, classifier):
        """TimeoutError gets retry classification."""
        error = TimeoutError("Step timed out after 300s")
        result = classifier.classify(error)
        
        assert result.action == ErrorAction.RETRY
        assert result.retry_after is not None
    
    def test_classify_transient(self, classifier):
        """TransientError gets retry classification."""
        error = TransientError("Network connection lost")
        result = classifier.classify(error)
        
        assert result.action == ErrorAction.RETRY
    
    def test_classify_blocked(self, classifier):
        """ExecutionBlockedError gets clarify classification."""
        error = ExecutionBlockedError("Need clarification on requirements")
        result = classifier.classify(error)
        
        assert result.action == ErrorAction.CLARIFY
    
    def test_classify_pattern_matching(self, classifier):
        """Pattern matching works for generic exceptions."""
        error = Exception("The request is ambiguous")
        result = classifier.classify(error)
        
        # Should match "ambiguous" pattern
        assert result.action == ErrorAction.CLARIFY
    
    def test_classify_rate_limit_pattern(self, classifier):
        """Rate limit pattern is detected."""
        error = Exception("rate limit exceeded")
        result = classifier.classify(error)
        
        assert result.action == ErrorAction.RETRY
    
    def test_classify_network_pattern(self, classifier):
        """Network error pattern is detected."""
        error = Exception("connection refused")
        result = classifier.classify(error)
        
        assert result.action == ErrorAction.RETRY
    
    def test_classify_with_context(self, classifier):
        """Classification uses context for retry count."""
        error = TimeoutError("timed out")
        
        # First retry
        result1 = classifier.classify(error, context={"retry_count": 0})
        assert result1.action == ErrorAction.RETRY
        
        # Max retries exceeded
        result2 = classifier.classify(error, context={"retry_count": 3})
        assert result2.action == ErrorAction.MANUAL
    
    def test_should_retry(self, classifier):
        """should_retry method works correctly."""
        classification = ErrorClassification(
            action=ErrorAction.RETRY,
            confidence=0.9,
            reason="test"
        )
        
        assert classifier.should_retry(classification, 0) is True
        assert classifier.should_retry(classification, 2) is True
        assert classifier.should_retry(classification, 3) is False
    
    def test_get_retry_delay(self, classifier):
        """get_retry_delay returns correct values."""
        classification = ErrorClassification(
            action=ErrorAction.RETRY,
            confidence=0.9,
            reason="test",
            retry_after=10
        )
        
        assert classifier.get_retry_delay(classification, 0) == 10
        
        # Without retry_after, uses exponential backoff
        classification2 = ErrorClassification(
            action=ErrorAction.RETRY,
            confidence=0.9,
            reason="test"
        )
        delay = classifier.get_retry_delay(classification2, 0)
        assert delay > 0


class TestErrorActionEnum:
    def test_error_action_values(self):
        """ErrorAction enum has expected values."""
        assert ErrorAction.CLARIFY.value == "clarify"
        assert ErrorAction.RE_PLAN.value == "re_plan"
        assert ErrorAction.RETRY.value == "retry"
        assert ErrorAction.MANUAL.value == "manual"


class TestConvenienceFunctions:
    def test_classify_error_function(self):
        """classify_error convenience function works."""
        error = TimeoutError("timed out")
        result = classify_error(error)
        
        assert isinstance(result, ErrorClassification)
        assert result.action == ErrorAction.RETRY
    
    def test_get_classifier_singleton(self):
        """get_classifier returns singleton instance."""
        c1 = get_classifier()
        c2 = get_classifier()
        assert c1 is c2

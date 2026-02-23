"""
DevGodzilla Error Classification Service

Classifies errors during orchestration and suggests appropriate actions.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from devgodzilla.errors import (
    DevGodzillaError,
    EngineError,
    EngineNotFoundError,
    OrchestrationError,
    QAGateFailed,
    SpecificationError,
    ValidationError,
    WindmillError,
)
from devgodzilla.logging import get_logger

logger = get_logger(__name__)


# Additional Error Types for Classification

class AgentUnavailableError(OrchestrationError):
    """
    Raised when a requested agent/engine is not available.
    
    This can happen when:
    - The agent configuration is missing
    - The agent is disabled
    - The agent binary is not installed
    - The agent API is unreachable
    """
    category = "orchestration"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, metadata=metadata, retryable=False)
        self.agent_id = agent_id


class ExecutionBlockedError(OrchestrationError):
    """
    Raised when execution needs clarification before proceeding.
    
    This indicates the agent cannot proceed without additional input
    from the user or clarification of requirements.
    """
    category = "orchestration"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        blocking_reason: Optional[str] = None,
        suggested_questions: Optional[List[str]] = None,
        options: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, metadata=metadata, retryable=False)
        self.blocking_reason = blocking_reason
        self.suggested_questions = suggested_questions or []
        self.options = options or []


class TimeoutError(OrchestrationError):
    """
    Raised when step execution times out.
    
    This can indicate:
    - The agent took too long
    - Network issues
    - Resource constraints
    """
    category = "orchestration"
    retryable = True

    def __init__(
        self,
        message: str,
        *,
        timeout_seconds: Optional[int] = None,
        step_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, metadata=metadata, retryable=True)
        self.timeout_seconds = timeout_seconds
        self.step_id = step_id


class TransientError(OrchestrationError):
    """
    Raised for recoverable errors that can be retried.
    
    Examples:
    - Network timeouts
    - Rate limiting
    - Temporary resource unavailability
    """
    category = "orchestration"
    retryable = True

    def __init__(
        self,
        message: str,
        *,
        retry_after: Optional[int] = None,
        is_rate_limit: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message, metadata=metadata, retryable=True)
        self.retry_after = retry_after
        self.is_rate_limit = is_rate_limit


class ErrorAction(str, Enum):
    """Action to take for a classified error."""
    CLARIFY = "clarify"        # Request clarification from user
    RE_PLAN = "re_plan"        # Re-plan the step/protocol
    RE_SPECIFY = "re_specify"  # Re-specify requirements
    RETRY = "retry"            # Retry the operation
    MANUAL = "manual"          # Requires manual intervention


@dataclass
class ErrorClassification:
    """
    Classification result for an error.
    
    Provides recommended action and context for handling the error.
    """
    action: ErrorAction
    confidence: float  # 0.0 to 1.0
    reason: str
    suggested_question: Optional[str] = None
    options: Optional[List[str]] = None
    retry_after: Optional[int] = None  # Seconds to wait before retry
    metadata: Dict[str, Any] = field(default_factory=dict)


# Additional patterns for extended classification
_EXTENDED_PATTERNS: List[Tuple[re.Pattern, ErrorAction, str]] = [
    # Rate limiting patterns
    (re.compile(r"rate limit|too many requests|429|quota exceeded", re.IGNORECASE),
     ErrorAction.RETRY, "Rate limited by API"),
    
    # Network patterns
    (re.compile(r"connection refused|network unreachable|dns failed|socket error", re.IGNORECASE),
     ErrorAction.RETRY, "Network connectivity issue"),
    
    # Planning patterns
    (re.compile(r"circular.*dependency|cycle detected|dependency.*conflict", re.IGNORECASE),
     ErrorAction.RE_PLAN, "Dependency issue in plan"),
    
    (re.compile(r"invalid.*plan|plan.*failed|cannot.*execute.*plan", re.IGNORECASE),
     ErrorAction.RE_PLAN, "Plan execution failed"),
    
    # Agent unavailable patterns
    (re.compile(r"agent.*not.*available|engine.*not.*found|not.*installed|binary.*not.*found", re.IGNORECASE),
     ErrorAction.MANUAL, "Agent/engine unavailable"),
    
    # Permission/auth patterns
    (re.compile(r"permission denied|unauthorized|forbidden|403|401|authentication", re.IGNORECASE),
     ErrorAction.MANUAL, "Authentication/permission issue"),
    
    # Resource patterns
    (re.compile(r"out of memory|disk.*full|resource.*exhausted", re.IGNORECASE),
     ErrorAction.MANUAL, "Resource exhaustion"),
    
    # Configuration patterns
    (re.compile(r"config.*error|missing.*config|invalid.*config", re.IGNORECASE),
     ErrorAction.MANUAL, "Configuration error"),
]


@dataclass
class ErrorClassifier:
    """
    Classifies errors and suggests remediation actions.
    
    Uses pattern matching on error messages and error type inspection
    to determine the best course of action.
    
    Example:
        classifier = ErrorClassifier()
        
        try:
            # ... execute step ...
            pass
        except Exception as e:
            classification = classifier.classify(e, context={
                "step_id": step.id,
                "agent_id": "opencode",
            })
            
            if classification.action == ErrorAction.RETRY:
                # Retry after delay
                await asyncio.sleep(classification.retry_after or 5)
                # ... retry ...
            elif classification.action == ErrorAction.CLARIFY:
                # Ask user for clarification
                question = classification.suggested_question
    """
    
    action_patterns: Dict[str, List[str]] = field(default_factory=lambda: {
        "clarify": [
            "ambiguous", "unclear", "missing information",
            "need.*clarification", "which.*should"
        ],
        "re_plan": [
            "wrong approach", "architecture.*issue",
            "dependency.*conflict", "incompatible"
        ],
        "re_specify": [
            "impossible", "contradictory",
            "invalid requirement", "cannot.*satisfy"
        ],
        "retry": [
            "timeout", "transient", "network.*error",
            "rate.*limit", "connection.*reset"
        ],
    })
    
    max_retry_count: int = 3
    default_retry_after: int = 5
    
    _compiled_patterns: Dict[str, List] = field(default_factory=dict, repr=False)
    
    def __post_init__(self) -> None:
        """Initialize compiled patterns after dataclass creation."""
        self._compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List]:
        """Pre-compile regex patterns for performance."""
        return {
            action: [re.compile(p, re.IGNORECASE) for p in patterns]
            for action, patterns in self.action_patterns.items()
        }
    
    def classify(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> ErrorClassification:
        """
        Classify an error and suggest action.
        
        Args:
            error: The exception to classify
            context: Optional context (step_id, retry_count, agent_id, etc.)
            
        Returns:
            ErrorClassification with recommended action
        """
        context = context or {}
        retry_count = context.get("retry_count", 0)
        
        # First check if this is a known error type
        type_classification = self._classify_by_type(error, context)
        if type_classification:
            return type_classification
        
        # Extract searchable text from error and context
        error_text = self._extract_error_text(error, context)
        
        # Try pattern matching on error message
        for action, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(error_text):
                    return ErrorClassification(
                        action=ErrorAction(action),
                        confidence=0.8,
                        reason=f"Matched pattern: {pattern.pattern}",
                        metadata={"pattern_matched": pattern.pattern},
                    )
        
        # Try extended patterns
        for pattern, action, reason in _EXTENDED_PATTERNS:
            if pattern.search(error_text):
                if action == ErrorAction.RETRY and retry_count >= self.max_retry_count:
                    return ErrorClassification(
                        action=ErrorAction.MANUAL,
                        confidence=0.6,
                        reason=f"{reason} (max retries exceeded)",
                        suggested_question="The operation failed multiple times. Would you like to try a different approach?",
                        metadata={"pattern_matched": pattern.pattern},
                    )
                return ErrorClassification(
                    action=action,
                    confidence=0.7,
                    reason=reason,
                    retry_after=self.default_retry_after if action == ErrorAction.RETRY else None,
                    metadata={"pattern_matched": pattern.pattern},
                )
        
        # Check error metadata for hints
        if isinstance(error, DevGodzillaError):
            meta_classification = self._classify_by_metadata(error, context)
            if meta_classification:
                return meta_classification
        
        # Default classification
        return ErrorClassification(
            action=self._default_action(error),
            confidence=0.5,
            reason="No specific pattern matched",
            metadata={"error_type": type(error).__name__},
        )
    
    def _extract_error_text(self, error: Exception, context: Optional[Dict]) -> str:
        """Extract searchable text from error and context."""
        parts = [str(error), type(error).__name__]
        if context:
            parts.extend(str(v) for v in context.values() if isinstance(v, str))
        return " ".join(parts)
    
    def _default_action(self, error: Exception) -> ErrorAction:
        """Determine default action based on error type."""
        if isinstance(error, TimeoutError):
            return ErrorAction.RETRY
        elif isinstance(error, AgentUnavailableError):
            return ErrorAction.CLARIFY
        elif isinstance(error, SpecificationError):
            return ErrorAction.RE_SPECIFY
        else:
            return ErrorAction.MANUAL

    def _classify_by_type(
        self,
        error: Exception,
        context: Dict[str, Any],
    ) -> Optional[ErrorClassification]:
        """Classify based on error type."""
        retry_count = context.get("retry_count", 0)
        
        # Specification errors
        if isinstance(error, SpecificationError):
            action_map = {
                "clarify": ErrorAction.CLARIFY,
                "re_plan": ErrorAction.RE_PLAN,
                "re_specify": ErrorAction.RE_SPECIFY,
            }
            action = action_map.get(error.action, ErrorAction.CLARIFY)
            return ErrorClassification(
                action=action,
                confidence=0.9,
                reason=f"Specification error (action={error.action})",
                metadata={"step_id": error.step_id, "spec_action": error.action},
            )
        
        # Agent unavailable
        if isinstance(error, AgentUnavailableError):
            return ErrorClassification(
                action=ErrorAction.MANUAL,
                confidence=0.95,
                reason=f"Agent '{error.agent_id}' is not available",
                suggested_question=f"The agent '{error.agent_id}' is not available. Would you like to use a different agent?",
                metadata={"agent_id": error.agent_id},
            )
        
        # Engine not found
        if isinstance(error, EngineNotFoundError):
            return ErrorClassification(
                action=ErrorAction.MANUAL,
                confidence=0.95,
                reason="Requested engine is not registered",
                suggested_question="The requested engine is not available. Would you like to configure or select a different engine?",
                metadata={},
            )
        
        # Execution blocked
        if isinstance(error, ExecutionBlockedError):
            return ErrorClassification(
                action=ErrorAction.CLARIFY,
                confidence=0.9,
                reason=error.blocking_reason or "Execution is blocked",
                suggested_question=error.suggested_questions[0] if error.suggested_questions else None,
                options=error.options,
                metadata={"blocking_reason": error.blocking_reason},
            )
        
        # Timeout
        if isinstance(error, TimeoutError):
            if retry_count >= self.max_retry_count:
                return ErrorClassification(
                    action=ErrorAction.MANUAL,
                    confidence=0.8,
                    reason=f"Operation timed out after {retry_count} retries",
                    suggested_question="The operation keeps timing out. Would you like to increase the timeout or try a different approach?",
                    metadata={"timeout_seconds": error.timeout_seconds, "retries": retry_count},
                )
            return ErrorClassification(
                action=ErrorAction.RETRY,
                confidence=0.85,
                reason=f"Operation timed out (retry {retry_count + 1}/{self.max_retry_count})",
                retry_after=min(self.default_retry_after * (2 ** retry_count), 60),  # Exponential backoff, max 60s
                metadata={"timeout_seconds": error.timeout_seconds},
            )
        
        # Transient error
        if isinstance(error, TransientError):
            if retry_count >= self.max_retry_count:
                return ErrorClassification(
                    action=ErrorAction.MANUAL,
                    confidence=0.7,
                    reason=f"Transient error persisted after {retry_count} retries",
                    metadata={"is_rate_limit": error.is_rate_limit, "retries": retry_count},
                )
            retry_after = error.retry_after or self.default_retry_after
            if error.is_rate_limit:
                retry_after = max(retry_after, 30)  # At least 30s for rate limits
            return ErrorClassification(
                action=ErrorAction.RETRY,
                confidence=0.85,
                reason="Transient error - retry recommended",
                retry_after=retry_after,
                metadata={"is_rate_limit": error.is_rate_limit},
            )
        
        # QA gate failure
        if isinstance(error, QAGateFailed):
            return ErrorClassification(
                action=ErrorAction.RETRY,
                confidence=0.75,
                reason="QA gate check failed - may be auto-fixable",
                suggested_question="Quality checks failed. Would you like to attempt an automatic fix?",
                metadata={},
            )
        
        # Validation errors
        if isinstance(error, ValidationError):
            return ErrorClassification(
                action=ErrorAction.RE_SPECIFY,
                confidence=0.8,
                reason="Validation failed - requirements may need adjustment",
                suggested_question="The implementation doesn't meet validation requirements. Would you like to adjust the specification?",
                metadata={},
            )
        
        # Windmill errors
        if isinstance(error, WindmillError):
            if retry_count < self.max_retry_count:
                return ErrorClassification(
                    action=ErrorAction.RETRY,
                    confidence=0.7,
                    reason="Windmill execution failed - transient issue possible",
                    retry_after=self.default_retry_after,
                    metadata={},
                )
            return ErrorClassification(
                action=ErrorAction.MANUAL,
                confidence=0.7,
                reason="Windmill execution failed after retries",
                metadata={},
            )
        
        # Engine errors
        if isinstance(error, EngineError):
            return ErrorClassification(
                action=ErrorAction.RETRY,
                confidence=0.6,
                reason="Engine execution failed",
                retry_after=self.default_retry_after,
                metadata={"category": error.category},
            )
        
        return None

    def _classify_by_metadata(
        self,
        error: DevGodzillaError,
        context: Dict[str, Any],
    ) -> Optional[ErrorClassification]:
        """Classify based on error metadata."""
        metadata = error.metadata or {}
        retry_count = context.get("retry_count", 0)
        
        # Check for timeout flag
        if metadata.get("timeout"):
            if retry_count >= self.max_retry_count:
                return ErrorClassification(
                    action=ErrorAction.MANUAL,
                    confidence=0.8,
                    reason="Operation timed out after retries",
                    metadata={"from_metadata": True},
                )
            return ErrorClassification(
                action=ErrorAction.RETRY,
                confidence=0.8,
                reason="Operation timed out",
                retry_after=self.default_retry_after,
                metadata={"from_metadata": True},
            )
        
        # Check retryable flag
        if not error.retryable:
            return ErrorClassification(
                action=ErrorAction.MANUAL,
                confidence=0.85,
                reason="Error is not retryable",
                metadata={"from_metadata": True},
            )
        
        return None

    def should_retry(
        self,
        classification: ErrorClassification,
        retry_count: int,
    ) -> bool:
        """Determine if the error should be retried."""
        if classification.action != ErrorAction.RETRY:
            return False
        return retry_count < self.max_retry_count

    def get_retry_delay(
        self,
        classification: ErrorClassification,
        retry_count: int,
    ) -> int:
        """Get the delay before retry in seconds."""
        if classification.retry_after:
            return classification.retry_after
        # Exponential backoff
        return min(self.default_retry_after * (2 ** retry_count), 60)


# Singleton instance
_classifier_instance: Optional[ErrorClassifier] = None


def get_classifier() -> ErrorClassifier:
    """Get the singleton ErrorClassifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ErrorClassifier()
    return _classifier_instance


# Backward-compatible alias
get_error_classifier = get_classifier


def classify_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> ErrorClassification:
    """
    Classify an error (backward-compatible function).
    
    Args:
        error: The exception to classify
        context: Optional context dictionary
        
    Returns:
        ErrorClassification with recommended action
    """
    return get_classifier().classify(error, context)

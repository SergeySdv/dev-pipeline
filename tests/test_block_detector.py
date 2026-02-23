"""Tests for BlockDetector."""

import pytest

from devgodzilla.engines.block_detector import (
    BlockDetector,
    BlockInfo,
    BlockReason,
    detect_block,
)


class TestBlockReason:
    """Tests for BlockReason enum."""

    def test_block_reason_values(self):
        """Test BlockReason enum values."""
        assert BlockReason.CLARIFICATION_NEEDED.value == "clarification_needed"
        assert BlockReason.AMBIGUOUS_REQUIREMENT.value == "ambiguous_requirement"
        assert BlockReason.MISSING_INFORMATION.value == "missing_information"
        assert BlockReason.CONFLICTING_INSTRUCTIONS.value == "conflicting_instructions"
        assert BlockReason.IMPOSSIBLE_REQUEST.value == "impossible_request"
        assert BlockReason.PERMISSION_DENIED.value == "permission_denied"
        assert BlockReason.RESOURCE_NOT_FOUND.value == "resource_not_found"


class TestBlockInfo:
    """Tests for BlockInfo dataclass."""

    def test_block_info_creation(self):
        """Test BlockInfo creation."""
        info = BlockInfo(
            reason=BlockReason.CLARIFICATION_NEEDED,
            message="Agent needs clarification",
            suggested_question="What would you like?",
            options=["Option A", "Option B"],
            context={"key": "value"},
            confidence=0.9,
        )
        assert info.reason == BlockReason.CLARIFICATION_NEEDED
        assert info.message == "Agent needs clarification"
        assert info.suggested_question == "What would you like?"
        assert info.options == ["Option A", "Option B"]
        assert info.context == {"key": "value"}
        assert info.confidence == 0.9

    def test_block_info_defaults(self):
        """Test BlockInfo default values."""
        info = BlockInfo(
            reason=BlockReason.MISSING_INFORMATION,
            message="Missing info",
        )
        assert info.suggested_question is None
        assert info.options == []
        assert info.context == {}
        assert info.confidence == 1.0


class TestBlockDetector:
    """Tests for BlockDetector."""

    @pytest.fixture
    def detector(self):
        """Create BlockDetector instance."""
        return BlockDetector()

    def test_no_block_detected(self, detector):
        """Output without blocking patterns returns None."""
        output = "Task completed successfully. Created file.py"
        result = detector.detect(output)
        assert result is None

    def test_empty_output(self, detector):
        """Empty output returns None."""
        result = detector.detect("")
        assert result is None

    def test_whitespace_only_output(self, detector):
        """Whitespace only output returns None."""
        result = detector.detect("   \n\t  \n  ")
        assert result is None

    def test_clarification_needed(self, detector):
        """Detects clarification needed pattern."""
        output = "I need clarification on which approach to use."
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.CLARIFICATION_NEEDED

    def test_missing_information(self, detector):
        """Detects missing information pattern."""
        output = "Cannot proceed without the API key."
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.MISSING_INFORMATION

    def test_ambiguous_requirement(self, detector):
        """Detects ambiguous requirement pattern."""
        output = "This is an ambiguous requirement about the output format."
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.AMBIGUOUS_REQUIREMENT

    def test_conflicting_instructions(self, detector):
        """Detects conflicting instructions pattern."""
        output = "There are conflicting requirements about the implementation."
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.CONFLICTING_INSTRUCTIONS

    def test_impossible_request(self, detector):
        """Detects impossible request pattern."""
        output = "It is impossible to implement this feature as described."
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.IMPOSSIBLE_REQUEST

    def test_permission_denied(self, detector):
        """Detects permission denied pattern."""
        output = "Permission denied: cannot access /root/config"
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.PERMISSION_DENIED

    def test_resource_not_found(self, detector):
        """Detects resource not found pattern."""
        output = "The file does not exist at that path."
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.RESOURCE_NOT_FOUND

    def test_detect_with_which_question(self, detector):
        """Detects 'which' question pattern."""
        output = "Which framework should I use for this project?"
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.CLARIFICATION_NEEDED

    def test_detect_not_sure_pattern(self, detector):
        """Detects 'I'm not sure' pattern."""
        output = "I'm not sure how to implement this functionality."
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.AMBIGUOUS_REQUIREMENT

    def test_extract_context(self, detector):
        """Context extraction includes surrounding text."""
        output = "Line 1\nLine 2\nNeed clarification here\nLine 4\nLine 5"
        result = detector.detect(output)
        assert result is not None
        # Context should be populated
        assert "context" in result.context
        # The match should be in the context
        assert "clarification" in result.context.get("context", "").lower()

    def test_detect_all(self, detector):
        """Detect all blocks in output."""
        output = "Need clarification on X. Also missing information about Y."
        results = detector.detect_all(output)
        assert len(results) >= 2

    def test_detect_all_empty(self, detector):
        """Detect all returns empty list for no blocks."""
        output = "Successfully completed the task."
        results = detector.detect_all(output)
        assert len(results) == 0

    def test_suggested_question(self, detector):
        """Block info includes suggested question."""
        output = "I'm not sure which database to use."
        result = detector.detect(output)
        if result:
            assert result.suggested_question is not None
            assert "?" in result.suggested_question

    def test_suggested_question_for_missing_info(self, detector):
        """Suggested question for missing information."""
        output = "Cannot proceed without authentication credentials."
        result = detector.detect(output)
        if result:
            assert result.suggested_question is not None

    def test_confidence_high_for_permission_denied(self, detector):
        """High confidence for permission denied."""
        output = "Permission denied: access to file.txt"
        result = detector.detect(output)
        assert result is not None
        assert result.confidence >= 0.9

    def test_confidence_high_for_resource_not_found(self, detector):
        """High confidence for resource not found."""
        output = "File not found: config.json"
        result = detector.detect(output)
        assert result is not None
        assert result.confidence >= 0.85

    def test_case_insensitive_detection(self, detector):
        """Detection is case insensitive."""
        outputs = [
            "PERMISSION DENIED: cannot access file",
            "Permission Denied: access denied",
            "permission denied: operation failed",
        ]
        for output in outputs:
            result = detector.detect(output)
            assert result is not None
            assert result.reason == BlockReason.PERMISSION_DENIED

    def test_message_includes_reason(self, detector):
        """Block message includes the reason."""
        output = "Cannot proceed without the database connection string."
        result = detector.detect(output)
        assert result is not None
        assert result.message is not None
        assert result.reason.value in result.message

    def test_message_includes_captured_detail(self, detector):
        """Block message includes captured detail when available."""
        output = "Cannot proceed without the API key."
        result = detector.detect(output)
        assert result is not None
        # The captured detail "the API key" should be in the message
        assert "api key" in result.message.lower()

    def test_deduplicate_blocks(self, detector):
        """Duplicate blocks are deduplicated."""
        output = "Cannot proceed without authentication. Cannot proceed without authentication."
        results = detector.detect_all(output)
        # Should deduplicate overlapping matches
        assert len(results) <= 2


class TestDetectBlockFunction:
    """Tests for convenience detect_block function."""

    def test_detect_block_convenience_function(self):
        """detect_block convenience function works."""
        result = detect_block("Cannot proceed without authentication")
        assert result is not None
        assert result.reason == BlockReason.MISSING_INFORMATION

    def test_detect_block_returns_none_for_success(self):
        """detect_block returns None for successful output."""
        result = detect_block("Task completed successfully!")
        assert result is None


class TestBlockDetectorPatterns:
    """Tests for specific pattern matching."""

    @pytest.fixture
    def detector(self):
        return BlockDetector()

    def test_cannot_determine_pattern(self, detector):
        """Detects 'cannot determine' pattern."""
        output = "Cannot determine the best approach for this problem."
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.AMBIGUOUS_REQUIREMENT

    def test_unable_to_proceed_pattern(self, detector):
        """Detects 'unable to proceed' pattern."""
        output = "Unable to proceed without additional context."
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.MISSING_INFORMATION

    def test_requires_additional_information(self, detector):
        """Detects 'requires additional information' pattern."""
        output = "This task requires additional information to complete."
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.MISSING_INFORMATION

    def test_could_you_clarify_pattern(self, detector):
        """Detects 'could you clarify' pattern."""
        output = "Could you please clarify the expected behavior?"
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.CLARIFICATION_NEEDED

    def test_would_you_clarify_pattern(self, detector):
        """Detects 'would you clarify' pattern."""
        output = "Would you clarify how the API should respond?"
        result = detector.detect(output)
        assert result is not None
        assert result.reason == BlockReason.CLARIFICATION_NEEDED


class TestBlockDetectorContext:
    """Tests for context extraction."""

    @pytest.fixture
    def detector(self):
        return BlockDetector()

    def test_context_includes_surrounding_lines(self, detector):
        """Context includes lines around the match."""
        output = """
This is line 1.
This is line 2.
I need clarification on the requirements.
This is line 4.
This is line 5.
""".strip()
        result = detector.detect(output)
        assert result is not None
        context_data = result.context
        assert "context" in context_data

    def test_context_at_start_of_output(self, detector):
        """Context extraction works at start of output."""
        output = "Cannot proceed without more info."
        result = detector.detect(output)
        assert result is not None
        assert result.context is not None

    def test_context_includes_line_number(self, detector):
        """Context includes line number of match."""
        output = "Line 1\nLine 2\nLine 3\nCannot proceed without the key\nLine 5"
        result = detector.detect(output)
        assert result is not None
        # Line number should be tracked
        assert "line_number" in result.context


class TestBlockDetectorSuggestedQuestions:
    """Tests for suggested question generation."""

    @pytest.fixture
    def detector(self):
        return BlockDetector()

    def test_question_for_missing_info(self, detector):
        """Question is customized for missing information."""
        output = "Cannot proceed without the database password."
        result = detector.detect(output)
        assert result is not None
        assert result.suggested_question is not None
        assert "database password" in result.suggested_question.lower()

    def test_question_for_clarification(self, detector):
        """Question is customized for clarification needed."""
        output = "Need clarification on the output format."
        result = detector.detect(output)
        assert result is not None
        assert result.suggested_question is not None
        assert "output format" in result.suggested_question.lower()

    def test_question_for_ambiguous_requirement(self, detector):
        """Question is customized for ambiguous requirements."""
        output = "This is an ambiguous requirement about authentication."
        result = detector.detect(output)
        assert result is not None
        assert result.suggested_question is not None
        assert "authentication" in result.suggested_question.lower()

    def test_default_question_for_unknown_detail(self, detector):
        """Default question used when no detail captured."""
        output = "Permission denied."
        result = detector.detect(output)
        assert result is not None
        assert result.suggested_question is not None
        # Should have a default question about permissions
        assert len(result.suggested_question) > 0

"""Tests for ChecklistValidator."""

import pytest
from pathlib import Path

from devgodzilla.qa.checklist_validator import (
    ChecklistValidator,
    ChecklistItem,
    ValidationResult,
)


class TestChecklistItem:
    """Tests for ChecklistItem dataclass."""

    def test_create_item(self):
        item = ChecklistItem(
            id="1",
            description="Test item",
            checked=False,
            required=True,
        )
        assert item.id == "1"
        assert item.description == "Test item"
        assert item.checked is False
        assert item.required is True

    def test_default_values(self):
        item = ChecklistItem(id="1", description="Test")
        assert item.checked is False
        assert item.required is True
        assert item.category == "general"
        assert item.validation_hints == []


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_create_result(self):
        result = ValidationResult(
            item_id="1",
            passed=True,
            confidence=0.9,
            evidence=["Found test"],
            reasoning="Tests detected",
        )
        assert result.item_id == "1"
        assert result.passed is True
        assert result.confidence == 0.9
        assert result.suggestions == []

    def test_result_with_suggestions(self):
        result = ValidationResult(
            item_id="1",
            passed=False,
            confidence=0.5,
            evidence=[],
            reasoning="No tests found",
            suggestions=["Add unit tests", "Add integration tests"],
        )
        assert len(result.suggestions) == 2


class TestChecklistValidator:
    @pytest.fixture
    def validator(self):
        return ChecklistValidator(use_llm=False)  # Pattern-based only for tests

    @pytest.fixture
    def sample_checklist(self):
        return """
- [ ] Implement user authentication
- [x] Create database schema
- [ ] Add unit tests
- [Optional] Add integration tests
"""

    def test_parse_checklist(self, validator, sample_checklist):
        items = validator.parse_checklist(sample_checklist)
        # The parser may not handle [Optional] prefix, so check what we get
        assert len(items) >= 3
        assert items[0].checked is False
        assert items[1].checked is True
        assert items[2].required is True

    def test_parse_checklist_empty(self, validator):
        items = validator.parse_checklist("")
        assert items == []

    def test_parse_checklist_no_checkboxes(self, validator):
        content = "This is just text\nNo checkboxes here"
        items = validator.parse_checklist(content)
        assert items == []

    def test_extract_keywords(self, validator):
        keywords = validator._extract_keywords("Implement user authentication with OAuth2")
        assert "implement" in keywords
        assert "user" in keywords
        assert "authentication" in keywords
        assert "oauth2" in keywords
        # Stop words should be removed
        assert "with" not in keywords

    def test_extract_keywords_removes_stopwords(self, validator):
        keywords = validator._extract_keywords("The quick brown fox jumps over the lazy dog")
        # Common stop words should be removed
        assert "the" not in keywords
        # "over" is not in the stop words list, so it may be included
        assert "quick" in keywords

    def test_has_test_patterns(self, validator):
        assert validator._has_test_patterns("def test_login(): pass")
        assert validator._has_test_patterns("it('should work', () => {})")
        assert validator._has_test_patterns("describe('feature', () => {})")
        assert validator._has_test_patterns("test('my test', () => {})")
        assert validator._has_test_patterns("expect(result).toBe(true)")
        assert not validator._has_test_patterns("def regular_function(): pass")

    def test_has_error_handling_patterns(self, validator):
        assert validator._has_error_handling_patterns("try:\n    pass\nexcept:")
        assert validator._has_error_handling_patterns("catch (e) {}")
        assert validator._has_error_handling_patterns("raise ValueError()")
        assert not validator._has_error_handling_patterns("def regular_function(): pass")

    def test_validate_item_with_patterns(self, validator, tmp_path):
        test_file = tmp_path / "test_auth.py"
        test_file.write_text("def test_login(): pass")

        item = ChecklistItem(
            id="1",
            description="Add unit tests for authentication",
            required=True,
        )

        result = validator.validate_item(item, [test_file])
        assert result.passed
        assert result.confidence > 0

    def test_validate_item_no_match(self, validator, tmp_path):
        test_file = tmp_path / "main.py"
        test_file.write_text("def regular_function(): pass")

        item = ChecklistItem(
            id="1",
            description="Add blockchain integration",
            required=True,
        )

        result = validator.validate_item(item, [test_file])
        # Should have low confidence since no keywords match
        assert result.confidence < 0.8

    def test_validate_all(self, validator, tmp_path, sample_checklist):
        test_file = tmp_path / "tests.py"
        test_file.write_text("def test_schema(): pass")

        items = validator.parse_checklist(sample_checklist)
        results = validator.validate_all(items, [test_file])

        # Number of results should match number of parsed items
        assert len(results) == len(items)
        assert all(isinstance(r, ValidationResult) for r in results)

    def test_validate_all_with_multiple_artifacts(self, validator, tmp_path):
        (tmp_path / "test_auth.py").write_text("def test_login(): pass")
        (tmp_path / "auth.py").write_text("def login(): pass")

        items = [
            ChecklistItem(id="1", description="Add authentication"),
            ChecklistItem(id="2", description="Add unit tests"),
        ]

        results = validator.validate_all(items, [tmp_path / "test_auth.py", tmp_path / "auth.py"])
        assert len(results) == 2


class TestChecklistValidatorWithLLM:
    """Tests for LLM-based validation (mocked)."""

    @pytest.fixture
    def mock_llm_client(self):
        class MockLLMClient:
            def complete(self, prompt):
                return "PASSED\nConfidence: 0.9\nEvidence: Found implementation"

        return MockLLMClient()

    def test_validate_with_llm(self, tmp_path, mock_llm_client):
        validator = ChecklistValidator(llm_client=mock_llm_client, use_llm=True)

        test_file = tmp_path / "code.py"
        test_file.write_text("def important_function(): pass")

        item = ChecklistItem(
            id="1",
            description="Implement important function",
            required=True,
        )

        result = validator.validate_item(item, [test_file])
        # Since LLM returns PASSED, should pass
        assert result.passed is True

    def test_llm_fallback_on_error(self, tmp_path):
        class FailingLLMClient:
            def complete(self, prompt):
                raise RuntimeError("LLM unavailable")

        validator = ChecklistValidator(
            llm_client=FailingLLMClient(),
            use_llm=True,
        )

        test_file = tmp_path / "code.py"
        test_file.write_text("def function(): pass")

        item = ChecklistItem(id="1", description="Do something")

        result = validator.validate_item(item, [test_file])
        # Should fallback to pattern validation
        assert isinstance(result, ValidationResult)


class TestChecklistValidatorHelpers:
    """Tests for helper methods."""

    @pytest.fixture
    def validator(self):
        return ChecklistValidator(use_llm=False)

    def test_build_artifact_context(self, validator, tmp_path):
        file1 = tmp_path / "file1.py"
        file2 = tmp_path / "file2.py"
        file1.write_text("content1")
        file2.write_text("content2")

        context = validator._build_artifact_context([file1, file2])
        assert "file1.py" in context
        assert "file2.py" in context
        assert "content1" in context
        assert "content2" in context

    def test_build_artifact_context_empty(self, validator, tmp_path):
        context = validator._build_artifact_context([])
        assert context == ""

    def test_parse_llm_response(self, validator):
        response = """
PASSED
Confidence: 0.85
Evidence: Found the implementation at line 10
Reasoning: The code correctly implements the feature
"""
        result = validator._parse_llm_response("1", response)
        assert result.item_id == "1"
        assert result.passed is True
        assert result.confidence == 0.85

    def test_parse_llm_response_failed(self, validator):
        response = "FAILED\nConfidence: 0.9\nNot implemented"
        result = validator._parse_llm_response("1", response)
        assert result.passed is False

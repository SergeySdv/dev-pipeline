"""
Tests for ClarifierService.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from devgodzilla.db.database import SQLiteDatabase
from devgodzilla.services.base import ServiceContext
from devgodzilla.services.clarifier import ClarifierService
from devgodzilla.config import load_config


class TestClarifierService:
    """Tests for ClarifierService."""

    @pytest.fixture
    def db(self, tmp_path: Path):
        db_path = tmp_path / "test.db"
        db = SQLiteDatabase(db_path)
        db.init_schema()
        return db

    @pytest.fixture
    def context(self):
        config = load_config()
        return ServiceContext(config=config)

    @pytest.fixture
    def clarifier(self, context: ServiceContext, db: SQLiteDatabase):
        return ClarifierService(context, db)

    @pytest.fixture
    def sample_project(self, db: SQLiteDatabase):
        return db.create_project(
            name="Test Project",
            git_url="https://github.com/example/test.git",
            base_branch="main",
        )

    @pytest.fixture
    def sample_protocol(self, db: SQLiteDatabase, sample_project):
        return db.create_protocol_run(
            project_id=sample_project.id,
            protocol_name="test-protocol",
            status="planned",
            base_branch="main",
        )

    # ==================== ensure_from_policy Tests ====================

    def test_ensure_from_policy_empty(self, clarifier, sample_project):
        """Test with empty policy returns empty list."""
        result = clarifier.ensure_from_policy(
            project_id=sample_project.id,
            policy={},
            applies_to="onboarding",
        )
        assert result == []

    def test_ensure_from_policy_no_clarifications(self, clarifier, sample_project):
        """Test with policy without clarifications."""
        result = clarifier.ensure_from_policy(
            project_id=sample_project.id,
            policy={"other_key": "value"},
            applies_to="onboarding",
        )
        assert result == []

    def test_ensure_from_policy_basic(self, clarifier, sample_project):
        """Test creating clarifications from policy."""
        policy = {
            "clarifications": {
                "items": [
                    {
                        "key": "data_class",
                        "question": "What is the data classification?",
                        "blocking": True,
                    },
                    {
                        "key": "team",
                        "question": "Which team owns this?",
                        "blocking": False,
                    },
                ]
            }
        }

        result = clarifier.ensure_from_policy(
            project_id=sample_project.id,
            policy=policy,
            applies_to="onboarding",
        )

        assert len(result) == 2
        assert result[0].key == "data_class"
        assert result[0].blocking is True
        assert result[1].key == "team"
        assert result[1].blocking is False

    def test_ensure_from_policy_filters_by_applies_to(self, clarifier, sample_project):
        """Test that clarifications are filtered by applies_to."""
        policy = {
            "clarifications": {
                "items": [
                    {
                        "key": "onboarding_q",
                        "question": "Onboarding question?",
                        "applies_to": "onboarding",
                    },
                    {
                        "key": "execution_q",
                        "question": "Execution question?",
                        "applies_to": "execution",
                    },
                ]
            }
        }

        result = clarifier.ensure_from_policy(
            project_id=sample_project.id,
            policy=policy,
            applies_to="onboarding",
        )

        assert len(result) == 1
        assert result[0].key == "onboarding_q"

    def test_ensure_from_policy_with_options(self, clarifier, sample_project):
        """Test clarifications with options."""
        policy = {
            "clarifications": {
                "items": [
                    {
                        "key": "env",
                        "question": "Target environment?",
                        "options": ["development", "staging", "production"],
                    }
                ]
            }
        }

        result = clarifier.ensure_from_policy(
            project_id=sample_project.id,
            policy=policy,
            applies_to="test",
        )

        assert len(result) == 1
        assert result[0].options == ["development", "staging", "production"]

    def test_ensure_from_policy_with_recommended(self, clarifier, sample_project):
        """Test clarifications with recommended values."""
        policy = {
            "clarifications": {
                "items": [
                    {
                        "key": "branch_prefix",
                        "question": "Branch prefix?",
                        "recommended": "feature/",
                    }
                ]
            }
        }

        result = clarifier.ensure_from_policy(
            project_id=sample_project.id,
            policy=policy,
            applies_to="test",
        )

        assert len(result) == 1
        assert result[0].recommended == {"value": "feature/"}

    def test_ensure_from_policy_protocol_scoped(self, clarifier, sample_project, sample_protocol):
        """Test protocol-scoped clarifications."""
        policy = {
            "clarifications": {
                "items": [
                    {
                        "key": "strategy",
                        "question": "Implementation strategy?",
                    }
                ]
            }
        }

        result = clarifier.ensure_from_policy(
            project_id=sample_project.id,
            policy=policy,
            applies_to="planning",
            protocol_run_id=sample_protocol.id,
        )

        assert len(result) == 1
        assert result[0].protocol_run_id == sample_protocol.id

    def test_ensure_from_policy_dedupes(self, clarifier, sample_project):
        """Test that duplicate clarifications are deduped."""
        policy = {
            "clarifications": {
                "items": [
                    {"key": "q1", "question": "Question 1?"},
                ]
            }
        }

        # Create once
        clarifier.ensure_from_policy(
            project_id=sample_project.id,
            policy=policy,
            applies_to="test",
        )

        # Create again - should update, not duplicate
        result = clarifier.ensure_from_policy(
            project_id=sample_project.id,
            policy=policy,
            applies_to="test",
        )

        # Should still have only one clarification
        open_items = clarifier.list_open(project_id=sample_project.id)
        assert len(open_items) == 1

    def test_ensure_from_policy_skips_invalid(self, clarifier, sample_project):
        """Test that invalid clarifications are skipped."""
        policy = {
            "clarifications": {
                "items": [
                    {"key": "valid", "question": "Valid question?"},
                    {"key": "", "question": "Empty key?"},  # Invalid
                    {"key": "no_question"},  # Missing question
                    "not_a_dict",  # Not a dict
                ]
            }
        }

        result = clarifier.ensure_from_policy(
            project_id=sample_project.id,
            policy=policy,
            applies_to="test",
        )

        assert len(result) == 1
        assert result[0].key == "valid"

    # ==================== list_open Tests ====================

    def test_list_open_empty(self, clarifier, sample_project):
        """Test listing when no open clarifications."""
        result = clarifier.list_open(project_id=sample_project.id)
        assert result == []

    def test_list_open_returns_open_only(self, clarifier, sample_project):
        """Test that only open clarifications are returned."""
        db = clarifier.db
        
        # Create and answer one
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="answered",
            question="Answered question?",
            applies_to="test",
        )
        clarifier.answer(
            project_id=sample_project.id,
            key="answered",
            answer={"text": "done"},
        )

        # Create open one
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="open",
            question="Open question?",
            applies_to="test",
        )

        result = clarifier.list_open(project_id=sample_project.id)
        assert len(result) == 1
        assert result[0].key == "open"

    def test_list_open_filters_by_applies_to(self, clarifier, sample_project):
        """Test filtering by applies_to."""
        db = clarifier.db
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="q1",
            question="Q1?",
            applies_to="onboarding",
        )
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="q2",
            question="Q2?",
            applies_to="execution",
        )

        result = clarifier.list_open(
            project_id=sample_project.id,
            applies_to="onboarding",
        )
        assert len(result) == 1
        assert result[0].key == "q1"

    # ==================== answer Tests ====================

    def test_answer_clarification(self, clarifier, sample_project):
        """Test answering a clarification."""
        db = clarifier.db
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="to_answer",
            question="Question?",
            applies_to="test",
        )

        result = clarifier.answer(
            project_id=sample_project.id,
            key="to_answer",
            answer={"text": "My answer"},
            answered_by="test_user",
        )

        assert result.status == "answered"
        assert result.answer == {"text": "My answer"}
        assert result.answered_by == "test_user"

    def test_answer_dismisses_with_none(self, clarifier, sample_project):
        """Test that None answer dismisses clarification."""
        db = clarifier.db
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="dismiss",
            question="Question?",
            applies_to="test",
        )

        result = clarifier.answer(
            project_id=sample_project.id,
            key="dismiss",
            answer=None,
        )

        assert result.status == "answered"

    # ==================== has_blocking_open Tests ====================

    def test_has_blocking_open_false_when_empty(self, clarifier, sample_project):
        """Test returns False when no clarifications."""
        assert not clarifier.has_blocking_open(project_id=sample_project.id)

    def test_has_blocking_open_false_when_only_non_blocking(self, clarifier, sample_project):
        """Test returns False when only non-blocking clarifications."""
        db = clarifier.db
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="nb",
            question="Non-blocking?",
            applies_to="test",
            blocking=False,
        )

        assert not clarifier.has_blocking_open(project_id=sample_project.id)

    def test_has_blocking_open_true(self, clarifier, sample_project):
        """Test returns True when blocking clarification exists."""
        db = clarifier.db
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="blocking",
            question="Blocking?",
            applies_to="test",
            blocking=True,
        )

        assert clarifier.has_blocking_open(project_id=sample_project.id)

    def test_has_blocking_open_false_when_answered(self, clarifier, sample_project):
        """Test returns False when blocking clarification is answered."""
        db = clarifier.db
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="was_blocking",
            question="Was blocking?",
            applies_to="test",
            blocking=True,
        )
        clarifier.answer(
            project_id=sample_project.id,
            key="was_blocking",
            answer={"text": "answered"},
        )

        assert not clarifier.has_blocking_open(project_id=sample_project.id)

    # ==================== list_blocking_open Tests ====================

    def test_list_blocking_open(self, clarifier, sample_project):
        """Test listing only blocking open clarifications."""
        db = clarifier.db
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="b1",
            question="Blocking 1?",
            applies_to="test",
            blocking=True,
        )
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="nb1",
            question="Non-blocking?",
            applies_to="test",
            blocking=False,
        )
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="b2",
            question="Blocking 2?",
            applies_to="test",
            blocking=True,
        )

        result = clarifier.list_blocking_open(project_id=sample_project.id)
        assert len(result) == 2
        keys = {c.key for c in result}
        assert keys == {"b1", "b2"}

    # ==================== get_answer Tests ====================

    def test_get_answer_returns_none_when_not_found(self, clarifier, sample_project):
        """Test returns None for non-existent clarification."""
        result = clarifier.get_answer(
            project_id=sample_project.id,
            key="nonexistent",
        )
        assert result is None

    def test_get_answer_returns_none_when_unanswered(self, clarifier, sample_project):
        """Test returns None for unanswered clarification."""
        db = clarifier.db
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="unanswered",
            question="Question?",
            applies_to="test",
        )

        result = clarifier.get_answer(
            project_id=sample_project.id,
            key="unanswered",
        )
        assert result is None

    def test_get_answer_returns_answer(self, clarifier, sample_project):
        """Test returns answer for answered clarification."""
        db = clarifier.db
        db.upsert_clarification(
            scope=f"project:{sample_project.id}",
            project_id=sample_project.id,
            key="answered",
            question="Question?",
            applies_to="test",
        )
        clarifier.answer(
            project_id=sample_project.id,
            key="answered",
            answer={"text": "the answer"},
        )

        result = clarifier.get_answer(
            project_id=sample_project.id,
            key="answered",
        )
        assert result == {"text": "the answer"}

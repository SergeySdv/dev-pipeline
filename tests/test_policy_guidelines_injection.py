import json
import tempfile
from pathlib import Path

import pytest

from tasksgodzilla.pipeline import (
    build_policy_guidelines,
    load_repo_local_policy,
    planning_prompt,
    decompose_step_prompt,
)


def test_load_repo_local_policy_json(tmp_path: Path) -> None:
    policy_dir = tmp_path / ".tasksgodzilla"
    policy_dir.mkdir(parents=True, exist_ok=True)
    policy_content = {
        "meta": {"key": "custom", "version": "1.0"},
        "requirements": {"step_sections": ["Verification", "Rollback"]},
        "defaults": {"ci": {"required_checks": ["scripts/ci/test.sh"]}},
    }
    (policy_dir / "policy.json").write_text(json.dumps(policy_content), encoding="utf-8")

    result = load_repo_local_policy(tmp_path)
    assert result is not None
    assert result["meta"]["key"] == "custom"
    assert result["requirements"]["step_sections"] == ["Verification", "Rollback"]


def test_load_repo_local_policy_missing(tmp_path: Path) -> None:
    result = load_repo_local_policy(tmp_path)
    assert result is None


def test_build_policy_guidelines_from_policy() -> None:
    policy = {
        "meta": {"key": "team-standard", "version": "1.0"},
        "requirements": {
            "step_sections": ["Sub-tasks", "Verification", "Rollback"],
            "protocol_files": ["plan.md", "context.md"],
        },
        "defaults": {
            "ci": {"required_checks": ["scripts/ci/test.sh", "scripts/ci/lint.sh"]},
        },
    }
    guidelines = build_policy_guidelines(policy)
    assert guidelines is not None
    assert "policy_pack: team-standard@1.0" in guidelines
    assert "required_step_sections: ['Sub-tasks', 'Verification', 'Rollback']" in guidelines
    assert "required_checks: ['scripts/ci/test.sh', 'scripts/ci/lint.sh']" in guidelines
    assert "step_file_template:" in guidelines
    assert "## Verification" in guidelines
    assert "Run `scripts/ci/test.sh`" in guidelines


def test_build_policy_guidelines_none_for_empty() -> None:
    assert build_policy_guidelines(None) is None
    assert build_policy_guidelines({}) is None


def test_planning_prompt_includes_policy_guidelines() -> None:
    guidelines = "policy_pack: custom@1.0\nrequired_step_sections: ['Verification']"
    prompt = planning_prompt(
        protocol_name="0001-test",
        protocol_number="0001",
        task_short_name="test",
        description="Test task",
        repo_root=Path("/fake/repo"),
        worktree_root=Path("/fake/worktree"),
        templates_section="# Templates",
        policy_guidelines=guidelines,
    )
    assert "policy_pack: custom@1.0" in prompt
    assert "required_step_sections: ['Verification']" in prompt
    assert "Project policy guidelines (warnings by default):" in prompt


def test_planning_prompt_without_policy_guidelines() -> None:
    prompt = planning_prompt(
        protocol_name="0001-test",
        protocol_number="0001",
        task_short_name="test",
        description="Test task",
        repo_root=Path("/fake/repo"),
        worktree_root=Path("/fake/worktree"),
        templates_section="# Templates",
        policy_guidelines=None,
    )
    assert "Project policy guidelines" not in prompt


def test_decompose_step_prompt_includes_policy_guidelines() -> None:
    guidelines = "required_step_sections: ['Verification', 'Rollback']"
    prompt = decompose_step_prompt(
        protocol_name="0001-test",
        protocol_number="0001",
        plan_md="# Plan\n\n- Step 1",
        step_filename="01-implement.md",
        step_content="# Step\n\n- Do the thing",
        policy_guidelines=guidelines,
    )
    assert "required_step_sections: ['Verification', 'Rollback']" in prompt
    assert "Project policy guidelines (warnings by default):" in prompt


def test_decompose_step_prompt_without_policy_guidelines() -> None:
    prompt = decompose_step_prompt(
        protocol_name="0001-test",
        protocol_number="0001",
        plan_md="# Plan\n\n- Step 1",
        step_filename="01-implement.md",
        step_content="# Step\n\n- Do the thing",
        policy_guidelines=None,
    )
    assert "Project policy guidelines" not in prompt


def test_build_policy_guidelines_generates_verification_snippet() -> None:
    policy = {
        "meta": {"key": "test", "version": "1.0"},
        "defaults": {
            "ci": {"required_checks": ["scripts/ci/test.sh", "scripts/ci/build.sh"]},
        },
    }
    guidelines = build_policy_guidelines(policy)
    assert guidelines is not None
    assert "verification_snippet:" in guidelines
    assert "- Run `scripts/ci/test.sh`" in guidelines
    assert "- Run `scripts/ci/build.sh`" in guidelines

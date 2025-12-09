from pathlib import Path

from tasksgodzilla.services.prompts import PromptService


def test_resolve_qa_prompt_with_default(tmp_path):
    """Test resolve_qa_prompt uses default prompt when not specified in config."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    prompts_dir = workspace / "prompts"
    prompts_dir.mkdir()
    
    # Create default QA prompt
    qa_prompt = prompts_dir / "quality-validator.prompt.md"
    qa_prompt.write_text("# QA Prompt\n\nValidate the step.", encoding="utf-8")
    
    protocol_root = workspace / ".protocols" / "test-protocol"
    protocol_root.mkdir(parents=True)
    
    service = PromptService(workspace_root=workspace)
    
    # Empty config should use default
    qa_config = {}
    prompt_path, version = service.resolve_qa_prompt(qa_config, protocol_root, workspace)
    
    assert prompt_path == qa_prompt.resolve()
    assert version is not None


def test_resolve_qa_prompt_with_custom(tmp_path):
    """Test resolve_qa_prompt uses custom prompt from config."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    protocol_root = workspace / ".protocols" / "test-protocol"
    protocol_root.mkdir(parents=True)
    
    # Create custom QA prompt
    custom_prompt = protocol_root / "custom-qa.md"
    custom_prompt.write_text("# Custom QA\n\nCustom validation.", encoding="utf-8")
    
    service = PromptService(workspace_root=workspace)
    
    # Config with custom prompt
    qa_config = {"prompt": "custom-qa.md"}
    prompt_path, version = service.resolve_qa_prompt(qa_config, protocol_root, workspace)
    
    assert prompt_path == custom_prompt.resolve()
    assert version is not None


def test_build_qa_context(tmp_path):
    """Test build_qa_context gathers all required context."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    protocol_root = workspace / ".protocols" / "test-protocol"
    protocol_root.mkdir(parents=True)
    
    # Create protocol files
    (protocol_root / "plan.md").write_text("# Plan\n\n- [ ] Task 1", encoding="utf-8")
    (protocol_root / "context.md").write_text("# Context\n\nBackground info.", encoding="utf-8")
    (protocol_root / "log.md").write_text("# Log\n\n- Event 1", encoding="utf-8")
    
    # Create step file
    step_path = protocol_root / "01-step.md"
    step_path.write_text("# Step\n\nDo something.", encoding="utf-8")
    
    service = PromptService(workspace_root=workspace)
    context = service.build_qa_context(protocol_root, step_path, workspace)
    
    assert "plan" in context
    assert "# Plan" in context["plan"]
    assert "context" in context
    assert "Background info" in context["context"]
    assert "log" in context
    assert "Event 1" in context["log"]
    assert "step" in context
    assert "Do something" in context["step"]
    assert "step_name" in context
    assert context["step_name"] == "01-step.md"
    assert "git_status" in context
    assert "last_commit" in context


def test_build_qa_context_missing_files(tmp_path):
    """Test build_qa_context handles missing files gracefully."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    protocol_root = workspace / ".protocols" / "test-protocol"
    protocol_root.mkdir(parents=True)
    
    # Only create step file, no plan/context/log
    step_path = protocol_root / "01-step.md"
    step_path.write_text("# Step\n\nDo something.", encoding="utf-8")
    
    service = PromptService(workspace_root=workspace)
    context = service.build_qa_context(protocol_root, step_path, workspace)
    
    # Should have empty strings for missing files
    assert context["plan"] == ""
    assert context["context"] == ""
    assert context["log"] == ""
    assert context["step"] == "# Step\n\nDo something."


def test_resolve_step_path_for_qa_direct(tmp_path):
    """Test resolve_step_path_for_qa finds step file directly."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    protocol_root = workspace / ".protocols" / "test-protocol"
    protocol_root.mkdir(parents=True)
    
    # Create step file
    step_path = protocol_root / "01-step.md"
    step_path.write_text("# Step", encoding="utf-8")
    
    service = PromptService(workspace_root=workspace)
    resolved = service.resolve_step_path_for_qa(protocol_root, "01-step.md", workspace)
    
    assert resolved == step_path.resolve()


def test_resolve_step_path_for_qa_without_extension(tmp_path):
    """Test resolve_step_path_for_qa adds .md extension if needed."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    protocol_root = workspace / ".protocols" / "test-protocol"
    protocol_root.mkdir(parents=True)
    
    # Create step file
    step_path = protocol_root / "01-step.md"
    step_path.write_text("# Step", encoding="utf-8")
    
    service = PromptService(workspace_root=workspace)
    # Request without .md extension
    resolved = service.resolve_step_path_for_qa(protocol_root, "01-step", workspace)
    
    assert resolved == step_path.resolve()


def test_resolve_step_path_for_qa_fallback(tmp_path):
    """Test resolve_step_path_for_qa falls back to spec resolution."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    protocol_root = workspace / ".protocols" / "test-protocol"
    protocol_root.mkdir(parents=True)
    
    service = PromptService(workspace_root=workspace)
    # Non-existent step should still resolve to a path
    resolved = service.resolve_step_path_for_qa(protocol_root, "missing-step", workspace)
    
    # Should return a path (even if it doesn't exist)
    assert isinstance(resolved, Path)


def test_resolve_prompt(tmp_path):
    """Test resolve method returns path, text, and version."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    prompts_dir = workspace / "prompts"
    prompts_dir.mkdir()
    
    # Create a prompt file
    prompt_file = prompts_dir / "test-prompt.md"
    prompt_content = "# Test Prompt\n\nThis is a test prompt."
    prompt_file.write_text(prompt_content, encoding="utf-8")
    
    service = PromptService(workspace_root=workspace)
    path, text, version = service.resolve("prompts/test-prompt.md")
    
    assert path == prompt_file.resolve()
    assert text == prompt_content
    assert version is not None
    assert isinstance(version, str)

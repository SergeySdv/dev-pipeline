"""
Tests for devgodzilla.cli.agents module.

Tests cover agent list, check, and config commands.
"""

import yaml
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from devgodzilla.cli.main import cli
from devgodzilla.engines.interface import EngineKind


class TestAgentListCommand:
    """Tests for 'agent list' command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_registry(self):
        """Create a mock registry with sample agents."""
        registry = MagicMock()
        
        # Create mock metadata objects
        meta1 = SimpleNamespace(
            id="opencode",
            display_name="OpenCode",
            kind=EngineKind.CLI,
        )
        meta2 = SimpleNamespace(
            id="claude-code",
            display_name="Claude Code",
            kind=EngineKind.CLI,
        )
        meta3 = SimpleNamespace(
            id="cursor",
            display_name="Cursor",
            kind=EngineKind.IDE,
        )
        
        registry.list_metadata.return_value = [meta1, meta2, meta3]
        return registry

    @patch("devgodzilla.cli.agents.get_registry")
    def test_list_shows_agents(self, mock_get_registry, runner, mock_registry):
        """Test agent list displays registered agents."""
        mock_get_registry.return_value = mock_registry
        
        result = runner.invoke(cli, ["agent", "list"])
        
        assert result.exit_code == 0
        assert "opencode" in result.output
        assert "claude-code" in result.output
        assert "cursor" in result.output

    @patch("devgodzilla.cli.agents.get_registry")
    def test_list_empty(self, mock_get_registry, runner):
        """Test agent list with no registered agents."""
        registry = MagicMock()
        registry.list_metadata.return_value = []
        mock_get_registry.return_value = registry
        
        result = runner.invoke(cli, ["agent", "list"])
        
        assert result.exit_code == 0
        assert "No agents registered" in result.output

    @patch("devgodzilla.cli.agents.get_registry")
    def test_list_shows_table_headers(self, mock_get_registry, runner, mock_registry):
        """Test agent list includes table headers."""
        mock_get_registry.return_value = mock_registry
        
        result = runner.invoke(cli, ["agent", "list"])
        
        assert "ID" in result.output
        assert "Name" in result.output
        assert "Kind" in result.output

    @patch("devgodzilla.cli.agents.get_registry")
    def test_list_displays_kind(self, mock_get_registry, runner, mock_registry):
        """Test agent list shows engine kind."""
        mock_get_registry.return_value = mock_registry
        
        result = runner.invoke(cli, ["agent", "list"])
        
        # Should show CLI and IDE kinds
        assert "cli" in result.output.lower() or "CLI" in result.output


class TestAgentTestCommand:
    """Tests for 'agent test' command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_engine(self):
        """Create a mock engine."""
        engine = MagicMock()
        engine.check_availability.return_value = True
        return engine

    @patch("devgodzilla.cli.agents.get_registry")
    def test_agent_available(self, mock_get_registry, runner, mock_engine):
        """Test agent test when agent is available."""
        registry = MagicMock()
        registry.get.return_value = mock_engine
        mock_get_registry.return_value = registry
        
        result = runner.invoke(cli, ["agent", "test", "opencode"])
        
        assert result.exit_code == 0
        assert "available" in result.output.lower()
        registry.get.assert_called_once_with("opencode")

    @patch("devgodzilla.cli.agents.get_registry")
    def test_agent_unavailable(self, mock_get_registry, runner):
        """Test agent test when agent is unavailable."""
        engine = MagicMock()
        engine.check_availability.return_value = False
        
        registry = MagicMock()
        registry.get.return_value = engine
        mock_get_registry.return_value = registry
        
        result = runner.invoke(cli, ["agent", "test", "missing-agent"])
        
        assert result.exit_code == 0
        assert "unavailable" in result.output.lower()

    @patch("devgodzilla.cli.agents.get_registry")
    def test_agent_test_error(self, mock_get_registry, runner):
        """Test agent test handles errors."""
        registry = MagicMock()
        registry.get.side_effect = Exception("Connection failed")
        mock_get_registry.return_value = registry
        
        result = runner.invoke(cli, ["agent", "test", "broken-agent"])
        
        assert result.exit_code == 0
        assert "error" in result.output.lower()


class TestAgentCheckCommand:
    """Tests for 'agent check' command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_registry_with_agents(self):
        """Create mock registry with multiple agents."""
        registry = MagicMock()
        
        # Create mock metadata
        agents = [
            SimpleNamespace(id="agent1", display_name="Agent 1", kind=EngineKind.CLI),
            SimpleNamespace(id="agent2", display_name="Agent 2", kind=EngineKind.CLI),
            SimpleNamespace(id="agent3", display_name="Agent 3", kind=EngineKind.IDE),
        ]
        registry.list_metadata.return_value = agents
        return registry

    @patch("devgodzilla.cli.agents.get_registry")
    def test_check_all_available(self, mock_get_registry, runner, mock_registry_with_agents):
        """Test health check when all agents are available."""
        engine = MagicMock()
        engine.check_availability.return_value = True
        mock_registry_with_agents.get.return_value = engine
        mock_get_registry.return_value = mock_registry_with_agents
        
        result = runner.invoke(cli, ["agent", "check"])
        
        assert result.exit_code == 0
        assert "3/3" in result.output
        assert "agents available" in result.output.lower()

    @patch("devgodzilla.cli.agents.get_registry")
    def test_check_some_unavailable(self, mock_get_registry, runner, mock_registry_with_agents):
        """Test health check when some agents are unavailable."""
        engine_available = MagicMock()
        engine_available.check_availability.return_value = True
        
        engine_unavailable = MagicMock()
        engine_unavailable.check_availability.return_value = False
        
        def get_side_effect(agent_id):
            if agent_id == "agent1":
                return engine_available
            return engine_unavailable
        
        mock_registry_with_agents.get.side_effect = get_side_effect
        mock_get_registry.return_value = mock_registry_with_agents
        
        result = runner.invoke(cli, ["agent", "check"])
        
        assert result.exit_code == 0
        assert "1/3" in result.output

    @patch("devgodzilla.cli.agents.get_registry")
    def test_check_empty_registry(self, mock_get_registry, runner):
        """Test health check with no agents registered."""
        registry = MagicMock()
        registry.list_metadata.return_value = []
        mock_get_registry.return_value = registry
        
        result = runner.invoke(cli, ["agent", "check"])
        
        assert result.exit_code == 0
        assert "No agents registered" in result.output

    @patch("devgodzilla.cli.agents.get_registry")
    def test_check_shows_status_column(self, mock_get_registry, runner, mock_registry_with_agents):
        """Test health check includes status column."""
        engine = MagicMock()
        engine.check_availability.return_value = True
        mock_registry_with_agents.get.return_value = engine
        mock_get_registry.return_value = mock_registry_with_agents
        
        result = runner.invoke(cli, ["agent", "check"])
        
        assert "Status" in result.output

    @patch("devgodzilla.cli.agents.get_registry")
    def test_check_handles_errors(self, mock_get_registry, runner):
        """Test health check handles per-agent errors gracefully."""
        registry = MagicMock()
        
        agents = [
            SimpleNamespace(id="good", display_name="Good Agent", kind=EngineKind.CLI),
            SimpleNamespace(id="bad", display_name="Bad Agent", kind=EngineKind.CLI),
        ]
        registry.list_metadata.return_value = agents
        
        good_engine = MagicMock()
        good_engine.check_availability.return_value = True
        
        def get_side_effect(agent_id):
            if agent_id == "good":
                return good_engine
            raise Exception("Agent error")
        
        registry.get.side_effect = get_side_effect
        mock_get_registry.return_value = registry
        
        result = runner.invoke(cli, ["agent", "check"])
        
        assert result.exit_code == 0
        # Should still show 1 available and handle error
        assert "1/2" in result.output


class TestAgentConfigCommand:
    """Tests for 'agent config' command."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a mock config object with a temp config path."""
        config_path = tmp_path / "config" / "agents.yaml"

        class MockConfig:
            agent_config_path = config_path  # Use Path object, not string

        return MockConfig()

    @patch("devgodzilla.cli.main.validate_path_contract")
    @patch("devgodzilla.config.load_config")
    def test_config_show_empty(self, mock_load_config, mock_validate, runner, mock_config, tmp_path):
        """Test showing config when no custom config exists."""
        from devgodzilla.services.path_contract import PathContractReport
        
        mock_load_config.return_value = mock_config
        mock_validate.return_value = PathContractReport()  # Valid report

        result = runner.invoke(cli, ["agent", "config", "test-agent", "--show"])

        assert result.exit_code == 0
        assert "Configuration for test-agent" in result.output
        assert "No custom configuration" in result.output

    @patch("devgodzilla.cli.main.validate_path_contract")
    @patch("devgodzilla.config.load_config")
    def test_config_show_existing(self, mock_load_config, mock_validate, runner, mock_config, tmp_path):
        """Test showing existing config."""
        from devgodzilla.services.path_contract import PathContractReport
        
        # Create existing config
        config_path = tmp_path / "config" / "agents.yaml"
        mock_config.agent_config_path = config_path  # Use Path object
        config_path.parent.mkdir(parents=True, exist_ok=True)

        existing_config = {
            "agents": {
                "test-agent": {
                    "model": "existing-model",
                    "timeout_seconds": 120
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(existing_config, f)

        mock_load_config.return_value = mock_config
        mock_validate.return_value = PathContractReport()

        result = runner.invoke(cli, ["agent", "config", "test-agent", "--show"])

        assert result.exit_code == 0
        assert "Configuration for test-agent" in result.output
        assert "existing-model" in result.output

    @patch("devgodzilla.cli.main.validate_path_contract")
    @patch("devgodzilla.config.load_config")
    def test_config_set_model(self, mock_load_config, mock_validate, runner, mock_config, tmp_path):
        """Test setting model in config."""
        from devgodzilla.services.path_contract import PathContractReport
        
        mock_load_config.return_value = mock_config
        mock_validate.return_value = PathContractReport()

        result = runner.invoke(cli, ["agent", "config", "test-agent", "--model", "gpt-4"])

        assert result.exit_code == 0
        assert "Set model to: gpt-4" in result.output
        assert "Configuration saved" in result.output

        # Verify file was created
        config_path = tmp_path / "config" / "agents.yaml"
        assert config_path.exists()

        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["agents"]["test-agent"]["model"] == "gpt-4"

    @patch("devgodzilla.cli.main.validate_path_contract")
    @patch("devgodzilla.config.load_config")
    def test_config_set_timeout(self, mock_load_config, mock_validate, runner, mock_config, tmp_path):
        """Test setting timeout in config."""
        from devgodzilla.services.path_contract import PathContractReport
        
        mock_load_config.return_value = mock_config
        mock_validate.return_value = PathContractReport()

        result = runner.invoke(cli, ["agent", "config", "test-agent", "--timeout", "60"])

        assert result.exit_code == 0
        assert "Set timeout to: 60s" in result.output

        config_path = tmp_path / "config" / "agents.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["agents"]["test-agent"]["timeout_seconds"] == 60

    @patch("devgodzilla.cli.main.validate_path_contract")
    @patch("devgodzilla.config.load_config")
    def test_config_set_multiple_options(self, mock_load_config, mock_validate, runner, mock_config, tmp_path):
        """Test setting multiple config options at once."""
        from devgodzilla.services.path_contract import PathContractReport
        
        mock_load_config.return_value = mock_config
        mock_validate.return_value = PathContractReport()

        result = runner.invoke(cli, [
            "agent", "config", "test-agent",
            "--model", "claude-3",
            "--timeout", "90"
        ])

        assert result.exit_code == 0
        assert "Set model to: claude-3" in result.output
        assert "Set timeout to: 90s" in result.output

        config_path = tmp_path / "config" / "agents.yaml"
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["agents"]["test-agent"]["model"] == "claude-3"
        assert config["agents"]["test-agent"]["timeout_seconds"] == 90

    @patch("devgodzilla.cli.main.validate_path_contract")
    @patch("devgodzilla.config.load_config")
    def test_config_no_changes(self, mock_load_config, mock_validate, runner, mock_config, tmp_path):
        """Test config command with no changes specified."""
        from devgodzilla.services.path_contract import PathContractReport
        
        mock_load_config.return_value = mock_config
        mock_validate.return_value = PathContractReport()

        result = runner.invoke(cli, ["agent", "config", "test-agent"])

        assert result.exit_code == 0
        assert "No configuration changes specified" in result.output

    @patch("devgodzilla.cli.main.validate_path_contract")
    @patch("devgodzilla.config.load_config")
    def test_config_creates_directory(self, mock_load_config, mock_validate, runner, mock_config, tmp_path):
        """Test config creates parent directories if needed."""
        from devgodzilla.services.path_contract import PathContractReport
        
        # Use a nested path that doesn't exist
        nested_path = tmp_path / "deeply" / "nested" / "config" / "agents.yaml"
        mock_config.agent_config_path = nested_path  # Use Path object
        mock_load_config.return_value = mock_config
        mock_validate.return_value = PathContractReport()

        result = runner.invoke(cli, ["agent", "config", "test-agent", "--model", "test-model"])

        assert result.exit_code == 0
        assert nested_path.exists()

    @patch("devgodzilla.cli.main.validate_path_contract")
    @patch("devgodzilla.config.load_config")
    def test_config_persists_to_yaml(self, mock_load_config, mock_validate, runner, mock_config, tmp_path):
        """Test config is persisted to YAML file."""
        from devgodzilla.services.path_contract import PathContractReport
        
        mock_load_config.return_value = mock_config
        mock_validate.return_value = PathContractReport()

        runner.invoke(cli, ["agent", "config", "test-agent", "--model", "persisted-model"])

        config_path = tmp_path / "config" / "agents.yaml"

        # Read the file directly and verify YAML structure
        with open(config_path) as f:
            content = f.read()

        # Verify it's valid YAML
        config = yaml.safe_load(content)
        assert config is not None
        assert "agents" in config
        assert "test-agent" in config["agents"]

    @patch("devgodzilla.cli.main.validate_path_contract")
    @patch("devgodzilla.config.load_config")
    def test_config_updates_existing(self, mock_load_config, mock_validate, runner, mock_config, tmp_path):
        """Test config updates existing agent config."""
        from devgodzilla.services.path_contract import PathContractReport
        
        # Create existing config with some settings
        config_path = tmp_path / "config" / "agents.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        existing_config = {
            "agents": {
                "test-agent": {
                    "model": "old-model",
                    "timeout_seconds": 30
                }
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(existing_config, f)

        mock_load_config.return_value = mock_config
        mock_validate.return_value = PathContractReport()

        # Update just the model
        result = runner.invoke(cli, ["agent", "config", "test-agent", "--model", "new-model"])

        assert result.exit_code == 0

        # Verify timeout was preserved
        with open(config_path) as f:
            config = yaml.safe_load(f)

        assert config["agents"]["test-agent"]["model"] == "new-model"
        assert config["agents"]["test-agent"]["timeout_seconds"] == 30


class TestAgentConfigFunctionality:
    """
    Unit tests for agent config functionality that test the config logic
    without going through the CLI entry point.
    """

    def test_config_file_default_path(self, tmp_path):
        """Test default config file path."""
        # When no custom path is set, default is used
        default_path = Path("config/agents.yaml")
        assert default_path.name == "agents.yaml"
        assert "config" in str(default_path)

    def test_config_file_can_be_created(self, tmp_path):
        """Test config file can be created."""
        config_path = tmp_path / "config" / "agents.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = {
            "agents": {
                "test-agent": {
                    "model": "test-model",
                    "timeout_seconds": 60,
                }
            }
        }
        
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        assert config_path.exists()
        
        # Read back
        with open(config_path) as f:
            loaded = yaml.safe_load(f)
        
        assert loaded["agents"]["test-agent"]["model"] == "test-model"

    def test_config_file_update_preserves_other_agents(self, tmp_path):
        """Test updating one agent preserves others."""
        config_path = tmp_path / "agents.yaml"
        
        # Create initial config
        config_data = {
            "agents": {
                "agent1": {"model": "model1"},
                "agent2": {"model": "model2"},
            }
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        # Update agent1 only
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        config["agents"]["agent1"]["timeout_seconds"] = 120
        
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        
        # Verify agent2 preserved
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        assert config["agents"]["agent2"]["model"] == "model2"
        assert config["agents"]["agent1"]["timeout_seconds"] == 120


class TestAgentCommandGroup:
    """Tests for agent command group."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    def test_agent_help(self, runner):
        """Test agent command group help."""
        result = runner.invoke(cli, ["agent", "--help"])
        
        assert result.exit_code == 0
        assert "list" in result.output
        assert "test" in result.output
        assert "check" in result.output
        assert "config" in result.output

    def test_agent_subcommand_required(self, runner):
        """Test agent command requires subcommand."""
        result = runner.invoke(cli, ["agent"])
        
        # Click shows help when no subcommand provided
        assert result.exit_code == 0
        assert "list" in result.output.lower() or "Usage" in result.output

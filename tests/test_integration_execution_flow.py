"""Integration tests for execution flow with engines and block detection."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from devgodzilla.engines.registry import EngineRegistry, get_registry
from devgodzilla.engines.block_detector import BlockDetector, detect_block, BlockReason
from devgodzilla.engines.interface import EngineKind, EngineMetadata, EngineRequest, EngineResult


class TestExecutionFlowIntegration:
    """Tests for complete execution flow."""
    
    @pytest.fixture
    def registry(self):
        return EngineRegistry()
    
    @pytest.fixture
    def block_detector(self):
        return BlockDetector()
    
    def test_registry_lists_registered_engines(self, registry):
        """Registry can list registered engines."""
        # Initially empty or has some engines
        engines = registry.list_all()
        assert isinstance(engines, list)
    
    def test_engine_availability_check(self, registry):
        """Can check availability for registered engines."""
        # Check if registry has engines
        engines = registry.list_all()
        
        for engine in engines:
            # Should not raise
            available = engine.check_availability()
            assert isinstance(available, bool)
    
    def test_block_detection_in_execution_flow(self, block_detector):
        """BlockDetector integrates with execution results."""
        # Simulated execution output that's blocked
        blocked_output = """
Processing task...
Error: Cannot proceed without clarification on the authentication method.
Which authentication should be used: OAuth2 or API keys?
"""
        
        result = block_detector.detect(blocked_output)
        
        assert result is not None
        assert result.reason in (BlockReason.CLARIFICATION_NEEDED, 
                                  BlockReason.MISSING_INFORMATION,
                                  BlockReason.AMBIGUOUS_REQUIREMENT)
        assert result.suggested_question is not None
    
    def test_successful_execution_no_block(self, block_detector):
        """Successful execution doesn't trigger blocks."""
        success_output = """
Processing task...
Created file: main.py
Updated file: utils.py
Task completed successfully.
"""
        
        result = block_detector.detect(success_output)
        
        assert result is None
    
    def test_block_detector_convenience_function(self):
        """Convenience function detect_block works."""
        blocked = "Cannot proceed without additional information about the API endpoint."
        
        result = detect_block(blocked)
        
        assert result is not None
        assert result.reason == BlockReason.MISSING_INFORMATION
    
    def test_block_detector_multiple_blocks(self, block_detector):
        """Can detect multiple blocks in output."""
        output = """
Error: Need clarification on authentication method.
Also: Cannot determine the correct database schema.
"""
        
        blocks = block_detector.detect_all(output)
        
        # Should detect at least one block
        assert len(blocks) >= 1
    
    def test_block_detector_confidence_levels(self, block_detector):
        """Block detection returns confidence scores."""
        # High confidence pattern
        high_conf = "Permission denied: access to /etc/passwd"
        result = block_detector.detect(high_conf)
        
        if result:
            assert result.confidence >= 0.9
    
    def test_block_detector_context_extraction(self, block_detector):
        """BlockDetector extracts context around blocks."""
        output = """
Line 1: Some code
Line 2: More code  
Line 3: Cannot proceed without clarification on the output format.
Line 4: Next line
Line 5: Another line
"""
        
        result = block_detector.detect(output)
        
        assert result is not None
        assert "context" in result.context
        assert "match_text" in result.context


class TestEngineRegistryIntegration:
    """Tests for EngineRegistry functionality."""
    
    def test_register_and_unregister_engine(self):
        """Can register and unregister engines."""
        registry = EngineRegistry()
        
        # Create a mock engine
        mock_engine = MagicMock()
        mock_engine.metadata = EngineMetadata(
            id="test-engine",
            display_name="Test Engine",
            kind=EngineKind.CLI,
        )
        mock_engine.check_availability.return_value = True
        
        # Register
        registry.register(mock_engine)
        assert registry.has("test-engine")
        
        # Unregister
        registry.unregister("test-engine")
        assert not registry.has("test-engine")
    
    def test_set_default_engine(self):
        """Can set default engine."""
        registry = EngineRegistry()
        
        mock_engine = MagicMock()
        mock_engine.metadata = EngineMetadata(
            id="default-engine",
            display_name="Default Engine",
            kind=EngineKind.CLI,
        )
        
        registry.register(mock_engine, default=True)
        
        assert registry.get_default().metadata.id == "default-engine"
    
    def test_get_nonexistent_engine_raises(self):
        """Getting nonexistent engine raises error."""
        registry = EngineRegistry()
        
        from devgodzilla.engines.registry import EngineNotFoundError
        
        with pytest.raises(EngineNotFoundError):
            registry.get("nonexistent-engine")
    
    def test_list_engines_by_kind(self):
        """Can list engines by kind."""
        registry = EngineRegistry()
        
        cli_engine = MagicMock()
        cli_engine.metadata = EngineMetadata(
            id="cli-engine",
            display_name="CLI Engine",
            kind=EngineKind.CLI,
        )
        
        api_engine = MagicMock()
        api_engine.metadata = EngineMetadata(
            id="api-engine",
            display_name="API Engine",
            kind=EngineKind.API,
        )
        
        registry.register(cli_engine)
        registry.register(api_engine)
        
        cli_engines = registry.list_by_kind(EngineKind.CLI)
        api_engines = registry.list_by_kind(EngineKind.API)
        
        assert len(cli_engines) == 1
        assert len(api_engines) == 1


class TestBlockReasonPatterns:
    """Tests for various block reason patterns."""
    
    @pytest.fixture
    def detector(self):
        return BlockDetector()
    
    def test_clarification_needed_pattern(self, detector):
        """Detects clarification needed blocks."""
        output = "I need clarification on what format to use for the response."
        result = detector.detect(output)
        
        assert result is not None
        assert result.reason == BlockReason.CLARIFICATION_NEEDED
    
    def test_ambiguous_requirement_pattern(self, detector):
        """Detects ambiguous requirement blocks."""
        output = "Cannot determine the correct approach - ambiguous requirement about authentication"
        result = detector.detect(output)
        
        assert result is not None
    
    def test_permission_denied_pattern(self, detector):
        """Detects permission denied blocks."""
        output = "Permission denied: cannot write to /etc/config"
        result = detector.detect(output)
        
        assert result is not None
        assert result.reason == BlockReason.PERMISSION_DENIED
        assert result.confidence >= 0.9
    
    def test_resource_not_found_pattern(self, detector):
        """Detects resource not found blocks."""
        output = "File not found: /path/to/missing/file.txt"
        result = detector.detect(output)
        
        assert result is not None
        assert result.reason == BlockReason.RESOURCE_NOT_FOUND
    
    def test_impossible_request_pattern(self, detector):
        """Detects impossible request blocks."""
        output = "It is impossible to satisfy all the given constraints."
        result = detector.detect(output)
        
        assert result is not None
        assert result.reason == BlockReason.IMPOSSIBLE_REQUEST

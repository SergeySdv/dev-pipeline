"""Tests for Retry Configuration."""

import pytest
from pathlib import Path
import tempfile
import yaml
from devgodzilla.services.retry_config import (
    RetrySettings, OrchestrationConfig, CircuitBreakerSettings,
    TimeoutSettings, ParallelismSettings, FeedbackSettings,
    QueueSettings, get_orchestration_config, reload_orchestration_config
)


class TestRetrySettings:
    def test_default_retry_settings(self):
        """Default retry settings are sensible."""
        settings = RetrySettings()
        assert settings.max_attempts == 3
        assert settings.initial_delay_seconds == 10.0
        assert settings.backoff_multiplier == 2.0
        assert settings.jitter is True
    
    def test_custom_retry_settings(self):
        """Custom retry settings can be set."""
        settings = RetrySettings(
            max_attempts=5,
            initial_delay_seconds=5.0,
            max_delay_seconds=60.0,
            backoff_multiplier=3.0,
            jitter=False
        )
        assert settings.max_attempts == 5
        assert settings.initial_delay_seconds == 5.0
    
    def test_retry_settings_from_dict(self):
        """RetrySettings can be created from dict."""
        settings = RetrySettings.from_dict({
            "max_attempts": 10,
            "initial_delay_seconds": 30.0
        })
        assert settings.max_attempts == 10
        assert settings.initial_delay_seconds == 30.0


class TestOrchestrationConfig:
    def test_orchestration_config_defaults(self):
        """OrchestrationConfig has sensible defaults."""
        config = OrchestrationConfig()
        assert config.retry.max_attempts == 3
        assert config.parallelism.max_concurrent_steps == 4
        assert config.circuit_breaker.enabled is True
    
    def test_config_from_dict(self):
        """Config can be loaded from dictionary."""
        data = {
            "retry": {
                "max_attempts": 5,
                "initial_delay_seconds": 30
            },
            "parallelism": {
                "max_concurrent_steps": 8
            }
        }
        
        config = OrchestrationConfig.from_dict(data)
        
        assert config.retry.max_attempts == 5
        assert config.retry.initial_delay_seconds == 30
        assert config.parallelism.max_concurrent_steps == 8
    
    def test_config_from_yaml(self):
        """Config can be loaded from YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                "retry": {"max_attempts": 4},
                "parallelism": {"max_concurrent_steps": 8}
            }, f)
            f.flush()
            
            config = OrchestrationConfig.from_yaml(f.name)
            
            assert config.retry.max_attempts == 4
            assert config.parallelism.max_concurrent_steps == 8
    
    def test_config_from_missing_yaml(self):
        """Config returns defaults for missing file."""
        config = OrchestrationConfig.from_yaml("/nonexistent/path.yaml")
        assert config.retry.max_attempts == 3
    
    def test_get_retry_settings_with_override(self):
        """get_retry_settings returns override for specific error type."""
        config = OrchestrationConfig(
            retry_overrides={
                "timeout": RetrySettings(max_attempts=5)
            }
        )
        
        result = config.get_retry_settings("timeout")
        assert result.max_attempts == 5
        
        # No override returns default
        result2 = config.get_retry_settings("unknown")
        assert result2.max_attempts == 3
    
    def test_calculate_delay_basic(self):
        """calculate_delay returns correct exponential backoff."""
        config = OrchestrationConfig()
        config.retry.jitter = False  # Disable jitter for predictable testing
        
        # Note: calculate_delay is on OrchestrationConfig, uses retry settings
        delay0 = config.calculate_delay(1)
        delay1 = config.calculate_delay(2)
        delay2 = config.calculate_delay(3)
        
        # Each attempt should increase delay exponentially
        assert delay1 > delay0
        assert delay2 > delay1
    
    def test_calculate_delay_capped(self):
        """calculate_delay is capped at max_delay."""
        config = OrchestrationConfig()
        config.retry.max_delay_seconds = 100.0
        config.retry.jitter = False
        
        # Large attempt number
        delay = config.calculate_delay(10)
        assert delay <= 100.0


class TestOtherSettings:
    def test_circuit_breaker_settings(self):
        """CircuitBreakerSettings has correct defaults."""
        settings = CircuitBreakerSettings()
        assert settings.enabled is True
        assert settings.failure_threshold == 5
        assert settings.recovery_timeout_seconds == 60.0
    
    def test_timeout_settings(self):
        """TimeoutSettings has correct defaults."""
        settings = TimeoutSettings()
        assert settings.default_step_seconds == 300.0
        assert settings.max_step_seconds == 3600.0
    
    def test_parallelism_settings(self):
        """ParallelismSettings has correct defaults."""
        settings = ParallelismSettings()
        assert settings.max_concurrent_steps == 4
        assert settings.max_concurrent_protocols == 10
    
    def test_feedback_settings(self):
        """FeedbackSettings has correct defaults."""
        settings = FeedbackSettings()
        assert settings.max_clarification_loops == 3
        assert settings.max_replan_attempts == 2
    
    def test_queue_settings(self):
        """QueueSettings has correct defaults."""
        settings = QueueSettings()
        assert settings.max_depth == 1000
        assert "critical" in settings.priority_levels


class TestGlobalConfig:
    def test_get_orchestration_config(self):
        """get_orchestration_config returns config."""
        config = get_orchestration_config()
        assert isinstance(config, OrchestrationConfig)
    
    def test_reload_orchestration_config(self):
        """reload_orchestration_config returns fresh config."""
        config1 = get_orchestration_config()
        config2 = reload_orchestration_config()
        assert isinstance(config2, OrchestrationConfig)

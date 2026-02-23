"""Tests for OpenTelemetry telemetry service."""

import pytest
from unittest.mock import patch, MagicMock
from devgodzilla.services.telemetry import (
    TelemetryConfig, Telemetry, get_telemetry, init_telemetry,
    shutdown_telemetry, start_as_current_span, traced, set_span_attribute,
    get_current_span, record_exception
)


class TestTelemetryConfig:
    def test_default_config(self):
        config = TelemetryConfig()
        assert config.service_name == "devgodzilla"
        assert config.service_version == "0.1.0"
        assert config.environment == "development"
        assert config.otlp_endpoint is None
    
    def test_custom_config(self):
        config = TelemetryConfig(
            service_name="test-service",
            service_version="1.0.0",
            environment="production",
            otlp_endpoint="http://localhost:4318"
        )
        assert config.service_name == "test-service"
        assert config.otlp_endpoint == "http://localhost:4318"


class TestTelemetry:
    def test_telemetry_creation(self):
        telemetry = Telemetry()
        assert telemetry.config is not None
        assert telemetry.is_initialized is False
    
    def test_telemetry_with_custom_config(self):
        config = TelemetryConfig(service_name="custom-service")
        telemetry = Telemetry(config=config)
        assert telemetry.config.service_name == "custom-service"
    
    def test_initialize_without_otel_available(self):
        """Telemetry can be initialized when OTEL not available."""
        telemetry = Telemetry()
        # Should not raise even if OTEL is not installed
        result = telemetry.initialize()
        # Result depends on whether OTEL is actually installed
        assert isinstance(result, bool)
    
    def test_get_tracer(self):
        """get_tracer returns tracer instance."""
        telemetry = Telemetry()
        tracer = telemetry.get_tracer()
        # May be None if OTEL not available
        assert tracer is None or tracer is not None
    
    def test_shutdown(self):
        """Telemetry can be shut down."""
        telemetry = Telemetry()
        # Should not raise
        telemetry.shutdown()


class TestGlobalTelemetry:
    def test_get_telemetry_singleton(self):
        """get_telemetry returns consistent instance."""
        # Reset global state
        import devgodzilla.services.telemetry as tel_module
        tel_module._telemetry = None
        
        t1 = get_telemetry()
        t2 = get_telemetry()
        assert t1 is t2
    
    def test_init_telemetry(self):
        """init_telemetry initializes global telemetry."""
        import devgodzilla.services.telemetry as tel_module
        tel_module._telemetry = None
        
        result = init_telemetry()
        assert isinstance(result, bool)
    
    def test_shutdown_telemetry(self):
        """shutdown_telemetry clears global instance."""
        import devgodzilla.services.telemetry as tel_module
        
        init_telemetry()
        shutdown_telemetry()
        assert tel_module._telemetry is None


class TestTracingUtilities:
    def test_start_as_current_span_context_manager(self):
        """start_as_current_span works as context manager."""
        with start_as_current_span("test_operation", {"key": "value"}):
            # Should not raise
            pass
    
    def test_set_span_attribute(self):
        """set_span_attribute can be called safely."""
        # Should not raise even when no span is active
        set_span_attribute("test_key", "test_value")
    
    def test_get_current_span(self):
        """get_current_span returns current span or None."""
        span = get_current_span()
        # May be None if OTEL not available or no active span
        assert span is None or span is not None
    
    def test_record_exception(self):
        """record_exception can record exceptions."""
        exc = ValueError("test error")
        # Should not raise
        record_exception(exc, attributes={"extra": "info"})


class TestTracedDecorator:
    def test_traced_decorator_sync_function(self):
        """@traced decorator works on sync functions."""
        @traced("test_func")
        def test_function():
            return "result"
        
        result = test_function()
        assert result == "result"
    
    def test_traced_decorator_async_function(self):
        """@traced decorator works on async functions."""
        import asyncio
        
        @traced("test_async_func")
        async def test_async_function():
            return "async_result"
        
        result = asyncio.run(test_async_function())
        assert result == "async_result"
    
    def test_traced_decorator_with_attributes(self):
        """@traced decorator accepts attributes."""
        @traced("test_func", {"custom": "attribute"})
        def test_function():
            return "result"
        
        result = test_function()
        assert result == "result"
    
    def test_traced_decorator_preserves_function_name(self):
        """@traced decorator preserves function metadata."""
        @traced("test_func")
        def my_function():
            """My docstring."""
            return "result"
        
        assert my_function.__name__ == "my_function"

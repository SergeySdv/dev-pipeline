"""
DevGodzilla OpenTelemetry Tracing

Provides distributed tracing initialization and utilities for the DevGodzilla API
and service layer.
"""

from contextlib import contextmanager
from typing import Any, Callable, Optional

from devgodzilla.logging import get_logger

logger = get_logger(__name__)

# Try to import OpenTelemetry components
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
    from opentelemetry.trace import Status, StatusCode, get_tracer
    from opentelemetry.util.types import Attributes

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore
    FastAPIInstrumentor = None  # type: ignore
    HTTPXClientInstrumentor = None  # type: ignore
    RedisInstrumentor = None  # type: ignore
    RequestsInstrumentor = None  # type: ignore
    Resource = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    ConsoleSpanExporter = None  # type: ignore
    ParentBasedTraceIdRatio = None  # type: ignore
    Status = None  # type: ignore
    StatusCode = None  # type: ignore
    get_tracer = None  # type: ignore
    Attributes = None  # type: ignore


class TelemetryConfig:
    """Configuration for OpenTelemetry tracing."""

    def __init__(
        self,
        service_name: str = "devgodzilla",
        service_version: str = "0.1.0",
        environment: str = "development",
        otlp_endpoint: Optional[str] = None,
        sample_rate: float = 1.0,
        enable_console_export: bool = False,
        enable_fastapi_instrumentation: bool = True,
        enable_httpx_instrumentation: bool = True,
        enable_redis_instrumentation: bool = True,
        enable_requests_instrumentation: bool = True,
    ):
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.otlp_endpoint = otlp_endpoint
        self.sample_rate = sample_rate
        self.enable_console_export = enable_console_export
        self.enable_fastapi_instrumentation = enable_fastapi_instrumentation
        self.enable_httpx_instrumentation = enable_httpx_instrumentation
        self.enable_redis_instrumentation = enable_redis_instrumentation
        self.enable_requests_instrumentation = enable_requests_instrumentation


class Telemetry:
    """
    OpenTelemetry tracing manager for DevGodzilla.

    Handles initialization, configuration, and lifecycle of tracing components.
    """

    def __init__(self, config: Optional[TelemetryConfig] = None):
        self.config = config or TelemetryConfig()
        self._tracer_provider: Optional[Any] = None
        self._initialized = False

    @property
    def is_available(self) -> bool:
        """Check if OpenTelemetry is available."""
        return OTEL_AVAILABLE

    @property
    def is_initialized(self) -> bool:
        """Check if telemetry has been initialized."""
        return self._initialized

    def initialize(self) -> bool:
        """
        Initialize OpenTelemetry tracing.

        Returns True if initialization succeeded, False otherwise.
        """
        if not OTEL_AVAILABLE:
            logger.warning(
                "telemetry_unavailable",
                extra={"reason": "opentelemetry packages not installed"},
            )
            return False

        if self._initialized:
            logger.debug("telemetry_already_initialized")
            return True

        try:
            # Create resource with service information
            resource = Resource.create(
                {
                    "service.name": self.config.service_name,
                    "service.version": self.config.service_version,
                    "deployment.environment": self.config.environment,
                }
            )

            # Create tracer provider with sampling
            sampler = ParentBasedTraceIdRatio(self.config.sample_rate)
            self._tracer_provider = TracerProvider(
                resource=resource,
                sampler=sampler,
            )

            # Add OTLP exporter if endpoint is configured
            if self.config.otlp_endpoint:
                otlp_exporter = OTLPSpanExporter(endpoint=self.config.otlp_endpoint)
                self._tracer_provider.add_span_processor(
                    BatchSpanProcessor(otlp_exporter)
                )
                logger.info(
                    "telemetry_otlp_configured",
                    extra={"endpoint": self.config.otlp_endpoint},
                )

            # Add console exporter if enabled
            if self.config.enable_console_export:
                console_exporter = ConsoleSpanExporter()
                self._tracer_provider.add_span_processor(
                    BatchSpanProcessor(console_exporter)
                )
                logger.info("telemetry_console_export_enabled")

            # Set global tracer provider
            trace.set_tracer_provider(self._tracer_provider)

            # Auto-instrument libraries
            self._instrument_libraries()

            self._initialized = True
            logger.info(
                "telemetry_initialized",
                extra={
                    "service_name": self.config.service_name,
                    "sample_rate": self.config.sample_rate,
                },
            )
            return True

        except Exception as e:
            logger.error(
                "telemetry_init_failed",
                extra={"error": str(e)},
            )
            return False

    def _instrument_libraries(self) -> None:
        """Auto-instrument supported libraries."""
        if not OTEL_AVAILABLE:
            return

        # Instrument httpx
        if self.config.enable_httpx_instrumentation and HTTPXClientInstrumentor:
            try:
                HTTPXClientInstrumentor().instrument()
                logger.debug("telemetry_httpx_instrumented")
            except Exception as e:
                logger.warning(
                    "telemetry_httpx_instrumentation_failed",
                    extra={"error": str(e)},
                )

        # Instrument redis
        if self.config.enable_redis_instrumentation and RedisInstrumentor:
            try:
                RedisInstrumentor().instrument()
                logger.debug("telemetry_redis_instrumented")
            except Exception as e:
                logger.warning(
                    "telemetry_redis_instrumentation_failed",
                    extra={"error": str(e)},
                )

        # Instrument requests
        if self.config.enable_requests_instrumentation and RequestsInstrumentor:
            try:
                RequestsInstrumentor().instrument()
                logger.debug("telemetry_requests_instrumented")
            except Exception as e:
                logger.warning(
                    "telemetry_requests_instrumentation_failed",
                    extra={"error": str(e)},
                )

    def instrument_fastapi(self, app: Any) -> bool:
        """
        Instrument a FastAPI application.

        Args:
            app: FastAPI application instance

        Returns True if instrumentation succeeded, False otherwise.
        """
        if not OTEL_AVAILABLE or not FastAPIInstrumentor:
            logger.warning(
                "telemetry_fastapi_instrumentation_unavailable",
                extra={"reason": "opentelemetry-instrumentation-fastapi not installed"},
            )
            return False

        if not self.config.enable_fastapi_instrumentation:
            return False

        try:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("telemetry_fastapi_instrumented")
            return True
        except Exception as e:
            logger.error(
                "telemetry_fastapi_instrumentation_failed",
                extra={"error": str(e)},
            )
            return False

    def get_tracer(self, name: Optional[str] = None) -> Optional[Any]:
        """
        Get a tracer instance.

        Args:
            name: Optional tracer name (defaults to service name)

        Returns Tracer instance or None if not available.
        """
        if not OTEL_AVAILABLE or not get_tracer:
            return None

        return get_tracer(name or self.config.service_name)

    def shutdown(self) -> None:
        """Shutdown the tracer provider and flush remaining spans."""
        if self._tracer_provider:
            try:
                self._tracer_provider.shutdown()
                logger.info("telemetry_shutdown_complete")
            except Exception as e:
                logger.error(
                    "telemetry_shutdown_failed",
                    extra={"error": str(e)},
                )


# Global telemetry instance
_telemetry: Optional[Telemetry] = None


def get_telemetry() -> Telemetry:
    """Get the global telemetry instance."""
    global _telemetry
    if _telemetry is None:
        _telemetry = Telemetry()
    return _telemetry


def init_telemetry(config: Optional[TelemetryConfig] = None) -> bool:
    """
    Initialize global telemetry.

    Args:
        config: Optional telemetry configuration

    Returns True if initialization succeeded.
    """
    global _telemetry
    _telemetry = Telemetry(config)
    return _telemetry.initialize()


def shutdown_telemetry() -> None:
    """Shutdown global telemetry."""
    global _telemetry
    if _telemetry:
        _telemetry.shutdown()
        _telemetry = None


# Tracing utilities
def get_current_span() -> Optional[Any]:
    """Get the current active span, or None if not available."""
    if not OTEL_AVAILABLE:
        return None
    return trace.get_current_span()


def get_current_span_context() -> Optional[Any]:
    """Get the current span context, or None if not available."""
    if not OTEL_AVAILABLE:
        return None
    ctx = trace.get_current()
    return ctx


def set_span_attribute(key: str, value: Any) -> None:
    """Set an attribute on the current span."""
    if not OTEL_AVAILABLE:
        return
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_attribute(key, value)


def set_span_attributes(attributes: dict) -> None:
    """Set multiple attributes on the current span."""
    if not OTEL_AVAILABLE:
        return
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def record_exception(exc: Exception, attributes: Optional[dict] = None) -> None:
    """Record an exception on the current span."""
    if not OTEL_AVAILABLE:
        return
    span = trace.get_current_span()
    if span and span.is_recording():
        span.record_exception(exc, attributes=attributes)
        span.set_status(Status(StatusCode.ERROR, str(exc)))


def set_span_status(status_code: str, description: Optional[str] = None) -> None:
    """Set the status of the current span."""
    if not OTEL_AVAILABLE:
        return
    span = trace.get_current_span()
    if span and span.is_recording():
        code = (
            StatusCode.OK
            if status_code.lower() == "ok"
            else StatusCode.ERROR
            if status_code.lower() == "error"
            else StatusCode.UNSET
        )
        span.set_status(Status(code, description))


@contextmanager
def start_as_current_span(
    name: str,
    attributes: Optional[dict] = None,
    kind: Optional[Any] = None,
):
    """
    Context manager to start a new span as the current span.

    Usage:
        with start_as_current_span("my_operation", {"key": "value"}):
            # do work
    """
    if not OTEL_AVAILABLE:
        yield None
        return

    tracer = get_telemetry().get_tracer()
    if not tracer:
        yield None
        return

    span_kwargs: dict = {}
    if attributes:
        span_kwargs["attributes"] = attributes
    if kind is not None:
        span_kwargs["kind"] = kind

    with tracer.start_as_current_span(name, **span_kwargs) as span:
        yield span


def traced(
    name: Optional[str] = None,
    attributes: Optional[dict] = None,
) -> Callable:
    """
    Decorator to trace a function.

    Usage:
        @traced("my_function", {"custom": "attribute"})
        def my_function():
            pass
    """

    def decorator(func: Callable) -> Callable:
        if not OTEL_AVAILABLE:
            return func

        import functools

        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with start_as_current_span(span_name, attributes):
                return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with start_as_current_span(span_name, attributes):
                return await func(*args, **kwargs)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator

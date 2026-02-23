"""Integration tests for platform services."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from devgodzilla.services.health import HealthChecker, HealthStatus, ComponentHealth
from devgodzilla.services.events import (
    EventBus, Event, 
    StepStarted, StepCompleted, StepFailed,
    ProtocolStarted, ProtocolCompleted,
)


class TestPlatformServicesIntegration:
    """Tests for platform services working together."""
    
    @pytest.fixture
    def event_bus(self):
        return EventBus()


class TestEventBusIntegration:
    """Tests for EventBus pub/sub functionality."""
    
    @pytest.fixture
    def event_bus(self):
        return EventBus()
    
    def test_event_bus_subscribe_publish(self, event_bus):
        """EventBus pub/sub works correctly."""
        received = []
        
        def handler(event):
            received.append(event)
        
        event_bus.add_handler(None, handler)  # Wildcard handler
        event_bus.publish(StepStarted(step_run_id=1, step_name="Test"))
        
        assert len(received) == 1
    
    def test_event_bus_type_specific_handler(self, event_bus):
        """Can subscribe to specific event types."""
        step_events = []
        
        def step_handler(event):
            step_events.append(event)
        
        event_bus.add_handler(StepStarted, step_handler)
        event_bus.publish(StepStarted(step_run_id=1, step_name="Test"))
        event_bus.publish(ProtocolStarted(protocol_run_id=1, protocol_name="Protocol"))
        
        # Should only receive StepStarted
        assert len(step_events) == 1
        assert isinstance(step_events[0], StepStarted)
    
    def test_event_bus_decorator(self, event_bus):
        """Decorator subscription works."""
        received = []
        
        @event_bus.subscribe(StepCompleted)
        def handler(event):
            received.append(event)
        
        event_bus.publish(StepCompleted(step_run_id=1, step_name="Done", summary="Success"))
        
        assert len(received) == 1
    
    def test_event_bus_clear(self, event_bus):
        """Can clear all handlers."""
        received = []
        
        def handler(event):
            received.append(event)
        
        event_bus.add_handler(None, handler)
        event_bus.clear()
        event_bus.publish(StepStarted(step_run_id=1, step_name="Test"))
        
        assert len(received) == 0
    
    @pytest.mark.asyncio
    async def test_event_bus_async_publish(self, event_bus):
        """Async publish works correctly."""
        received = []
        
        def handler(event):
            received.append(event)
        
        event_bus.add_handler(None, handler)
        await event_bus.publish_async(StepStarted(step_run_id=1, step_name="Async"))
        
        assert len(received) == 1


class TestHealthCheckerIntegration:
    """Tests for HealthChecker functionality."""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.list_projects.return_value = []
        return db
    
    @pytest.fixture
    def mock_windmill(self):
        wm = MagicMock()
        wm.health_check.return_value = True
        return wm
    
    @pytest.fixture
    def mock_registry(self):
        reg = MagicMock()
        reg.check_all_available.return_value = {}
        reg.list_all.return_value = []
        return reg
    
    def test_health_checker_sync(self, mock_db, mock_windmill, mock_registry):
        """HealthChecker sync check works."""
        checker = HealthChecker(
            db=mock_db,
            windmill=mock_windmill,
            agent_registry=mock_registry
        )
        
        status = checker.check_all_sync()
        
        assert status is not None
        assert hasattr(status, "components")
        assert hasattr(status, "status")
    
    @pytest.mark.asyncio
    async def test_health_checker_async(self, mock_db, mock_windmill, mock_registry):
        """HealthChecker async check works."""
        checker = HealthChecker(
            db=mock_db,
            windmill=mock_windmill,
            agent_registry=mock_registry
        )
        
        status = await checker.check_all()
        
        assert status is not None
        assert hasattr(status, "components")
        assert "database" in status.components
        assert "windmill" in status.components
        assert "agents" in status.components
    
    @pytest.mark.asyncio
    async def test_health_checker_with_unavailable_windmill(self, mock_db, mock_registry):
        """HealthChecker handles unavailable Windmill."""
        mock_windmill = MagicMock()
        mock_windmill.health_check.side_effect = Exception("Connection refused")
        
        checker = HealthChecker(
            db=mock_db,
            windmill=mock_windmill,
            agent_registry=mock_registry
        )
        
        status = await checker.check_all()
        
        assert status.components["windmill"].status == "error"
    
    @pytest.mark.asyncio
    async def test_health_checker_specific_agent(self, mock_db, mock_windmill, mock_registry):
        """Can check specific agent health."""
        # Setup mock engine
        mock_engine = MagicMock()
        mock_engine.check_availability.return_value = True
        mock_engine.metadata.kind = MagicMock(value="cli")
        mock_registry.get.return_value = mock_engine
        
        checker = HealthChecker(
            db=mock_db,
            windmill=mock_windmill,
            agent_registry=mock_registry
        )
        
        result = await checker.check_agent("test-agent")
        
        assert result is not None
        assert hasattr(result, "status")


class TestEventTypes:
    """Tests for various event types."""
    
    def test_step_event_creation(self):
        """Step events can be created with proper attributes."""
        event = StepStarted(
            step_run_id=1,
            protocol_run_id=100,
            step_name="Implement feature",
            engine_id="opencode"
        )
        
        assert event.step_run_id == 1
        assert event.step_name == "Implement feature"
        assert event.engine_id == "opencode"
    
    def test_protocol_event_creation(self):
        """Protocol events can be created with proper attributes."""
        event = ProtocolCompleted(
            protocol_run_id=1,
            project_id=10
        )
        
        assert event.protocol_run_id == 1
        assert event.project_id == 10
    
    def test_event_metadata(self):
        """Events can carry metadata."""
        event = StepFailed(
            step_run_id=1,
            protocol_run_id=100,
            step_name="Test",
            error="Test failed",
            retryable=True
        )
        
        assert event.error == "Test failed"
        assert event.retryable is True
    
    def test_event_timestamp(self):
        """Events have timestamps."""
        from datetime import datetime
        
        event = StepStarted(step_run_id=1, step_name="Test")
        
        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)


class TestHealthStatusSerialization:
    """Tests for health status serialization."""
    
    def test_component_health_creation(self):
        """ComponentHealth can be created."""
        health = ComponentHealth(
            name="database",
            status="ok",
            latency_ms=50,
            details={"driver": "sqlite"}
        )
        
        assert health.name == "database"
        assert health.status == "ok"
        assert health.latency_ms == 50
    
    def test_health_status_creation(self):
        """HealthStatus can be created."""
        from datetime import datetime, timezone
        
        status = HealthStatus(
            status="ok",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc),
            components={
                "database": ComponentHealth(name="database", status="ok")
            },
            checks_passed=1,
            checks_failed=0
        )
        
        assert status.status == "ok"
        assert status.checks_passed == 1

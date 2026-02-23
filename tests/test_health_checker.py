"""Tests for HealthChecker service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from devgodzilla.services.health import (
    HealthChecker, HealthStatus, ComponentHealth, health_status_to_dict
)


class TestComponentHealth:
    def test_component_health_creation(self):
        health = ComponentHealth(
            name="database",
            status="ok",
            message="Connected",
            latency_ms=5
        )
        assert health.name == "database"
        assert health.status == "ok"
        assert health.message == "Connected"
        assert health.latency_ms == 5
    
    def test_component_health_minimal(self):
        health = ComponentHealth(name="test", status="ok")
        assert health.name == "test"
        assert health.message is None
        assert health.latency_ms is None
        assert health.details == {}


class TestHealthStatus:
    def test_health_status_creation(self):
        from datetime import datetime, timezone
        
        status = HealthStatus(
            status="ok",
            version="1.0.0",
            timestamp=datetime.now(timezone.utc),
            components={},
            checks_passed=1,
            checks_failed=0
        )
        assert status.status == "ok"
        assert status.version == "1.0.0"
        assert status.checks_passed == 1


class TestHealthChecker:
    @pytest.fixture
    def mock_db(self):
        mock = MagicMock()
        mock.list_projects = MagicMock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_windmill(self):
        mock = MagicMock()
        mock.health_check = MagicMock(return_value=True)
        return mock
    
    @pytest.fixture
    def mock_agent_registry(self):
        mock = MagicMock()
        mock.list_all = MagicMock(return_value=[])
        mock.check_all_available = MagicMock(return_value={})
        return mock
    
    @pytest.fixture
    def checker(self, mock_db, mock_windmill, mock_agent_registry):
        return HealthChecker(
            db=mock_db,
            windmill=mock_windmill,
            agent_registry=mock_agent_registry
        )
    
    @pytest.fixture
    def checker_no_windmill(self, mock_db, mock_agent_registry):
        return HealthChecker(
            db=mock_db,
            windmill=None,
            agent_registry=mock_agent_registry
        )
    
    def test_checker_creation(self, checker):
        assert checker.db is not None
        assert checker.windmill is not None
        assert checker.agent_registry is not None
    
    @pytest.mark.asyncio
    async def test_check_all(self, checker):
        """check_all returns HealthStatus."""
        status = await checker.check_all()
        
        assert isinstance(status, HealthStatus)
        assert status.status in ("ok", "degraded", "error")
        assert "database" in status.components
        assert "windmill" in status.components
        assert "agents" in status.components
    
    @pytest.mark.asyncio
    async def test_check_all_no_windmill(self, checker_no_windmill):
        """check_all works without windmill client."""
        status = await checker_no_windmill.check_all()
        
        assert isinstance(status, HealthStatus)
        assert status.components["windmill"].message == "disabled"
    
    @pytest.mark.asyncio
    async def test_check_database_healthy(self, checker, mock_db):
        """Database check returns healthy status."""
        mock_db.list_projects = MagicMock(return_value=[])
        
        result = await checker._check_database()
        
        assert result.status == "ok"
    
    @pytest.mark.asyncio
    async def test_check_database_error(self, checker, mock_db):
        """Database check handles errors."""
        mock_db.list_projects = MagicMock(side_effect=Exception("DB error"))
        
        result = await checker._check_database()
        
        assert result.status == "error"
        assert "DB error" in result.message
    
    @pytest.mark.asyncio
    async def test_check_windmill_healthy(self, checker, mock_windmill):
        """Windmill check returns healthy status."""
        mock_windmill.health_check = MagicMock(return_value=True)
        
        result = await checker._check_windmill()
        
        assert result.status == "ok"
    
    @pytest.mark.asyncio
    async def test_check_windmill_unhealthy(self, checker, mock_windmill):
        """Windmill check handles unhealthy status."""
        mock_windmill.health_check = MagicMock(return_value=False)
        
        result = await checker._check_windmill()
        
        assert result.status == "error"
    
    @pytest.mark.asyncio
    async def test_check_agents_empty(self, checker, mock_agent_registry):
        """Agent check handles empty registry."""
        mock_agent_registry.list_all = MagicMock(return_value=[])
        
        result = await checker._check_agents()
        
        assert result.status == "ok"
    
    @pytest.mark.asyncio
    async def test_check_agent(self, checker, mock_agent_registry):
        """check_agent returns specific agent health."""
        mock_engine = MagicMock()
        mock_engine.check_availability = MagicMock(return_value=True)
        mock_engine.metadata.id = "test-agent"
        mock_engine.metadata.kind.value = "cli"
        mock_agent_registry.get = MagicMock(return_value=mock_engine)
        
        result = await checker.check_agent("test-agent")
        
        assert result.status == "ok"
    
    def test_check_all_sync(self, checker):
        """check_all_sync returns HealthStatus."""
        status = checker.check_all_sync()
        
        assert isinstance(status, HealthStatus)
        assert status.status in ("ok", "degraded", "error")


class TestHealthStatusToDict:
    def test_health_status_to_dict(self):
        from datetime import datetime, timezone
        
        status = HealthStatus(
            status="ok",
            version="1.0.0",
            timestamp=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            components={
                "db": ComponentHealth(name="db", status="ok")
            },
            checks_passed=1,
            checks_failed=0
        )
        
        result = health_status_to_dict(status)
        
        assert result["status"] == "ok"
        assert result["version"] == "1.0.0"
        assert "components" in result
        assert result["checks_passed"] == 1
        assert result["checks_failed"] == 0
    
    def test_health_status_to_dict_with_components(self):
        from datetime import datetime, timezone
        
        status = HealthStatus(
            status="degraded",
            version="0.1.0",
            timestamp=datetime.now(timezone.utc),
            components={
                "database": ComponentHealth(
                    name="database",
                    status="ok",
                    latency_ms=5
                ),
                "windmill": ComponentHealth(
                    name="windmill",
                    status="error",
                    message="Connection failed"
                )
            },
            checks_passed=1,
            checks_failed=1
        )
        
        result = health_status_to_dict(status)
        
        assert result["status"] == "degraded"
        assert "database" in result["components"]
        assert "windmill" in result["components"]
        assert result["components"]["windmill"]["status"] == "error"

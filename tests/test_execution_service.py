from pathlib import Path
from unittest.mock import patch, MagicMock

from tasksgodzilla.domain import ProtocolStatus, StepStatus
from tasksgodzilla.services import ExecutionService
from tasksgodzilla.storage import Database


def test_execute_step_service_exists(tmp_path):
    """Test that ExecutionService can be instantiated and has execute_step method."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    service = ExecutionService(db=db)
    
    # Verify service has the execute_step method
    assert hasattr(service, "execute_step")
    assert callable(service.execute_step)


def test_execute_step_requires_database(tmp_path):
    """Test that ExecutionService requires a database."""
    db = Database(tmp_path / "test.db")
    db.init_schema()
    
    service = ExecutionService(db=db)
    
    # Verify service has database
    assert service.db is not None
    assert service.db == db

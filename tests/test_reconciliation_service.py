"""Tests for ReconciliationService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from devgodzilla.services.reconciliation import (
    ReconciliationService, ReconciliationReport, ReconciliationDetail,
    ReconciliationAction, ProtocolReconciliation, StepReconciliation
)


class TestReconciliationDetail:
    def test_reconciliation_detail_creation(self):
        detail = ReconciliationDetail(
            step_run_id=123,
            step_name="test_step",
            protocol_run_id=456,
            db_status="RUNNING",
            windmill_status="COMPLETED",
            action=ReconciliationAction.AUTO_FIXED
        )
        assert detail.step_run_id == 123
        assert detail.action == ReconciliationAction.AUTO_FIXED
        assert detail.message is None
    
    def test_reconciliation_detail_with_message(self):
        detail = ReconciliationDetail(
            step_run_id=1,
            step_name="step",
            protocol_run_id=2,
            db_status="PENDING",
            windmill_status="RUNNING",
            action=ReconciliationAction.NO_CHANGE,
            message="Statuses match"
        )
        assert detail.message == "Statuses match"


class TestReconciliationReport:
    def test_reconciliation_report_creation(self):
        report = ReconciliationReport(
            total_checked=10,
            mismatches_found=2,
            auto_fixed=1,
            requires_manual=1
        )
        assert report.total_checked == 10
        assert report.mismatches_found == 2
        assert report.details == []
    
    def test_reconciliation_report_with_details(self):
        detail = ReconciliationDetail(
            step_run_id=1,
            step_name="step",
            protocol_run_id=2,
            db_status="RUNNING",
            windmill_status="COMPLETED",
            action=ReconciliationAction.AUTO_FIXED
        )
        report = ReconciliationReport(
            total_checked=1,
            mismatches_found=1,
            auto_fixed=1,
            requires_manual=0,
            details=[detail]
        )
        assert len(report.details) == 1


class TestReconciliationService:
    @pytest.fixture
    def mock_context(self):
        context = MagicMock()
        context.request_id = "test-request"
        return context
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    @pytest.fixture
    def mock_windmill(self):
        return MagicMock()
    
    @pytest.fixture
    def service(self, mock_context, mock_db, mock_windmill):
        return ReconciliationService(
            context=mock_context,
            db=mock_db,
            windmill=mock_windmill
        )
    
    def test_service_creation(self, service):
        assert service.db is not None
        assert service.windmill is not None
    
    @pytest.mark.asyncio
    async def test_reconcile_runs_empty(self, service, mock_db):
        """Reconciliation with no active runs returns empty report."""
        mock_db.list_all_protocol_runs.return_value = []
        
        report = await service.reconcile_runs()
        
        assert report.total_checked == 0
        assert report.mismatches_found == 0
    
    @pytest.mark.asyncio
    async def test_reconcile_runs_no_windmill(self, mock_context, mock_db):
        """Reconciliation without windmill client handles gracefully."""
        service = ReconciliationService(
            context=mock_context,
            db=mock_db,
            windmill=None
        )
        mock_db.list_all_protocol_runs.return_value = []
        
        report = await service.reconcile_runs()
        
        assert isinstance(report, ReconciliationReport)
    
    @pytest.mark.asyncio
    async def test_reconcile_protocol(self, service, mock_db, mock_windmill):
        """Reconcile single protocol returns protocol reconciliation."""
        mock_protocol = MagicMock()
        mock_protocol.protocol_name = "test_protocol"
        mock_protocol.status = "RUNNING"
        mock_db.get_protocol_run.return_value = mock_protocol
        mock_db.list_step_runs.return_value = []
        
        result = await service.reconcile_protocol(protocol_run_id=1)
        
        assert isinstance(result, ProtocolReconciliation)
        assert result.protocol_run_id == 1
    
    @pytest.mark.asyncio
    async def test_reconcile_step(self, service, mock_db, mock_windmill):
        """Reconcile single step returns step reconciliation."""
        mock_step = MagicMock()
        mock_step.id = 123
        mock_step.step_name = "test_step"
        mock_step.protocol_run_id = 456
        mock_step.status = "RUNNING"
        mock_step.windmill_job_id = "job-789"
        mock_db.get_step_run.return_value = mock_step
        mock_db.list_job_runs.return_value = []
        
        result = await service.reconcile_step(step_run_id=123)
        
        assert isinstance(result, StepReconciliation)
        assert result.step_run_id == 123
    
    def test_reconciliation_action_enum(self):
        """ReconciliationAction enum has expected values."""
        assert ReconciliationAction.NO_CHANGE.value == "no_change"
        assert ReconciliationAction.AUTO_FIXED.value == "auto_fixed"
        assert ReconciliationAction.MANUAL_REQUIRED.value == "manual_required"
        assert ReconciliationAction.ERROR.value == "error"

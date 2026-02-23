"""
DevGodzilla Services

Core service layer for platform operations.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devgodzilla.services.base import Service, ServiceContext
    from devgodzilla.services.events import EventBus, get_event_bus
    from devgodzilla.services.git import GitService
    from devgodzilla.services.clarifier import ClarifierService
    from devgodzilla.services.policy import PolicyService, EffectivePolicy, Finding
    from devgodzilla.services.planning import PlanningService, PlanningResult
    from devgodzilla.services.constitution import ConstitutionService, Constitution, Article
    from devgodzilla.services.orchestrator import OrchestratorService, OrchestratorResult, OrchestratorMode
    from devgodzilla.services.execution import ExecutionService, ExecutionResult, StepResolution
    from devgodzilla.services.quality import QualityService, QAResult, QAVerdict
    from devgodzilla.services.specification import SpecificationService, SpecifyResult, PlanResult, TasksResult
    from devgodzilla.services.telemetry import (
        Telemetry,
        TelemetryConfig,
        get_telemetry,
        init_telemetry,
        shutdown_telemetry,
        start_as_current_span,
        traced,
        set_span_attribute,
        set_span_attributes,
        record_exception,
    )
    from devgodzilla.services.error_classification import (
        ErrorAction,
        ErrorClassification,
        ErrorClassifier,
        AgentUnavailableError,
        ExecutionBlockedError,
        TimeoutError,
        TransientError,
        classify_error,
        get_error_classifier,
    )
    from devgodzilla.services.reconciliation import (
        ReconciliationService,
        ReconciliationReport,
        ReconciliationDetail,
        ProtocolReconciliation,
        StepReconciliation,
        ReconciliationAction,
    )

__all__ = [
    # Base
    "Service",
    "ServiceContext",
    # Events
    "EventBus",
    "get_event_bus",
    # Git
    "GitService",
    # Clarifier
    "ClarifierService",
    # Policy
    "PolicyService",
    "EffectivePolicy",
    "Finding",
    # Planning
    "PlanningService",
    "PlanningResult",
    # Specification
    "SpecificationService",
    "SpecifyResult",
    "PlanResult",
    "TasksResult",
    # Constitution
    "ConstitutionService",
    "Constitution",
    "Article",
    # Orchestrator
    "OrchestratorService",
    "OrchestratorResult",
    "OrchestratorMode",
    # Execution
    "ExecutionService",
    "ExecutionResult",
    "StepResolution",
    # Quality
    "QualityService",
    "QAResult",
    "QAVerdict",
    # Telemetry
    "Telemetry",
    "TelemetryConfig",
    "get_telemetry",
    "init_telemetry",
    "shutdown_telemetry",
    "start_as_current_span",
    "traced",
    "set_span_attribute",
    "set_span_attributes",
    "record_exception",
    # Error Classification
    "ErrorAction",
    "ErrorClassification",
    "ErrorClassifier",
    "AgentUnavailableError",
    "ExecutionBlockedError",
    "TimeoutError",
    "TransientError",
    "classify_error",
    "get_error_classifier",
    # Reconciliation
    "ReconciliationService",
    "ReconciliationReport",
    "ReconciliationDetail",
    "ProtocolReconciliation",
    "StepReconciliation",
    "ReconciliationAction",
]

_EXPORTS = {
    "Service": "devgodzilla.services.base",
    "ServiceContext": "devgodzilla.services.base",
    "EventBus": "devgodzilla.services.events",
    "get_event_bus": "devgodzilla.services.events",
    "GitService": "devgodzilla.services.git",
    "ClarifierService": "devgodzilla.services.clarifier",
    "PolicyService": "devgodzilla.services.policy",
    "EffectivePolicy": "devgodzilla.services.policy",
    "Finding": "devgodzilla.services.policy",
    "PlanningService": "devgodzilla.services.planning",
    "PlanningResult": "devgodzilla.services.planning",
    "SpecificationService": "devgodzilla.services.specification",
    "SpecifyResult": "devgodzilla.services.specification",
    "PlanResult": "devgodzilla.services.specification",
    "TasksResult": "devgodzilla.services.specification",
    "ConstitutionService": "devgodzilla.services.constitution",
    "Constitution": "devgodzilla.services.constitution",
    "Article": "devgodzilla.services.constitution",
    "OrchestratorService": "devgodzilla.services.orchestrator",
    "OrchestratorResult": "devgodzilla.services.orchestrator",
    "OrchestratorMode": "devgodzilla.services.orchestrator",
    "ExecutionService": "devgodzilla.services.execution",
    "ExecutionResult": "devgodzilla.services.execution",
    "StepResolution": "devgodzilla.services.execution",
    "QualityService": "devgodzilla.services.quality",
    "QAResult": "devgodzilla.services.quality",
    "QAVerdict": "devgodzilla.services.quality",
    # Telemetry
    "Telemetry": "devgodzilla.services.telemetry",
    "TelemetryConfig": "devgodzilla.services.telemetry",
    "get_telemetry": "devgodzilla.services.telemetry",
    "init_telemetry": "devgodzilla.services.telemetry",
    "shutdown_telemetry": "devgodzilla.services.telemetry",
    "start_as_current_span": "devgodzilla.services.telemetry",
    "traced": "devgodzilla.services.telemetry",
    "set_span_attribute": "devgodzilla.services.telemetry",
    "set_span_attributes": "devgodzilla.services.telemetry",
    "record_exception": "devgodzilla.services.telemetry",
    # Error Classification
    "ErrorAction": "devgodzilla.services.error_classification",
    "ErrorClassification": "devgodzilla.services.error_classification",
    "ErrorClassifier": "devgodzilla.services.error_classification",
    "AgentUnavailableError": "devgodzilla.services.error_classification",
    "ExecutionBlockedError": "devgodzilla.services.error_classification",
    "TimeoutError": "devgodzilla.services.error_classification",
    "TransientError": "devgodzilla.services.error_classification",
    "classify_error": "devgodzilla.services.error_classification",
    "get_error_classifier": "devgodzilla.services.error_classification",
    # Reconciliation
    "ReconciliationService": "devgodzilla.services.reconciliation",
    "ReconciliationReport": "devgodzilla.services.reconciliation",
    "ReconciliationDetail": "devgodzilla.services.reconciliation",
    "ProtocolReconciliation": "devgodzilla.services.reconciliation",
    "StepReconciliation": "devgodzilla.services.reconciliation",
    "ReconciliationAction": "devgodzilla.services.reconciliation",
}


def __getattr__(name: str):
    module_path = _EXPORTS.get(name)
    if not module_path:
        raise AttributeError(f"module {__name__} has no attribute {name}")
    module = import_module(module_path)
    return getattr(module, name)


def __dir__() -> list[str]:
    return sorted(__all__)

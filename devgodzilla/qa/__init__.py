"""
DevGodzilla Quality Assurance

Constitutional QA with spec-kit checklist integration.
Composable QA gates (TestGate, LintGate, ChecklistGate).
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from devgodzilla.qa.gates import (
        Gate,
        GateContext,
        GateResult,
        GateVerdict,
        Finding,
        TestGate,
        LintGate,
        TypeGate,
        ChecklistGate,
        FormatGate,
        CoverageGate,
        ConstitutionalGate,
        ConstitutionalSummaryGate,
        PromptQAGate,
        TestFirstGate,
    )
    from devgodzilla.qa.feedback import (
        FeedbackRouter,
        FeedbackAction,
        FeedbackRoute,
        RoutedFeedback,
        ErrorCategory,
        classify_error,
    )
    from devgodzilla.qa.report_generator import (
        ReportGenerator,
        QAReport,
        ReportSection,
    )
    from devgodzilla.qa.checklist_validator import (
        ChecklistValidator,
        ChecklistItem,
        ValidationResult,
    )

__all__ = [
    # Gates interface
    "Gate",
    "GateContext",
    "GateResult",
    "GateVerdict",
    "Finding",
    # Common gates
    "TestGate",
    "LintGate",
    "TypeGate",
    "ChecklistGate",
    "FormatGate",
    "CoverageGate",
    # Constitutional gates
    "ConstitutionalGate",
    "ConstitutionalSummaryGate",
    "PromptQAGate",
    "TestFirstGate",
    # Feedback routing
    "FeedbackRouter",
    "FeedbackAction",
    "FeedbackRoute",
    "RoutedFeedback",
    "ErrorCategory",
    "classify_error",
    # Report generation
    "ReportGenerator",
    "QAReport",
    "ReportSection",
    # Checklist validation
    "ChecklistValidator",
    "ChecklistItem",
    "ValidationResult",
]

_GATE_EXPORTS = {
    "Gate",
    "GateContext",
    "GateResult",
    "GateVerdict",
    "Finding",
    "TestGate",
    "LintGate",
    "TypeGate",
    "ChecklistGate",
    "FormatGate",
    "CoverageGate",
    "ConstitutionalGate",
    "ConstitutionalSummaryGate",
    "PromptQAGate",
    "TestFirstGate",
}
_FEEDBACK_EXPORTS = {
    "FeedbackRouter",
    "FeedbackAction",
    "FeedbackRoute",
    "RoutedFeedback",
    "ErrorCategory",
    "classify_error",
}
_REPORT_EXPORTS = {
    "ReportGenerator",
    "QAReport",
    "ReportSection",
}
_VALIDATOR_EXPORTS = {
    "ChecklistValidator",
    "ChecklistItem",
    "ValidationResult",
}


def __getattr__(name: str):
    if name in _GATE_EXPORTS:
        from devgodzilla.qa import gates as gates_module
        return getattr(gates_module, name)
    if name in _FEEDBACK_EXPORTS:
        from devgodzilla.qa import feedback as feedback_module
        return getattr(feedback_module, name)
    if name in _REPORT_EXPORTS:
        from devgodzilla.qa import report_generator as report_module
        return getattr(report_module, name)
    if name in _VALIDATOR_EXPORTS:
        from devgodzilla.qa import checklist_validator as validator_module
        return getattr(validator_module, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")


def __dir__() -> list[str]:
    return sorted(__all__)

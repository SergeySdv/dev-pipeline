"""
Run QA Script

Runs quality assurance checks on step output using constitutional gates.

Args:
    step_id: Task identifier
    step_output: Output from step execution
    constitution: Constitutional rules to check against

Returns:
    passed: Whether QA passed
    verdict: Overall verdict (pass, fail, warn)
    gate_results: Individual gate check results
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Import DevGodzilla QA if available
try:
    from devgodzilla.qa import QualityGate, run_gates
    from devgodzilla.db import get_database
    DEVGODZILLA_AVAILABLE = True
except ImportError:
    DEVGODZILLA_AVAILABLE = False


# Constitutional gates to check
CONSTITUTIONAL_GATES = [
    {
        "id": "article_1",
        "name": "Library-First",
        "description": "Prefer existing libraries over custom code",
        "severity": "warning",
    },
    {
        "id": "article_3",
        "name": "Test-First",
        "description": "Tests should be written alongside implementation",
        "severity": "error",
    },
    {
        "id": "article_5",
        "name": "Error Handling",
        "description": "Handle errors explicitly, never silently fail",
        "severity": "error",
    },
    {
        "id": "article_6",
        "name": "Security",
        "description": "No secrets committed, input validated",
        "severity": "error",
    },
    {
        "id": "article_7",
        "name": "Simplicity",
        "description": "Prefer simple solutions over clever ones",
        "severity": "warning",
    },
]


def main(
    step_id: str,
    step_output: dict = None,
    constitution: dict = None,
) -> dict:
    """Run QA checks on step output."""
    
    step_output = step_output or {}
    constitution = constitution or {}
    
    start_time = datetime.now()
    
    # Use DevGodzilla QA service if available
    if DEVGODZILLA_AVAILABLE:
        try:
            db = get_database()
            from devgodzilla.services import QualityService
            qa_service = QualityService(db)
            result = qa_service.run_qa(
                step_id=step_id,
                step_output=step_output,
                constitution=constitution,
            )
            return {
                "passed": result.passed,
                "verdict": result.verdict,
                "gate_results": result.gate_results,
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
            }
        except Exception as e:
            pass
    
    # Demo QA check
    return _demo_qa(step_id, step_output, start_time)


def _demo_qa(
    step_id: str,
    step_output: dict,
    start_time: datetime,
) -> dict:
    """Run demo QA checks."""
    
    gate_results = []
    errors = 0
    warnings = 0
    
    output_text = step_output.get("output", "")
    artifacts = step_output.get("artifacts", [])
    
    for gate in CONSTITUTIONAL_GATES:
        # Demo: Simple heuristic checks
        passed = True
        message = "Check passed"
        
        if gate["id"] == "article_3":
            # Check for test-related content
            if "test" not in output_text.lower():
                passed = False
                message = "No test-related output detected"
        
        elif gate["id"] == "article_5":
            # Check for error handling keywords
            if any(bad in output_text.lower() for bad in ["except: pass", "silent fail"]):
                passed = False
                message = "Potential silent error handling detected"
        
        elif gate["id"] == "article_6":
            # Check for potential secrets
            if any(secret in output_text.lower() for secret in ["password=", "api_key=", "secret="]):
                passed = False
                message = "Potential secret exposure detected"
        
        result = {
            "gate_id": gate["id"],
            "name": gate["name"],
            "passed": passed,
            "message": message,
            "severity": gate["severity"],
        }
        gate_results.append(result)
        
        if not passed:
            if gate["severity"] == "error":
                errors += 1
            else:
                warnings += 1
    
    # Determine overall verdict
    if errors > 0:
        verdict = "fail"
        passed = False
    elif warnings > 0:
        verdict = "warn"
        passed = True  # Warnings don't fail QA
    else:
        verdict = "pass"
        passed = True
    
    return {
        "passed": passed,
        "verdict": verdict,
        "gate_results": gate_results,
        "summary": {
            "total_gates": len(CONSTITUTIONAL_GATES),
            "passed": len(CONSTITUTIONAL_GATES) - errors - warnings,
            "errors": errors,
            "warnings": warnings,
        },
        "step_id": step_id,
        "duration_seconds": (datetime.now() - start_time).total_seconds(),
        "demo_mode": True,
    }

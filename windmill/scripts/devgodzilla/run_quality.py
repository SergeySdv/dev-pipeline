"""
Run Quality Script

Enhanced QA with constitutional gates, checklist validation, and code analysis.

Args:
    step_run_id: Step run ID from database
    step_output: Output from execute_step
    constitution_path: Path to constitution file

Returns:
    passed: Whether QA passed overall
    verdict: Overall verdict (pass, fail, warn)
    gate_results: Constitutional gate results
    checklist_result: Checklist validation results
    score: Quality score 0.0-1.0
"""

import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Import DevGodzilla services if available
try:
    from devgodzilla.db import get_database
    from devgodzilla.services import QualityService
    DEVGODZILLA_AVAILABLE = True
except ImportError:
    DEVGODZILLA_AVAILABLE = False


# Constitutional gates from architecture
CONSTITUTIONAL_GATES = [
    {
        "id": "article_1",
        "article": "I",
        "name": "Library-First Development",
        "description": "Prefer existing libraries over custom code",
        "blocking": False,
        "patterns": [
            (r"def\s+parse_json\s*\(", "Use pydantic or stdlib json"),
            (r"def\s+hash_password\s*\(", "Use bcrypt or argon2"),
            (r"class\s+\w*Validator\s*\(", "Consider pydantic for validation"),
        ],
    },
    {
        "id": "article_3",
        "article": "III",
        "name": "Test-First Development",
        "description": "Write tests before implementation",
        "blocking": True,
        "check": "has_tests",
    },
    {
        "id": "article_4",
        "article": "IV",
        "name": "Security by Default",
        "description": "Never commit secrets, validate all inputs",
        "blocking": True,
        "patterns": [
            (r"password\s*=\s*['\"][^'\"]+['\"]", "Potential hardcoded password"),
            (r"api_key\s*=\s*['\"][^'\"]+['\"]", "Potential hardcoded API key"),
            (r"secret\s*=\s*['\"][^'\"]+['\"]", "Potential hardcoded secret"),
        ],
    },
    {
        "id": "article_5",
        "article": "V",
        "name": "Error Handling",
        "description": "Handle errors explicitly",
        "blocking": True,
        "patterns": [
            (r"except:\s*pass", "Silent exception handling"),
            (r"except\s+Exception:\s*pass", "Silent exception handling"),
        ],
    },
    {
        "id": "article_7",
        "article": "VII",
        "name": "Simplicity",
        "description": "Prefer simple solutions",
        "blocking": False,
        "check": "complexity",
    },
    {
        "id": "article_9",
        "article": "IX",
        "name": "Integration Testing",
        "description": "Every feature must have integration tests",
        "blocking": True,
        "check": "has_integration_tests",
    },
]


def main(
    step_run_id: int,
    step_output: dict = None,
    constitution_path: str = "",
) -> dict:
    """Run comprehensive QA checks."""
    
    step_output = step_output or {}
    start_time = datetime.now()
    
    # Use DevGodzilla QA service if available
    if DEVGODZILLA_AVAILABLE:
        try:
            db = get_database()
            qa_service = QualityService(db)
            result = qa_service.run_for_step(step_run_id)
            return {
                "passed": result.verdict.passed,
                "verdict": "pass" if result.verdict.passed else "fail",
                "gate_results": [g.to_dict() for g in result.gate_results],
                "checklist_result": result.checklist_result.to_dict() if result.checklist_result else None,
                "score": result.verdict.score,
                "duration_seconds": (datetime.now() - start_time).total_seconds(),
            }
        except Exception as e:
            print(f"Warning: DevGodzilla QA service failed: {e}")
    
    # Fallback: Run demo QA
    return _run_demo_qa(step_run_id, step_output, constitution_path, start_time)


def _run_demo_qa(
    step_run_id: int,
    step_output: dict,
    constitution_path: str,
    start_time: datetime,
) -> dict:
    """Run demo QA checks."""
    
    output_text = step_output.get("output", "")
    artifacts = step_output.get("artifacts", [])
    
    gate_results = []
    total_score = 0.0
    blocking_failures = []
    
    for gate in CONSTITUTIONAL_GATES:
        result = _evaluate_gate(gate, output_text, artifacts)
        gate_results.append(result)
        
        if result["passed"]:
            total_score += 1.0
        elif result["status"] == "warning":
            total_score += 0.5
        
        if not result["passed"] and gate["blocking"]:
            blocking_failures.append(result)
    
    # Calculate overall score
    score = total_score / len(CONSTITUTIONAL_GATES) if CONSTITUTIONAL_GATES else 0.0
    
    # Determine verdict
    if blocking_failures:
        verdict = "fail"
        passed = False
    elif score < 0.7:
        verdict = "warn"
        passed = True
    else:
        verdict = "pass"
        passed = True
    
    # Generate report
    report = _generate_report(step_run_id, gate_results, passed, score)
    
    return {
        "passed": passed,
        "verdict": verdict,
        "gate_results": gate_results,
        "checklist_result": None,  # Would be populated with real checklist
        "score": round(score, 2),
        "blocking_failures": [f["gate_id"] for f in blocking_failures],
        "report": report,
        "step_run_id": step_run_id,
        "duration_seconds": (datetime.now() - start_time).total_seconds(),
    }


def _evaluate_gate(gate: dict, output_text: str, artifacts: list) -> dict:
    """Evaluate a single constitutional gate."""
    
    findings = []
    passed = True
    status = "passed"
    
    # Pattern-based checks
    if "patterns" in gate:
        for pattern, message in gate["patterns"]:
            matches = list(re.finditer(pattern, output_text, re.IGNORECASE))
            for match in matches:
                findings.append({
                    "code": f"CONST_{gate['article']}",
                    "message": message,
                    "matched": match.group(0)[:50],
                    "severity": "error" if gate["blocking"] else "warning",
                })
                if gate["blocking"]:
                    passed = False
                    status = "failed"
                else:
                    status = "warning"
    
    # Special check types
    if gate.get("check") == "has_tests":
        # Check for test-related keywords
        has_tests = any(x in output_text.lower() for x in ["test_", "pytest", "unittest", "@test"])
        if not has_tests:
            findings.append({
                "code": f"CONST_{gate['article']}_001",
                "message": "No test-related output detected",
                "severity": "error" if gate["blocking"] else "warning",
            })
            if gate["blocking"]:
                passed = False
                status = "failed"
    
    elif gate.get("check") == "has_integration_tests":
        has_integration = any(x in output_text.lower() for x in ["integration", "e2e", "end-to-end"])
        if not has_integration:
            findings.append({
                "code": f"CONST_{gate['article']}_001",
                "message": "No integration test indicators found",
                "severity": "warning",
            })
            status = "warning" if passed else status
    
    return {
        "gate_id": gate["id"],
        "article": gate["article"],
        "name": gate["name"],
        "passed": passed,
        "status": status,
        "blocking": gate["blocking"],
        "findings": findings,
    }


def _generate_report(
    step_run_id: int,
    gate_results: list,
    passed: bool,
    score: float,
) -> str:
    """Generate QA report in markdown."""
    
    status_icon = "✅" if passed else "❌"
    
    report = f"""# QA Report

**Step Run ID**: {step_run_id}
**Status**: {status_icon} {"PASSED" if passed else "FAILED"}
**Score**: {score:.0%}

## Constitutional Gate Results

| Article | Gate | Status | Findings |
|---------|------|--------|----------|
"""
    
    for gate in gate_results:
        status_icon = "✅" if gate["passed"] else ("⚠️" if gate["status"] == "warning" else "❌")
        finding_count = len(gate.get("findings", []))
        report += f"| {gate['article']} | {gate['name']} | {status_icon} | {finding_count} |\n"
    
    # List findings
    all_findings = []
    for gate in gate_results:
        for finding in gate.get("findings", []):
            all_findings.append({**finding, "gate": gate["name"]})
    
    if all_findings:
        report += "\n## Findings\n\n"
        for finding in all_findings:
            severity_icon = "❌" if finding["severity"] == "error" else "⚠️"
            report += f"- {severity_icon} **{finding['code']}**: {finding['message']}\n"
    
    report += "\n---\n*Generated by DevGodzilla QA*\n"
    
    return report

"""
DevGodzilla Library-First Gate

Gate that validates Article I: Library-First Development.
Detects patterns where existing libraries could be used instead of custom code.
"""

import re
from pathlib import Path
from typing import List, Set

from devgodzilla.qa.gates.interface import (
    Gate,
    GateContext,
    GateResult,
    GateVerdict,
    Finding,
)
from devgodzilla.logging import get_logger

logger = get_logger(__name__)


# Common patterns that indicate reinvention of well-known libraries
REINVENTION_PATTERNS = {
    # HTTP clients
    "python": [
        (r"class\s+\w*HTTP\w*Client", "requests", "Use 'requests' or 'httpx' library for HTTP clients"),
        (r"def\s+\w*request\w*\s*\(", "requests", "Consider using 'requests' or 'httpx' for HTTP requests"),
        (r"socket\.socket\(", "requests", "Use higher-level HTTP libraries like 'requests' or 'httpx'"),
        (r"urllib\.request", "requests", "Consider using 'requests' for simpler HTTP handling"),
        
        # JSON handling
        (r"def\s+parse_?json", "json", "Use built-in 'json' module for JSON parsing"),
        (r"def\s+to_?json", "json", "Use built-in 'json' module for JSON serialization"),
        
        # Date/time handling
        (r"def\s+\w*date\w*\s*\([^)]*\)\s*:", "datetime", "Use 'datetime' or 'dateutil' for date operations"),
        (r"class\s+\w*Date\w*Parser", "dateutil", "Use 'python-dateutil' for date parsing"),
        
        # Validation
        (r"class\s+\w*Validator", "pydantic", "Consider using 'pydantic' for data validation"),
        (r"def\s+validate_\w+\s*\(", "pydantic", "Consider using 'pydantic' models for validation"),
        
        # Logging
        (r"def\s+log_\w+\s*\(", "logging", "Use built-in 'logging' module for logging"),
        (r"class\s+\w*Logger\w*", "logging", "Use built-in 'logging' module for logging"),
        
        # Config handling
        (r"class\s+\w*Config\w*Parser", "pydantic", "Use 'pydantic-settings' for config management"),
        
        # CLI parsing
        (r"sys\.argv\[", "click", "Use 'click' or 'argparse' for CLI argument parsing"),
        (r"class\s+\w*Arg\w*Parser", "click", "Use 'click' or 'argparse' for CLI argument parsing"),
        
        # Testing utilities
        (r"def\s+assert_\w+\s*\(", "pytest", "Use pytest assertions and fixtures"),
        (r"class\s+\w*Mock\w*", "unittest.mock", "Use 'unittest.mock' or 'pytest-mock'"),
        
        # String manipulation
        (r"def\s+camel_to_snake", "inflection", "Use 'inflection' library for string transformations"),
        (r"def\s+snake_to_camel", "inflection", "Use 'inflection' library for string transformations"),
        (r"def\s+pluralize", "inflection", "Use 'inflection' library for pluralization"),
        
        # Encryption/hashing
        (r"def\s+\w*hash\w*\s*\(", "hashlib", "Use built-in 'hashlib' for hashing"),
        (r"def\s+\w*encrypt\w*\s*\(", "cryptography", "Use 'cryptography' library for encryption"),
        
        # URL handling
        (r"def\s+parse_url", "urllib.parse", "Use 'urllib.parse' for URL parsing"),
        (r"def\s+build_url", "urllib.parse", "Use 'urllib.parse' for URL building"),
    ],
    "javascript": [
        (r"function\s+\w*fetch\w*\s*\(", "axios", "Consider using 'axios' or native 'fetch'"),
        (r"class\s+\w*HTTP\w*Client", "axios", "Use 'axios' or 'node-fetch' for HTTP clients"),
        (r"function\s+formatDate", "date-fns", "Use 'date-fns' or 'luxon' for date formatting"),
        (r"function\s+deepClone", "lodash", "Use 'lodash.clonedeep' for deep cloning"),
        (r"function\s+isEqual", "lodash", "Use 'lodash.isequal' for deep equality"),
        (r"function\s+debounce", "lodash", "Use 'lodash.debounce' for debouncing"),
        (r"function\s+throttle", "lodash", "Use 'lodash.throttle' for throttling"),
    ],
    "typescript": [
        # Same as JavaScript, plus TypeScript-specific patterns
        (r"interface\s+\w*Validator", "zod", "Consider using 'zod' for runtime validation"),
        (r"type\s+Guard", "zod", "Use 'zod' for type guards and validation"),
    ],
}

# File extensions to language mapping
EXTENSION_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
}

# Directories to skip
SKIP_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "dist",
    "build",
    ".tox",
    "Origins",  # Vendored code
}


class LibraryFirstGate(Gate):
    """
    Gate that validates Article I: Library-First Development.
    
    Detects patterns where developers might be reinventing functionality
    that exists in well-tested, widely-used libraries.
    
    Example:
        gate = LibraryFirstGate()
        result = gate.run(context)
        if not result.passed:
            print("Consider using existing libraries instead of custom implementations")
    """

    def __init__(
        self,
        *,
        blocking: bool = False,
        max_findings_per_file: int = 5,
    ) -> None:
        self._blocking = blocking
        self.max_findings_per_file = max_findings_per_file

    @property
    def gate_id(self) -> str:
        return "library-first"

    @property
    def gate_name(self) -> str:
        return "Library-First Gate (Article I)"

    @property
    def blocking(self) -> bool:
        return self._blocking

    def run(self, context: GateContext) -> GateResult:
        """Check for library reinvention patterns."""
        findings = []
        workspace = Path(context.workspace_root)
        
        files_checked = 0
        patterns_found = 0
        
        for file_path in self._iter_source_files(workspace):
            language = EXTENSION_MAP.get(file_path.suffix)
            if not language:
                continue
            
            file_findings = self._check_file(file_path, language, workspace)
            findings.extend(file_findings)
            files_checked += 1
            patterns_found += len(file_findings)
        
        # Determine verdict
        if findings:
            # This is advisory by default (warning level)
            severity = "error" if self._blocking else "warning"
            for f in findings:
                f.severity = severity
            verdict = GateVerdict.FAIL if self._blocking else GateVerdict.WARN
        else:
            verdict = GateVerdict.PASS
        
        return GateResult(
            gate_id=self.gate_id,
            gate_name=self.gate_name,
            verdict=verdict,
            findings=findings,
            metadata={
                "files_checked": files_checked,
                "patterns_found": patterns_found,
                "article": "I",
                "article_title": "Library-First Development",
            },
        )

    def _iter_source_files(self, workspace: Path):
        """Iterate over source files in the workspace."""
        for path in workspace.rglob("*"):
            # Skip directories
            if not path.is_file():
                continue
            
            # Skip certain directories
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue
            
            # Only check known source file types
            if path.suffix in EXTENSION_MAP:
                yield path

    def _check_file(
        self,
        file_path: Path,
        language: str,
        workspace: Path,
    ) -> List[Finding]:
        """Check a single file for reinvention patterns."""
        findings = []
        patterns = REINVENTION_PATTERNS.get(language, [])
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.debug("file_read_error", extra={"file_path": str(file_path), "error": str(e)})
            return findings
        
        lines = content.split("\n")
        rel_path = str(file_path.relative_to(workspace))
        
        for pattern, library, suggestion in patterns:
            if len(findings) >= self.max_findings_per_file:
                break
            
            for i, line in enumerate(lines, 1):
                if len(findings) >= self.max_findings_per_file:
                    break
                
                if re.search(pattern, line):
                    findings.append(Finding(
                        gate_id=self.gate_id,
                        severity="warning",  # Will be updated based on blocking setting
                        message=f"Potential library reinvention detected. Consider using '{library}'",
                        file_path=rel_path,
                        line_number=i,
                        rule_id="article-I-library-first",
                        suggestion=suggestion,
                        metadata={
                            "pattern_matched": pattern,
                            "recommended_library": library,
                            "article": "I",
                        },
                    ))
        
        return findings


class LibraryFirstSummaryGate(Gate):
    """
    Summary gate for Article I compliance.
    
    Provides a quick check without detailed findings.
    """

    @property
    def gate_id(self) -> str:
        return "library-first-summary"

    @property
    def gate_name(self) -> str:
        return "Library-First Summary Gate"

    @property
    def blocking(self) -> bool:
        return False

    def run(self, context: GateContext) -> GateResult:
        """Quick check for library-first compliance."""
        # Run the full gate but just summarize
        full_gate = LibraryFirstGate()
        result = full_gate.run(context)
        
        return GateResult(
            gate_id=self.gate_id,
            gate_name=self.gate_name,
            verdict=result.verdict,
            metadata={
                "files_checked": result.metadata.get("files_checked", 0),
                "patterns_found": result.metadata.get("patterns_found", 0),
                "article": "I",
            },
        )

"""
DevGodzilla Simplicity Gate

Gate that validates Article VII: Simplicity.
Detects complexity issues like high cyclomatic complexity, deep nesting,
and overly long functions.
"""

import re
from pathlib import Path
from typing import List, Tuple

from devgodzilla.qa.gates.interface import (
    Gate,
    GateContext,
    GateResult,
    GateVerdict,
    Finding,
)
from devgodzilla.logging import get_logger

logger = get_logger(__name__)


# Default thresholds
DEFAULT_MAX_CYCLOMATIC_COMPLEXITY = 10
DEFAULT_MAX_FUNCTION_LENGTH = 50
DEFAULT_MAX_NESTING_DEPTH = 4
DEFAULT_MAX_FILE_LENGTH = 500
DEFAULT_MAX_PARAMETERS = 5

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

# File extensions to check
CHECKED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}


class ComplexityAnalyzer:
    """Analyzes code complexity metrics."""
    
    # Python keywords that increase cyclomatic complexity
    PYTHON_BRANCH_KEYWORDS = {
        "if", "elif", "for", "while", "and", "or",
        "except", "with", "assert", "match", "case",
    }
    
    # JavaScript/TypeScript branch keywords
    JS_BRANCH_KEYWORDS = {
        "if", "else", "for", "while", "switch", "case",
        "catch", "&&", "||", "?", "?.",
    }
    
    @classmethod
    def count_cyclomatic_complexity(cls, content: str, language: str) -> int:
        """
        Estimate cyclomatic complexity of a code block.
        
        This is a simplified heuristic that counts decision points.
        """
        complexity = 1  # Base complexity
        
        if language == "python":
            # Count branch keywords
            tokens = re.findall(r'\b(\w+)\b', content)
            complexity += sum(1 for t in tokens if t in cls.PYTHON_BRANCH_KEYWORDS)
            
            # Count boolean operators
            complexity += len(re.findall(r'\band\b|\bor\b', content))
            
            # Count comprehensions
            complexity += len(re.findall(r'\[.*for.*in.*\]', content))
            complexity += len(re.findall(r'\{.*for.*in.*\}', content))
            
        elif language in ("javascript", "typescript"):
            # Count branch keywords
            tokens = re.findall(r'\b(\w+)\b', content)
            complexity += sum(1 for t in tokens if t in cls.JS_BRANCH_KEYWORDS)
            
            # Count ternary operators
            complexity += len(re.findall(r'\?', content))
            
            # Count logical operators
            complexity += len(re.findall(r'&&|\|\|', content))
        
        return complexity
    
    @classmethod
    def calculate_nesting_depth(cls, line: str, language: str) -> int:
        """Calculate the nesting depth of a line based on indentation."""
        if language == "python":
            # Python uses indentation
            return len(line) - len(line.lstrip())
        else:
            # For JS/TS, count braces (rough estimate)
            return line.count("{") - line.count("}")
        
    @classmethod
    def count_parameters(cls, line: str, language: str) -> int:
        """Count parameters in a function definition."""
        if language == "python":
            match = re.search(r'def\s+\w+\s*\(([^)]*)\)', line)
            if match:
                params = match.group(1).split(",")
                # Filter out empty strings and self/cls
                params = [p.strip() for p in params if p.strip() and p.strip() not in ("self", "cls")]
                return len(params)
        elif language in ("javascript", "typescript"):
            match = re.search(r'function\s+\w+\s*\(([^)]*)\)', line)
            if not match:
                match = re.search(r'const\s+\w+\s*=\s*\(([^)]*)\)\s*=>', line)
            if match:
                params = match.group(1).split(",")
                params = [p.strip() for p in params if p.strip()]
                return len(params)
        return 0


class SimplicityGate(Gate):
    """
    Gate that validates Article VII: Simplicity.
    
    Detects code complexity issues including:
    - High cyclomatic complexity
    - Deeply nested code
    - Overly long functions
    - Too many parameters
    - Long files
    
    Example:
        gate = SimplicityGate(
            max_cyclomatic_complexity=10,
            max_function_length=50,
        )
        result = gate.run(context)
    """

    def __init__(
        self,
        *,
        blocking: bool = False,
        max_cyclomatic_complexity: int = DEFAULT_MAX_CYCLOMATIC_COMPLEXITY,
        max_function_length: int = DEFAULT_MAX_FUNCTION_LENGTH,
        max_nesting_depth: int = DEFAULT_MAX_NESTING_DEPTH,
        max_file_length: int = DEFAULT_MAX_FILE_LENGTH,
        max_parameters: int = DEFAULT_MAX_PARAMETERS,
    ) -> None:
        self._blocking = blocking
        self.max_cyclomatic_complexity = max_cyclomatic_complexity
        self.max_function_length = max_function_length
        self.max_nesting_depth = max_nesting_depth
        self.max_file_length = max_file_length
        self.max_parameters = max_parameters

    @property
    def gate_id(self) -> str:
        return "simplicity"

    @property
    def gate_name(self) -> str:
        return "Simplicity Gate (Article VII)"

    @property
    def blocking(self) -> bool:
        return self._blocking

    def run(self, context: GateContext) -> GateResult:
        """Check for complexity issues."""
        findings = []
        workspace = Path(context.workspace_root)
        
        files_checked = 0
        total_issues = 0
        
        for file_path in self._iter_source_files(workspace):
            language = self._get_language(file_path)
            if not language:
                continue
            
            file_findings = self._check_file(file_path, language, workspace)
            findings.extend(file_findings)
            files_checked += 1
            total_issues += len(file_findings)
        
        # Determine verdict
        if findings:
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
                "total_issues": total_issues,
                "thresholds": {
                    "max_cyclomatic_complexity": self.max_cyclomatic_complexity,
                    "max_function_length": self.max_function_length,
                    "max_nesting_depth": self.max_nesting_depth,
                    "max_file_length": self.max_file_length,
                    "max_parameters": self.max_parameters,
                },
                "article": "VII",
                "article_title": "Simplicity",
            },
        )

    def _iter_source_files(self, workspace: Path):
        """Iterate over source files in the workspace."""
        for path in workspace.rglob("*"):
            if not path.is_file():
                continue
            
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue
            
            if path.suffix in CHECKED_EXTENSIONS:
                yield path

    def _get_language(self, file_path: Path) -> str:
        """Determine language from file extension."""
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        return ext_to_lang.get(file_path.suffix, "")

    def _check_file(
        self,
        file_path: Path,
        language: str,
        workspace: Path,
    ) -> List[Finding]:
        """Check a single file for complexity issues."""
        findings = []
        rel_path = str(file_path.relative_to(workspace))
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            logger.debug("file_read_error", extra={"file_path": str(file_path), "error": str(e)})
            return findings
        
        lines = content.split("\n")
        
        # Check file length
        if len(lines) > self.max_file_length:
            findings.append(Finding(
                gate_id=self.gate_id,
                severity="warning",
                message=f"File is too long ({len(lines)} lines, max {self.max_file_length})",
                file_path=rel_path,
                rule_id="article-vii-file-length",
                suggestion="Consider splitting into multiple modules",
                metadata={
                    "actual_lines": len(lines),
                    "max_lines": self.max_file_length,
                    "article": "VII",
                },
            ))
        
        # Check functions
        functions = self._extract_functions(content, language)
        for func_name, start_line, func_content in functions:
            # Check function length
            func_lines = func_content.count("\n") + 1
            if func_lines > self.max_function_length:
                findings.append(Finding(
                    gate_id=self.gate_id,
                    severity="warning",
                    message=f"Function '{func_name}' is too long ({func_lines} lines, max {self.max_function_length})",
                    file_path=rel_path,
                    line_number=start_line,
                    rule_id="article-vii-function-length",
                    suggestion="Break down into smaller, focused functions",
                    metadata={
                        "function_name": func_name,
                        "actual_lines": func_lines,
                        "max_lines": self.max_function_length,
                        "article": "VII",
                    },
                ))
            
            # Check cyclomatic complexity
            complexity = ComplexityAnalyzer.count_cyclomatic_complexity(func_content, language)
            if complexity > self.max_cyclomatic_complexity:
                findings.append(Finding(
                    gate_id=self.gate_id,
                    severity="warning",
                    message=f"Function '{func_name}' has high complexity ({complexity}, max {self.max_cyclomatic_complexity})",
                    file_path=rel_path,
                    line_number=start_line,
                    rule_id="article-vii-cyclomatic-complexity",
                    suggestion="Reduce branching logic or extract helper functions",
                    metadata={
                        "function_name": func_name,
                        "actual_complexity": complexity,
                        "max_complexity": self.max_cyclomatic_complexity,
                        "article": "VII",
                    },
                ))
        
        # Check for deep nesting
        findings.extend(self._check_nesting(lines, language, rel_path))
        
        # Check function parameters
        findings.extend(self._check_parameters(content, language, rel_path))
        
        return findings

    def _extract_functions(
        self,
        content: str,
        language: str,
    ) -> List[Tuple[str, int, str]]:
        """Extract function definitions with their content."""
        functions = []
        lines = content.split("\n")
        
        if language == "python":
            # Find function definitions
            for i, line in enumerate(lines):
                match = re.match(r'^\s*def\s+(\w+)\s*\(', line)
                if match:
                    func_name = match.group(1)
                    start_indent = len(line) - len(line.lstrip())
                    func_lines = [line]
                    
                    # Collect function body
                    for j in range(i + 1, len(lines)):
                        next_line = lines[j]
                        if next_line.strip() == "":
                            func_lines.append(next_line)
                            continue
                        
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent <= start_indent and next_line.strip():
                            break
                        func_lines.append(next_line)
                    
                    functions.append((func_name, i + 1, "\n".join(func_lines)))
        
        elif language in ("javascript", "typescript"):
            # Find function definitions
            for i, line in enumerate(lines):
                match = re.match(r'.*function\s+(\w+)\s*\(', line)
                if not match:
                    match = re.match(r'.*const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>', line)
                if match:
                    func_name = match.group(1)
                    # Simplified: just get a chunk of lines
                    end_line = min(i + 50, len(lines))
                    func_content = "\n".join(lines[i:end_line])
                    functions.append((func_name, i + 1, func_content))
        
        return functions

    def _check_nesting(
        self,
        lines: List[str],
        language: str,
        rel_path: str,
    ) -> List[Finding]:
        """Check for deeply nested code."""
        findings = []
        
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            
            if language == "python":
                indent = (len(line) - len(line.lstrip())) // 4
                if indent > self.max_nesting_depth:
                    findings.append(Finding(
                        gate_id=self.gate_id,
                        severity="warning",
                        message=f"Deep nesting detected (level {indent}, max {self.max_nesting_depth})",
                        file_path=rel_path,
                        line_number=i,
                        rule_id="article-vii-nesting-depth",
                        suggestion="Extract nested logic into separate functions",
                        metadata={
                            "actual_depth": indent,
                            "max_depth": self.max_nesting_depth,
                            "article": "VII",
                        },
                    ))
                    break  # One finding per file is enough
        
        return findings

    def _check_parameters(
        self,
        content: str,
        language: str,
        rel_path: str,
    ) -> List[Finding]:
        """Check for functions with too many parameters."""
        findings = []
        lines = content.split("\n")
        
        for i, line in enumerate(lines, 1):
            param_count = ComplexityAnalyzer.count_parameters(line, language)
            if param_count > self.max_parameters:
                # Extract function name
                if language == "python":
                    match = re.search(r'def\s+(\w+)', line)
                else:
                    match = re.search(r'function\s+(\w+)', line)
                    if not match:
                        match = re.search(r'const\s+(\w+)\s*=', line)
                
                func_name = match.group(1) if match else "unknown"
                
                findings.append(Finding(
                    gate_id=self.gate_id,
                    severity="warning",
                    message=f"Function '{func_name}' has too many parameters ({param_count}, max {self.max_parameters})",
                    file_path=rel_path,
                    line_number=i,
                    rule_id="article-vii-parameter-count",
                    suggestion="Consider using a config object or builder pattern",
                    metadata={
                        "function_name": func_name,
                        "actual_params": param_count,
                        "max_params": self.max_parameters,
                        "article": "VII",
                    },
                ))
        
        return findings


class SimplicitySummaryGate(Gate):
    """
    Summary gate for Article VII compliance.
    
    Provides a quick complexity overview.
    """

    @property
    def gate_id(self) -> str:
        return "simplicity-summary"

    @property
    def gate_name(self) -> str:
        return "Simplicity Summary Gate"

    @property
    def blocking(self) -> bool:
        return False

    def run(self, context: GateContext) -> GateResult:
        """Quick check for simplicity compliance."""
        full_gate = SimplicityGate()
        result = full_gate.run(context)
        
        # Summarize findings by type
        issues_by_type = {}
        for finding in result.findings:
            rule_id = finding.rule_id or "unknown"
            issues_by_type[rule_id] = issues_by_type.get(rule_id, 0) + 1
        
        return GateResult(
            gate_id=self.gate_id,
            gate_name=self.gate_name,
            verdict=result.verdict,
            metadata={
                "files_checked": result.metadata.get("files_checked", 0),
                "total_issues": result.metadata.get("total_issues", 0),
                "issues_by_type": issues_by_type,
                "article": "VII",
            },
        )

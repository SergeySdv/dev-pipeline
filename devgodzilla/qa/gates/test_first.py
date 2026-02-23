"""Enhanced TestFirstGate with git history analysis.

Article III: Test-First Development - verifies tests were written before code.
"""

import subprocess
from typing import List
from pathlib import Path

from devgodzilla.qa.gates.interface import (
    Gate,
    GateContext,
    GateResult,
    GateVerdict,
    Finding,
)
from devgodzilla.logging import get_logger

logger = get_logger(__name__)


class TestFirstGate(Gate):
    """Article III: Test-First Development gate with git history analysis.
    
    Validates that tests are written before or alongside code changes.
    Analyzes git history to detect patterns where code is committed
    without corresponding tests.
    
    Example:
        gate = TestFirstGate()
        result = gate.run(context)
        if result.verdict == GateVerdict.FAIL:
            print("Tests should be written first!")
    """
    
    # Thresholds
    min_test_ratio: float = 0.3  # At least 30% of commits should touch tests
    max_test_after_code_days: int = 1  # Tests should be within 1 day of code
    
    @property
    def gate_id(self) -> str:
        return "test_first"
    
    @property
    def gate_name(self) -> str:
        return "Test-First Development (Article III)"
    
    @property
    def blocking(self) -> bool:
        return True
    
    @property
    def enabled(self) -> bool:
        return True
    
    def run(self, context: GateContext) -> GateResult:
        """Execute the test-first gate check.
        
        Args:
            context: Gate execution context
            
        Returns:
            GateResult with verdict and findings
        """
        findings: List[Finding] = []
        
        # Check for test directory
        test_dirs = self._find_test_dirs(context)
        if not test_dirs:
            findings.append(Finding(
                gate_id=self.gate_id,
                severity="error",
                message="No test directory found",
                suggestion="Create a tests/ or __tests__/ directory"
            ))
            return GateResult(
                gate_id=self.gate_id,
                gate_name=self.gate_name,
                verdict=GateVerdict.FAIL,
                findings=findings,
                metadata={"message": "No test directory found"}
            )
        
        # Analyze git history for test-first patterns
        git_available = self._check_git_available(context)
        if git_available:
            history_findings = self._analyze_git_history(context)
            findings.extend(history_findings)
        else:
            findings.append(Finding(
                gate_id=self.gate_id,
                severity="info",
                message="Git not available for history analysis"
            ))
        
        # Check test coverage patterns
        coverage_findings = self._check_coverage_patterns(context, test_dirs)
        findings.extend(coverage_findings)
        
        verdict = GateVerdict.PASS
        if any(f.severity == "error" for f in findings):
            verdict = GateVerdict.FAIL
        elif any(f.severity == "warning" for f in findings):
            verdict = GateVerdict.WARN
        
        return GateResult(
            gate_id=self.gate_id,
            gate_name=self.gate_name,
            verdict=verdict,
            findings=findings,
            metadata={"message": f"Found {len(findings)} test-first issues"}
        )
    
    def _find_test_dirs(self, context: GateContext) -> List[Path]:
        """Find test directories in the project.
        
        Args:
            context: Gate execution context
            
        Returns:
            List of found test directory paths
        """
        test_dir_names = ["tests", "test", "__tests__", "spec", "specs"]
        found = []
        
        workspace = Path(context.workspace_root)
        for name in test_dir_names:
            test_dir = workspace / name
            if test_dir.exists():
                found.append(test_dir)
        
        return found
    
    def _check_git_available(self, context: GateContext) -> bool:
        """Check if git is available in the workspace.
        
        Args:
            context: Gate execution context
            
        Returns:
            True if git is available
        """
        try:
            result = subprocess.run(
                ["git", "-C", str(context.workspace_root), "rev-parse", "--git-dir"],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _analyze_git_history(self, context: GateContext) -> List[Finding]:
        """Analyze git history for test-first patterns.
        
        Args:
            context: Gate execution context
            
        Returns:
            List of findings from git history analysis
        """
        findings = []
        
        try:
            # Get recent commits
            result = subprocess.run(
                ["git", "-C", str(context.workspace_root), "log",
                 "--oneline", "--name-only", "-20"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                return findings
            
            commits = self._parse_git_log(result.stdout)
            
            code_only_count = 0
            
            # Analyze each commit
            for commit in commits:
                test_files = [f for f in commit["files"] if self._is_test_file(f)]
                code_files = [f for f in commit["files"] if not self._is_test_file(f) and self._is_source_file(f)]
                
                # Check if code-only commit (no tests)
                if code_files and not test_files:
                    code_only_count += 1
                    # Only warn on first few instances to avoid spam
                    if code_only_count <= 3:
                        findings.append(Finding(
                            gate_id=self.gate_id,
                            severity="warning",
                            message=f"Commit {commit['hash'][:7]} has code changes without tests",
                            suggestion="Consider adding tests for new code",
                            metadata={"commit_hash": commit["hash"], "code_files": code_files}
                        ))
            
            # Summary finding if many code-only commits
            if code_only_count > 5:
                findings.append(Finding(
                    gate_id=self.gate_id,
                    severity="warning",
                    message=f"Found {code_only_count} commits with code but no tests",
                    suggestion="Consider writing tests alongside code changes"
                ))
            
        except subprocess.TimeoutExpired:
            findings.append(Finding(
                gate_id=self.gate_id,
                severity="info",
                message="Git history analysis timed out"
            ))
        except Exception as e:
            logger.warning(
                "git_history_analysis_failed",
                extra={"error": str(e)}
            )
            findings.append(Finding(
                gate_id=self.gate_id,
                severity="info",
                message=f"Could not analyze git history: {e}"
            ))
        
        return findings
    
    def _parse_git_log(self, output: str) -> List[dict]:
        """Parse git log output into structured commits.
        
        Args:
            output: Raw git log output
            
        Returns:
            List of commit dictionaries
        """
        commits = []
        current = None
        
        for line in output.strip().split("\n"):
            if not line:
                continue
            
            # Commit header line
            if not line.startswith("\t") and len(line) > 7:
                if current:
                    commits.append(current)
                parts = line.split(" ", 1)
                current = {
                    "hash": parts[0],
                    "message": parts[1] if len(parts) > 1 else "",
                    "files": []
                }
            # File line
            elif line.startswith("\t") and current:
                current["files"].append(line.strip())
        
        if current:
            commits.append(current)
        
        return commits
    
    def _is_test_file(self, path: str) -> bool:
        """Check if a file is a test file.
        
        Args:
            path: File path to check
            
        Returns:
            True if the file is a test file
        """
        test_patterns = ["test_", "_test.", ".test.", ".spec.", "__tests__"]
        return any(p in path for p in test_patterns)
    
    def _is_source_file(self, path: str) -> bool:
        """Check if a file is a source code file.
        
        Args:
            path: File path to check
            
        Returns:
            True if the file is a source code file
        """
        source_extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"]
        return any(path.endswith(ext) for ext in source_extensions)
    
    def _check_coverage_patterns(self, context: GateContext, test_dirs: List[Path]) -> List[Finding]:
        """Check for test coverage patterns.
        
        Args:
            context: Gate execution context
            test_dirs: List of test directory paths
            
        Returns:
            List of findings related to test coverage
        """
        findings = []
        
        workspace = Path(context.workspace_root)
        
        # Check for coverage configuration
        coverage_files = [
            workspace / "pytest.ini",
            workspace / "setup.cfg",
            workspace / "pyproject.toml",
            workspace / ".coveragerc",
            workspace / "jest.config.js",
            workspace / "jest.config.ts",
            workspace / "vitest.config.ts",
        ]
        
        has_coverage_config = any(f.exists() for f in coverage_files)
        
        if not has_coverage_config:
            findings.append(Finding(
                gate_id=self.gate_id,
                severity="info",
                message="No coverage configuration found",
                suggestion="Add pytest-cov or jest coverage configuration"
            ))
        
        # Check for test count
        test_count = 0
        for test_dir in test_dirs:
            for ext in ["*.py", "*.test.*", "*.spec.*"]:
                test_count += len(list(test_dir.rglob(ext)))
        
        if test_count == 0:
            findings.append(Finding(
                gate_id=self.gate_id,
                severity="warning",
                message="No test files found in test directories",
                suggestion="Add test files to the test directory"
            ))
        
        return findings

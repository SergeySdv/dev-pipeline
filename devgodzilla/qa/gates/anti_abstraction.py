"""
DevGodzilla Anti-Abstraction Gate

Gate that validates Article VIII: Anti-Abstraction.
Detects premature abstraction, over-engineering, and unused abstractions.
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

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
DEFAULT_MIN_DUPLICATIONS = 3  # Before abstracting (rule of three)
DEFAULT_MAX_ABSTRACTION_DEPTH = 3  # Max inheritance/abstraction levels
DEFAULT_MAX_INTERFACES_RATIO = 0.3  # Max ratio of abstract to concrete

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
    "tests",  # Test doubles are expected
    "__tests__",
}

# File extensions to check
CHECKED_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}


class AbstractionDetector:
    """Detects abstraction patterns in code."""
    
    # Python patterns indicating abstractions
    PYTHON_ABSTRACT_PATTERNS = [
        (r'^\s*class\s+\w+\s*\([^)]*\):\s*$', "class"),
        (r'^\s*from\s+abc\s+import', "abc_import"),
        (r'^\s*@abstractmethod', "abstract_method"),
        (r'^\s*class\s+\w+\s*\(\s*ABC\s*\)', "abstract_class"),
        (r'^\s*class\s+\w+\s*\([^)]*Protocol[^)]*\)', "protocol"),
        (r'^\s*class\s+\w+\s*\([^)]*Interface[^)]*\)', "interface"),
        (r'^\s*def\s+__init__\s*\(', "constructor"),
    ]
    
    # JavaScript/TypeScript patterns
    JS_ABSTRACT_PATTERNS = [
        (r'^\s*abstract\s+class\s+\w+', "abstract_class"),
        (r'^\s*interface\s+\w+', "interface"),
        (r'^\s*type\s+\w+\s*=', "type_alias"),
        (r'^\s*class\s+\w+\s+extends\s+', "inheritance"),
        (r'^\s*class\s+\w+\s+implements\s+', "implements"),
    ]
    
    @classmethod
    def find_abstractions(cls, content: str, language: str) -> List[Tuple[str, int, str]]:
        """Find abstraction declarations in code."""
        abstractions = []
        patterns = cls.PYTHON_ABSTRACT_PATTERNS if language == "python" else cls.JS_ABSTRACT_PATTERNS
        
        for i, line in enumerate(content.split("\n"), 1):
            for pattern, abstract_type in patterns:
                if re.search(pattern, line):
                    abstractions.append((abstract_type, i, line.strip()))
                    break
        
        return abstractions
    
    @classmethod
    def find_class_hierarchy(cls, content: str, language: str) -> Dict[str, List[str]]:
        """Find class inheritance relationships."""
        hierarchy = {}
        
        if language == "python":
            # Find class definitions with bases
            pattern = r'^\s*class\s+(\w+)\s*\(([^)]+)\)'
            for match in re.finditer(pattern, content, re.MULTILINE):
                class_name = match.group(1)
                bases = [b.strip() for b in match.group(2).split(",")]
                hierarchy[class_name] = bases
        
        elif language in ("javascript", "typescript"):
            # Find extends
            pattern = r'class\s+(\w+)\s+extends\s+(\w+)'
            for match in re.finditer(pattern, content):
                class_name = match.group(1)
                base_class = match.group(2)
                hierarchy[class_name] = [base_class]
        
        return hierarchy
    
    @classmethod
    def count_usages(cls, symbol: str, content: str, file_path: Path) -> int:
        """Count how many times a symbol is used (excluding its definition)."""
        # Simple heuristic: count occurrences minus definition
        count = len(re.findall(rf'\b{re.escape(symbol)}\b', content))
        
        # Subtract 1 for the definition itself (rough estimate)
        if count > 0:
            count -= 1
        
        return max(0, count)


class AntiAbstractionGate(Gate):
    """
    Gate that validates Article VIII: Anti-Abstraction.
    
    Detects:
    - Premature abstractions (unused base classes, interfaces)
    - Deep inheritance hierarchies
    - Abstract classes with only one implementation
    - Over-engineered patterns
    
    The "rule of three" principle: don't abstract until you have
    three duplications of the same pattern.
    
    Example:
        gate = AntiAbstractionGate()
        result = gate.run(context)
    """

    def __init__(
        self,
        *,
        blocking: bool = False,
        min_duplications: int = DEFAULT_MIN_DUPLICATIONS,
        max_abstraction_depth: int = DEFAULT_MAX_ABSTRACTION_DEPTH,
        max_interfaces_ratio: float = DEFAULT_MAX_INTERFACES_RATIO,
    ) -> None:
        self._blocking = blocking
        self.min_duplications = min_duplications
        self.max_abstraction_depth = max_abstraction_depth
        self.max_interfaces_ratio = max_interfaces_ratio

    @property
    def gate_id(self) -> str:
        return "anti-abstraction"

    @property
    def gate_name(self) -> str:
        return "Anti-Abstraction Gate (Article VIII)"

    @property
    def blocking(self) -> bool:
        return self._blocking

    def run(self, context: GateContext) -> GateResult:
        """Check for premature abstraction issues."""
        findings = []
        workspace = Path(context.workspace_root)
        
        files_checked = 0
        total_issues = 0
        
        # Collect all abstractions across the codebase
        all_abstractions: Dict[str, List[Tuple[Path, int, str]]] = {}
        all_classes: Dict[str, Tuple[Path, int]] = {}
        inheritance_trees: Dict[str, List[str]] = {}
        
        # First pass: collect all abstractions
        for file_path in self._iter_source_files(workspace):
            language = self._get_language(file_path)
            if not language:
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                logger.debug("file_read_error", extra={"file_path": str(file_path), "error": str(e)})
                continue
            
            files_checked += 1
            
            # Find abstractions
            abstractions = AbstractionDetector.find_abstractions(content, language)
            for abstract_type, line_num, line_text in abstractions:
                if abstract_type not in all_abstractions:
                    all_abstractions[abstract_type] = []
                all_abstractions[abstract_type].append((file_path, line_num, line_text))
            
            # Find class definitions
            if language == "python":
                for match in re.finditer(r'^\s*class\s+(\w+)', content, re.MULTILINE):
                    class_name = match.group(1)
                    all_classes[class_name] = (file_path, match.start() + 1)
            
            # Find inheritance
            hierarchy = AbstractionDetector.find_class_hierarchy(content, language)
            for child, parents in hierarchy.items():
                for parent in parents:
                    if parent not in ("object", "ABC", "Protocol"):
                        if parent not in inheritance_trees:
                            inheritance_trees[parent] = []
                        inheritance_trees[parent].append(child)
        
        # Second pass: analyze for issues
        findings.extend(self._check_single_implementations(
            inheritance_trees, all_classes, workspace
        ))
        findings.extend(self._check_deep_inheritance(
            inheritance_trees, all_classes, workspace
        ))
        findings.extend(self._check_unused_abstractions(
            all_abstractions, all_classes, workspace
        ))
        findings.extend(self._check_over_abstracted_files(
            workspace
        ))
        
        total_issues = len(findings)
        
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
                "abstractions_found": sum(len(v) for v in all_abstractions.values()),
                "classes_found": len(all_classes),
                "article": "VIII",
                "article_title": "Anti-Abstraction",
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

    def _check_single_implementations(
        self,
        inheritance_trees: Dict[str, List[str]],
        all_classes: Dict[str, Tuple[Path, int]],
        workspace: Path,
    ) -> List[Finding]:
        """Check for base classes with only one implementation."""
        findings = []
        
        for base_class, children in inheritance_trees.items():
            if len(children) == 1:
                if base_class in all_classes:
                    file_path, line_num = all_classes[base_class]
                    rel_path = str(file_path.relative_to(workspace))
                    
                    findings.append(Finding(
                        gate_id=self.gate_id,
                        severity="warning",
                        message=f"Base class '{base_class}' has only one implementation '{children[0]}'. Consider inlining.",
                        file_path=rel_path,
                        line_number=line_num,
                        rule_id="article-viii-single-implementation",
                        suggestion="Consider removing the abstraction until more implementations are needed (rule of three)",
                        metadata={
                            "base_class": base_class,
                            "only_child": children[0],
                            "article": "VIII",
                        },
                    ))
        
        return findings

    def _check_deep_inheritance(
        self,
        inheritance_trees: Dict[str, List[str]],
        all_classes: Dict[str, Tuple[Path, int]],
        workspace: Path,
    ) -> List[Finding]:
        """Check for deep inheritance hierarchies."""
        findings = []
        
        def get_depth(class_name: str, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()
            if class_name in visited:
                return 0
            visited.add(class_name)
            
            children = inheritance_trees.get(class_name, [])
            if not children:
                return 1
            return 1 + max(get_depth(child, visited) for child in children)
        
        # Find root classes (classes that are not children of any other class)
        all_children = set()
        for children in inheritance_trees.values():
            all_children.update(children)
        
        root_classes = set(inheritance_trees.keys()) - all_children
        
        for root in root_classes:
            depth = get_depth(root)
            if depth > self.max_abstraction_depth:
                if root in all_classes:
                    file_path, line_num = all_classes[root]
                    rel_path = str(file_path.relative_to(workspace))
                    
                    findings.append(Finding(
                        gate_id=self.gate_id,
                        severity="warning",
                        message=f"Deep inheritance hierarchy starting at '{root}' (depth {depth}, max {self.max_abstraction_depth})",
                        file_path=rel_path,
                        line_number=line_num,
                        rule_id="article-viii-deep-inheritance",
                        suggestion="Consider composition over inheritance",
                        metadata={
                            "root_class": root,
                            "depth": depth,
                            "max_depth": self.max_abstraction_depth,
                            "article": "VIII",
                        },
                    ))
        
        return findings

    def _check_unused_abstractions(
        self,
        all_abstractions: Dict[str, List[Tuple[Path, int, str]]],
        all_classes: Dict[str, Tuple[Path, int]],
        workspace: Path,
    ) -> List[Finding]:
        """Check for potentially unused abstractions."""
        findings = []
        
        # Check for abstract classes that might not be used
        abstract_classes = all_abstractions.get("abstract_class", [])
        abstract_classes.extend(all_abstractions.get("protocol", []))
        abstract_classes.extend(all_abstractions.get("interface", []))
        
        # Look for classes ending in "Base", "Abstract", "Interface"
        for class_name, (file_path, line_num) in all_classes.items():
            if any(suffix in class_name for suffix in ["Base", "Abstract", "Interface", "Mixin"]):
                # Check if this class is used elsewhere
                rel_path = str(file_path.relative_to(workspace))
                
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                
                # Count references (very simple heuristic)
                # In a real implementation, would use AST or proper symbol resolution
                pattern = rf'\b{re.escape(class_name)}\b'
                references = len(re.findall(pattern, content))
                
                # Check if it's in inheritance trees
                in_hierarchy = class_name in {
                    p for parents in [all_classes.keys()] for p in parents
                }
                
                if references <= 2 and not in_hierarchy:
                    findings.append(Finding(
                        gate_id=self.gate_id,
                        severity="info",  # Low severity, just advisory
                        message=f"Potentially unused abstraction: '{class_name}'",
                        file_path=rel_path,
                        line_number=line_num,
                        rule_id="article-viii-unused-abstraction",
                        suggestion="Verify this abstraction is actually needed, or remove it",
                        metadata={
                            "class_name": class_name,
                            "references": references,
                            "article": "VIII",
                        },
                    ))
        
        return findings

    def _check_over_abstracted_files(self, workspace: Path) -> List[Finding]:
        """Check for files with too many abstractions."""
        findings = []
        
        for file_path in self._iter_source_files(workspace):
            language = self._get_language(file_path)
            if not language:
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            
            abstractions = AbstractionDetector.find_abstractions(content, language)
            
            # Count class/interface definitions
            class_count = sum(1 for a in abstractions if a[0] in ("class", "abstract_class", "interface"))
            
            if class_count > 5:  # Arbitrary threshold
                rel_path = str(file_path.relative_to(workspace))
                
                findings.append(Finding(
                    gate_id=self.gate_id,
                    severity="info",
                    message=f"File has many abstractions ({class_count} classes/interfaces)",
                    file_path=rel_path,
                    rule_id="article-viii-over-abstracted-file",
                    suggestion="Consider splitting into multiple files",
                    metadata={
                        "class_count": class_count,
                        "article": "VIII",
                    },
                ))
        
        return findings


class AntiAbstractionSummaryGate(Gate):
    """
    Summary gate for Article VIII compliance.
    
    Provides a quick abstraction overview.
    """

    @property
    def gate_id(self) -> str:
        return "anti-abstraction-summary"

    @property
    def gate_name(self) -> str:
        return "Anti-Abstraction Summary Gate"

    @property
    def blocking(self) -> bool:
        return False

    def run(self, context: GateContext) -> GateResult:
        """Quick check for abstraction compliance."""
        full_gate = AntiAbstractionGate()
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
                "article": "VIII",
            },
        )

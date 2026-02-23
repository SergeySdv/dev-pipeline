"""LLM-based checklist validation.

Validates checklist items against actual code artifacts using
semantic understanding rather than simple pattern matching.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path

from devgodzilla.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChecklistItem:
    """A single checklist item."""
    id: str
    description: str
    checked: bool = False
    required: bool = True
    category: str = "general"
    validation_hints: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of validating a checklist item."""
    item_id: str
    passed: bool
    confidence: float
    evidence: List[str]
    reasoning: str
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ChecklistValidator:
    """Validates checklist items against code artifacts using LLM.
    
    Provides both pattern-based and LLM-based validation strategies
    for verifying checklist items are satisfied by code artifacts.
    
    Example:
        validator = ChecklistValidator(llm_client=my_client)
        items = validator.parse_checklist(markdown_content)
        results = validator.validate_all(items, [Path("src/main.py")])
    """
    
    llm_client: Any = None  # Optional LLM client for semantic validation
    smart_context: Any = None  # SmartContextManager for large files
    use_llm: bool = True
    
    def parse_checklist(self, content: str) -> List[ChecklistItem]:
        """Parse checklist from markdown content.
        
        Args:
            content: Markdown content with checklist items
            
        Returns:
            List of ChecklistItem objects
        """
        items = []
        pattern = r"- \[([ x])\] (.+)"
        
        for i, match in enumerate(re.finditer(pattern, content)):
            checked = match.group(1).lower() == "x"
            description = match.group(2).strip()
            
            # Detect required/optional
            required = not description.startswith("[Optional]")
            if description.startswith("[Optional]"):
                description = description[10:].strip()
            
            items.append(ChecklistItem(
                id=f"item-{i+1}",
                description=description,
                checked=checked,
                required=required
            ))
        
        logger.debug(
            "checklist_parsed",
            extra={"item_count": len(items), "checked": sum(1 for i in items if i.checked)}
        )
        
        return items
    
    def validate_item(
        self,
        item: ChecklistItem,
        artifacts: List[Path],
        context: Optional[Dict] = None
    ) -> ValidationResult:
        """Validate a single checklist item against artifacts.
        
        Args:
            item: Checklist item to validate
            artifacts: List of artifact paths to check against
            context: Optional additional context
            
        Returns:
            ValidationResult with pass/fail status and evidence
        """
        
        # First, try pattern-based validation
        pattern_result = self._validate_with_patterns(item, artifacts)
        if pattern_result.confidence >= 0.8:
            return pattern_result
        
        # If LLM available and enabled, use semantic validation
        if self.use_llm and self.llm_client:
            return self._validate_with_llm(item, artifacts, context)
        
        # Fall back to pattern result
        return pattern_result
    
    def validate_all(
        self,
        items: List[ChecklistItem],
        artifacts: List[Path],
        context: Optional[Dict] = None
    ) -> List[ValidationResult]:
        """Validate all checklist items.
        
        Args:
            items: List of checklist items to validate
            artifacts: List of artifact paths to check against
            context: Optional additional context
            
        Returns:
            List of ValidationResult objects
        """
        results = [
            self.validate_item(item, artifacts, context)
            for item in items
        ]
        
        passed = sum(1 for r in results if r.passed)
        logger.info(
            "checklist_validation_complete",
            extra={
                "total_items": len(items),
                "passed": passed,
                "failed": len(items) - passed
            }
        )
        
        return results
    
    def _validate_with_patterns(
        self,
        item: ChecklistItem,
        artifacts: List[Path]
    ) -> ValidationResult:
        """Validate using pattern matching.
        
        Args:
            item: Checklist item to validate
            artifacts: List of artifact paths to check
            
        Returns:
            ValidationResult based on pattern matching
        """
        
        evidence = []
        confidence = 0.0
        passed = False
        
        # Extract keywords from item description
        keywords = self._extract_keywords(item.description)
        
        for artifact in artifacts:
            try:
                content = artifact.read_text()
                
                # Check for keyword presence
                keyword_matches = sum(
                    1 for kw in keywords
                    if kw.lower() in content.lower()
                )
                
                if keyword_matches >= len(keywords) * 0.5:
                    evidence.append(f"Found relevant keywords in {artifact.name}")
                    confidence = min(0.8, 0.4 + keyword_matches * 0.1)
                    passed = True
                
                # Check for specific patterns based on item type
                if "test" in item.description.lower():
                    if self._has_test_patterns(content):
                        evidence.append(f"Test patterns found in {artifact.name}")
                        confidence = max(confidence, 0.7)
                        passed = True
                
                if "error handling" in item.description.lower():
                    if self._has_error_handling_patterns(content):
                        evidence.append(f"Error handling patterns in {artifact.name}")
                        confidence = max(confidence, 0.6)
                
            except Exception:
                continue
        
        return ValidationResult(
            item_id=item.id,
            passed=passed,
            confidence=confidence,
            evidence=evidence,
            reasoning=f"Pattern-based validation: {len(evidence)} matches found"
        )
    
    def _validate_with_llm(
        self,
        item: ChecklistItem,
        artifacts: List[Path],
        context: Optional[Dict]
    ) -> ValidationResult:
        """Validate using LLM for semantic understanding.
        
        Args:
            item: Checklist item to validate
            artifacts: List of artifact paths to check
            context: Optional additional context
            
        Returns:
            ValidationResult from LLM analysis
        """
        
        # Build context from artifacts
        artifact_context = self._build_artifact_context(artifacts)
        
        # Construct prompt for LLM
        prompt = f"""Check if the following checklist item is satisfied by the code:

Checklist Item: {item.description}

Code Context:
{artifact_context}

Respond with:
1. PASSED or FAILED
2. Confidence (0.0-1.0)
3. Evidence from code
4. Reasoning
"""
        
        # Call LLM (implementation depends on client)
        try:
            response = self.llm_client.complete(prompt)
            return self._parse_llm_response(item.id, response)
        except Exception as e:
            logger.warning(
                "llm_validation_failed",
                extra={"item_id": item.id, "error": str(e)}
            )
            return ValidationResult(
                item_id=item.id,
                passed=False,
                confidence=0.0,
                evidence=[],
                reasoning=f"LLM validation failed: {e}"
            )
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text.
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            List of relevant keywords
        """
        # Remove common words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                      "have", "has", "had", "do", "does", "did", "will", "would", "could",
                      "should", "may", "might", "must", "shall", "can", "need", "to", "for",
                      "in", "on", "at", "by", "with", "from", "as", "into", "through"}
        
        words = re.findall(r'\b\w+\b', text.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]
    
    def _has_test_patterns(self, content: str) -> bool:
        """Check if content has test patterns.
        
        Args:
            content: Source code content
            
        Returns:
            True if test patterns are found
        """
        patterns = ["def test_", "it(", "describe(", "test(", "assert ", "expect("]
        return any(p in content for p in patterns)
    
    def _has_error_handling_patterns(self, content: str) -> bool:
        """Check if content has error handling patterns.
        
        Args:
            content: Source code content
            
        Returns:
            True if error handling patterns are found
        """
        patterns = ["try:", "except", "catch", "throw", "raise", ".error", "Error("]
        return any(p in content for p in patterns)
    
    def _build_artifact_context(self, artifacts: List[Path], max_tokens: int = 4000) -> str:
        """Build context string from artifacts.
        
        Args:
            artifacts: List of artifact paths
            max_tokens: Maximum tokens for context
            
        Returns:
            Context string built from artifacts
        """
        if self.smart_context:
            return self.smart_context.build_context(artifacts, "", max_tokens)
        
        # Simple concatenation fallback
        parts = []
        total = 0
        for artifact in artifacts:
            try:
                content = artifact.read_text()
                if total + len(content) > max_tokens * 4:
                    break
                parts.append(f"--- {artifact.name} ---\n{content}\n")
                total += len(content)
            except Exception:
                continue
        return "\n".join(parts)
    
    def _parse_llm_response(self, item_id: str, response: str) -> ValidationResult:
        """Parse LLM response into ValidationResult.
        
        Args:
            item_id: Checklist item ID
            response: Raw LLM response text
            
        Returns:
            Parsed ValidationResult
        """
        # Simple parsing - can be enhanced
        passed = "PASSED" in response.upper()
        
        # Extract confidence
        conf_match = re.search(r"confidence[:\s]+([0-9.]+)", response, re.IGNORECASE)
        confidence = float(conf_match.group(1)) if conf_match else 0.5
        
        return ValidationResult(
            item_id=item_id,
            passed=passed,
            confidence=confidence,
            evidence=[response[:500]],
            reasoning="LLM-based validation"
        )

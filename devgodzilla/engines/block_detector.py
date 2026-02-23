"""Block detection for agent execution feedback loops.

Detects when agent execution is blocked and needs human intervention.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

from devgodzilla.logging import get_logger

logger = get_logger(__name__)


class BlockReason(Enum):
    """Reason why agent execution is blocked."""
    CLARIFICATION_NEEDED = "clarification_needed"
    AMBIGUOUS_REQUIREMENT = "ambiguous_requirement"
    MISSING_INFORMATION = "missing_information"
    CONFLICTING_INSTRUCTIONS = "conflicting_instructions"
    IMPOSSIBLE_REQUEST = "impossible_request"
    PERMISSION_DENIED = "permission_denied"
    RESOURCE_NOT_FOUND = "resource_not_found"


@dataclass
class BlockInfo:
    """Information about a detected block."""
    reason: BlockReason
    message: str
    suggested_question: Optional[str] = None
    options: List[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class BlockDetector:
    """Detects when agent output indicates blocked execution.
    
    Analyzes agent output for patterns indicating the agent cannot
    proceed without additional input or intervention.
    
    Example:
        detector = BlockDetector()
        result = detector.detect(agent_output)
        
        if result:
            print(f"Blocked: {result.reason.value}")
            if result.suggested_question:
                print(f"Ask: {result.suggested_question}")
    """
    
    # Patterns that indicate blocking - ordered by specificity
    BLOCK_PATTERNS: List[tuple] = field(default_factory=lambda: [
        # High-specificity patterns first
        (r"cannot proceed without\s+(.+?)(?:\.|$)", BlockReason.MISSING_INFORMATION),
        (r"need[s]?\s+clarification\s+(?:on|about)?\s*(.+?)(?:\.|$)", BlockReason.CLARIFICATION_NEEDED),
        (r"ambiguous\s+(?:requirement|specification|request)\s*:?\s*(.+?)(?:\.|$)", BlockReason.AMBIGUOUS_REQUIREMENT),
        (r"missing\s+(?:required\s+)?information\s*:?\s*(.+?)(?:\.|$)", BlockReason.MISSING_INFORMATION),
        (r"conflicting\s+(?:requirements|instructions)\s*:?\s*(.+?)(?:\.|$)", BlockReason.CONFLICTING_INSTRUCTIONS),
        (r"impossible\s+to\s+(.+?)(?:\.|$)", BlockReason.IMPOSSIBLE_REQUEST),
        (r"permission\s+denied\s*:?\s*(.+?)(?:\.|$)", BlockReason.PERMISSION_DENIED),
        (r"(?:resource|file|directory)\s+(?:not\s+found|does\s+not\s+exist)\s*:?\s*(.+?)(?:\.|$)", BlockReason.RESOURCE_NOT_FOUND),
        
        # Question patterns indicating ambiguity
        (r"which\s+.*should\s+(?:I|we)\s+(?:choose|use|implement)\s*[:?]?\s*(.+?)(?:\.|$)", BlockReason.CLARIFICATION_NEEDED),
        (r"I'm\s+not\s+sure\s+(?:how|what|which)\s+(?:to\s+)?(.+?)(?:\.|$)", BlockReason.AMBIGUOUS_REQUIREMENT),
        (r"(?:could|would|should)\s+you\s+(?:please\s+)?clarify\s+(.+?)(?:\.|$)", BlockReason.CLARIFICATION_NEEDED),
        
        # General blocking patterns (lower specificity)
        (r"cannot\s+determine\s+(.+?)(?:\.|$)", BlockReason.AMBIGUOUS_REQUIREMENT),
        (r"unable\s+to\s+proceed\s*(?:without|due\s+to)?\s*(.+?)(?:\.|$)", BlockReason.MISSING_INFORMATION),
        (r"requires?\s+(?:additional|more)\s+(?:information|input|context)\s*:?\s*(.+?)(?:\.|$)", BlockReason.MISSING_INFORMATION),
    ])
    
    # Questions to ask for each block reason
    REASON_QUESTIONS: dict = field(default_factory=lambda: {
        BlockReason.CLARIFICATION_NEEDED: "Could you provide more details about what you'd like?",
        BlockReason.AMBIGUOUS_REQUIREMENT: "The requirements seem unclear. Could you clarify what you want?",
        BlockReason.MISSING_INFORMATION: "Additional information is needed to proceed. What can you provide?",
        BlockReason.CONFLICTING_INSTRUCTIONS: "There seem to be conflicting instructions. Which should take priority?",
        BlockReason.IMPOSSIBLE_REQUEST: "This request may not be achievable. Would you like to adjust the approach?",
        BlockReason.PERMISSION_DENIED: "Access was denied. Do you have the correct permissions or credentials?",
        BlockReason.RESOURCE_NOT_FOUND: "A required resource was not found. Is the path or reference correct?",
    })
    
    # Confidence thresholds
    HIGH_CONFIDENCE_PATTERNS: List[str] = field(default_factory=lambda: [
        r"cannot proceed without",
        r"permission denied",
        r"not found",
        r"impossible to",
    ])
    
    def detect(self, output: str) -> Optional[BlockInfo]:
        """Detect if output indicates blocked execution.
        
        Args:
            output: The agent output to analyze
            
        Returns:
            BlockInfo if a block is detected, None otherwise
        """
        if not output or not output.strip():
            return None
        
        output_lower = output.lower()
        
        # Check each pattern
        for pattern, reason in self.BLOCK_PATTERNS:
            match = re.search(pattern, output_lower, re.IGNORECASE | re.MULTILINE)
            if match:
                # Extract the matched portion as context
                matched_text = match.group(0)
                captured_group = match.group(1) if match.lastindex else None
                
                # Build message
                message = f"Agent execution blocked: {reason.value}"
                if captured_group:
                    message = f"{message} - {captured_group.strip()}"
                
                # Determine confidence
                confidence = self._calculate_confidence(matched_text, reason)
                
                # Extract context around the match
                context = self.extract_context(output, match)
                
                # Get suggested question
                suggested_question = self._get_suggested_question(reason, captured_group)
                
                return BlockInfo(
                    reason=reason,
                    message=message,
                    suggested_question=suggested_question,
                    context=context,
                    confidence=confidence,
                )
        
        return None
    
    def extract_context(self, output: str, match: re.Match) -> dict:
        """Extract relevant context around the block.
        
        Args:
            output: Full output text
            match: The regex match object
            
        Returns:
            Dictionary with context information
        """
        lines = output.split('\n')
        matched_line = None
        line_number = 0
        
        # Find the line containing the match
        for i, line in enumerate(lines):
            if match.group(0).lower() in line.lower():
                matched_line = line
                line_number = i
                break
        
        if matched_line is None:
            return {"match_text": match.group(0)}
        
        # Get surrounding context (2 lines before and after)
        start_idx = max(0, line_number - 2)
        end_idx = min(len(lines), line_number + 3)
        
        context_lines = lines[start_idx:end_idx]
        
        return {
            "match_text": match.group(0),
            "line_number": line_number,
            "context": "\n".join(context_lines),
            "surrounding_lines": {
                "before": lines[start_idx:line_number] if line_number > start_idx else [],
                "match": matched_line,
                "after": lines[line_number + 1:end_idx] if end_idx > line_number + 1 else [],
            },
        }
    
    def _calculate_confidence(self, matched_text: str, reason: BlockReason) -> float:
        """Calculate confidence score for the detection.
        
        Args:
            matched_text: The text that matched the pattern
            reason: The detected block reason
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Start with base confidence
        base_confidence = 0.7
        
        # Check if it matches a high-confidence pattern
        matched_lower = matched_text.lower()
        for high_conf_pattern in self.HIGH_CONFIDENCE_PATTERNS:
            if high_conf_pattern in matched_lower:
                return 0.95
        
        # Adjust based on reason
        reason_multipliers = {
            BlockReason.PERMISSION_DENIED: 0.95,
            BlockReason.RESOURCE_NOT_FOUND: 0.90,
            BlockReason.IMPOSSIBLE_REQUEST: 0.85,
            BlockReason.CONFLICTING_INSTRUCTIONS: 0.80,
            BlockReason.MISSING_INFORMATION: 0.75,
            BlockReason.CLARIFICATION_NEEDED: 0.70,
            BlockReason.AMBIGUOUS_REQUIREMENT: 0.65,
        }
        
        return reason_multipliers.get(reason, base_confidence)
    
    def _get_suggested_question(self, reason: BlockReason, captured_detail: Optional[str]) -> str:
        """Generate a suggested question for the user.
        
        Args:
            reason: The block reason
            captured_detail: Additional detail captured from the pattern
            
        Returns:
            A suggested question to ask the user
        """
        base_question = self.REASON_QUESTIONS.get(reason, "How would you like to proceed?")
        
        if captured_detail:
            # Customize the question with the captured detail
            detail = captured_detail.strip()
            if reason == BlockReason.MISSING_INFORMATION:
                return f"Could you provide the following information: {detail}?"
            elif reason == BlockReason.CLARIFICATION_NEEDED:
                return f"Could you clarify: {detail}?"
            elif reason == BlockReason.AMBIGUOUS_REQUIREMENT:
                return f"The requirement about '{detail}' seems ambiguous. Could you clarify?"
        
        return base_question
    
    def detect_all(self, output: str) -> List[BlockInfo]:
        """Detect all blocks in the output.
        
        Args:
            output: The agent output to analyze
            
        Returns:
            List of all detected BlockInfo objects
        """
        if not output or not output.strip():
            return []
        
        blocks = []
        output_lower = output.lower()
        
        for pattern, reason in self.BLOCK_PATTERNS:
            for match in re.finditer(pattern, output_lower, re.IGNORECASE | re.MULTILINE):
                captured_group = match.group(1) if match.lastindex else None
                
                message = f"Agent execution blocked: {reason.value}"
                if captured_group:
                    message = f"{message} - {captured_group.strip()}"
                
                confidence = self._calculate_confidence(match.group(0), reason)
                context = self.extract_context(output, match)
                suggested_question = self._get_suggested_question(reason, captured_group)
                
                blocks.append(BlockInfo(
                    reason=reason,
                    message=message,
                    suggested_question=suggested_question,
                    context=context,
                    confidence=confidence,
                ))
        
        # Remove duplicates based on overlapping matches
        return self._deduplicate_blocks(blocks)
    
    def _deduplicate_blocks(self, blocks: List[BlockInfo]) -> List[BlockInfo]:
        """Remove duplicate or overlapping blocks.
        
        Args:
            blocks: List of detected blocks
            
        Returns:
            Deduplicated list of blocks
        """
        if not blocks:
            return blocks
        
        # Sort by confidence (highest first)
        sorted_blocks = sorted(blocks, key=lambda b: b.confidence, reverse=True)
        
        # Keep track of seen match texts
        seen_matches = set()
        unique_blocks = []
        
        for block in sorted_blocks:
            match_text = block.context.get("match_text", "")
            # Normalize for comparison
            normalized = match_text.lower().strip()
            
            # Check if this is a duplicate or near-duplicate
            is_duplicate = False
            for seen in seen_matches:
                if normalized in seen or seen in normalized:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_matches.add(normalized)
                unique_blocks.append(block)
        
        return unique_blocks


# Convenience function
def detect_block(output: str) -> Optional[BlockInfo]:
    """Detect if output indicates blocked execution.
    
    Args:
        output: The agent output to analyze
        
    Returns:
        BlockInfo if a block is detected, None otherwise
    """
    detector = BlockDetector()
    return detector.detect(output)

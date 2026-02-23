"""Smart context handling for large code files using RAG.

When files are too large for the context window, chunk and retrieve
relevant sections based on the query. This enables QA gates to work
with large codebases without exceeding token limits.
"""

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from devgodzilla.logging import get_logger

logger = get_logger(__name__)


# Token estimation constants
CHARS_PER_TOKEN = 4  # Approximate chars per token for code


@dataclass
class TextChunk:
    """A chunk of text with metadata.
    
    Attributes:
        content: The actual text content
        start_line: Starting line number in the original file
        end_line: Ending line number in the original file
        token_count: Estimated number of tokens
        file_path: Path to the source file
        chunk_id: Unique identifier for this chunk
    """
    content: str
    start_line: int
    end_line: int
    token_count: int
    file_path: str
    chunk_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "token_count": self.token_count,
            "file_path": self.file_path,
            "chunk_id": self.chunk_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextChunk":
        """Create from dictionary representation."""
        return cls(
            content=data["content"],
            start_line=data["start_line"],
            end_line=data["end_line"],
            token_count=data["token_count"],
            file_path=data["file_path"],
            chunk_id=data["chunk_id"],
        )


@dataclass
class SmartContextManager:
    """Manages context for large files with chunking and retrieval.
    
    Provides intelligent chunking and retrieval strategies for handling
    large code files that exceed context window limits.
    
    Example:
        manager = SmartContextManager(max_chunk_tokens=500)
        chunks = manager.chunk_file(Path("large_file.py"))
        relevant = manager.retrieve_relevant_chunks(chunks, "error handling")
        context = manager.build_context([Path("file1.py")], "security check")
    """
    
    max_chunk_tokens: int = 500
    max_context_tokens: int = 8000
    overlap_tokens: int = 50
    
    def chunk_file(self, file_path: Path) -> List[TextChunk]:
        """Split a file into overlapping chunks.
        
        Args:
            file_path: Path to the file to chunk
            
        Returns:
            List of TextChunk objects
        """
        if not file_path.exists():
            logger.warning("file_not_found", extra={"path": str(file_path)})
            return []
        
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.error("file_read_error", extra={"path": str(file_path), "error": str(e)})
            return []
        
        return self.chunk_text(text, str(file_path))
    
    def chunk_text(self, text: str, file_path: str = "") -> List[TextChunk]:
        """Split text into overlapping chunks.
        
        Uses line-based chunking to preserve code structure.
        
        Args:
            text: Text content to chunk
            file_path: Optional file path for metadata
            
        Returns:
            List of TextChunk objects
        """
        if not text.strip():
            return []
        
        lines = text.splitlines()
        if not lines:
            return []
        
        chunks: List[TextChunk] = []
        current_chunk_lines: List[str] = []
        current_start = 0
        current_tokens = 0
        line_idx = 0
        
        overlap_lines = self._estimate_overlap_lines()
        
        while line_idx < len(lines):
            line = lines[line_idx]
            line_tokens = self.count_tokens(line)
            
            if current_tokens + line_tokens > self.max_chunk_tokens and current_chunk_lines:
                # Save current chunk
                chunk_content = "\n".join(current_chunk_lines)
                chunk_id = self._generate_chunk_id(file_path, current_start, line_idx)
                
                chunks.append(TextChunk(
                    content=chunk_content,
                    start_line=current_start + 1,  # 1-indexed
                    end_line=line_idx,
                    token_count=current_tokens,
                    file_path=file_path,
                    chunk_id=chunk_id,
                ))
                
                # Start new chunk with overlap
                overlap_start = max(0, len(current_chunk_lines) - overlap_lines)
                current_chunk_lines = current_chunk_lines[overlap_start:]
                current_tokens = sum(self.count_tokens(l) for l in current_chunk_lines)
                current_start = line_idx - len(current_chunk_lines)
            
            current_chunk_lines.append(line)
            current_tokens += line_tokens
            line_idx += 1
        
        # Don't forget the last chunk
        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines)
            chunk_id = self._generate_chunk_id(file_path, current_start, len(lines))
            
            chunks.append(TextChunk(
                content=chunk_content,
                start_line=current_start + 1,  # 1-indexed
                end_line=len(lines),
                token_count=current_tokens,
                file_path=file_path,
                chunk_id=chunk_id,
            ))
        
        logger.debug(
            "text_chunked",
            extra={
                "file_path": file_path,
                "total_lines": len(lines),
                "chunk_count": len(chunks),
            },
        )
        
        return chunks
    
    def _estimate_overlap_lines(self) -> int:
        """Estimate number of lines needed for overlap."""
        # Assume average 40 chars per line, estimate lines for overlap
        avg_chars_per_line = 40
        overlap_chars = self.overlap_tokens * CHARS_PER_TOKEN
        return max(1, overlap_chars // avg_chars_per_line)
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Uses simple character-based estimation.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        # Simple estimation: ~4 chars per token for code
        # Add bonus for whitespace/newlines which often split
        return max(1, len(text) // CHARS_PER_TOKEN + text.count("\n") // 2)
    
    def _generate_chunk_id(self, file_path: str, start: int, end: int) -> str:
        """Generate a unique chunk ID."""
        content = f"{file_path}:{start}:{end}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def retrieve_relevant_chunks(
        self, 
        chunks: List[TextChunk], 
        query: str,
        top_k: int = 3
    ) -> List[TextChunk]:
        """Retrieve most relevant chunks for a query using keyword matching.
        
        Uses a simple TF-IDF-like scoring for relevance.
        
        Args:
            chunks: List of chunks to search
            query: Query string
            top_k: Maximum number of chunks to return
            
        Returns:
            List of most relevant chunks
        """
        if not chunks or not query.strip():
            return chunks[:top_k] if chunks else []
        
        # Extract query keywords
        query_keywords = self._extract_keywords(query)
        if not query_keywords:
            return chunks[:top_k]
        
        # Score each chunk
        scored: List[Tuple[float, TextChunk]] = []
        for chunk in chunks:
            chunk_keywords = self._extract_keywords(chunk.content)
            score = self._compute_relevance(query_keywords, chunk_keywords)
            scored.append((score, chunk))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [chunk for _, chunk in scored[:top_k]]
    
    def _extract_keywords(self, text: str) -> Dict[str, int]:
        """Extract keywords from text with frequency counts."""
        # Simple keyword extraction
        # Remove common code symbols and split on whitespace
        text = text.lower()
        # Remove code symbols but keep underscores for snake_case
        text = re.sub(r'[^\w\s_]', ' ', text)
        
        # Split and count
        words = text.split()
        
        # Filter out very common words
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "of", "at", "by",
            "for", "with", "about", "against", "between", "into", "through",
            "during", "before", "after", "above", "below", "to", "from", "up",
            "down", "in", "out", "on", "off", "over", "under", "again", "further",
            "then", "once", "here", "there", "when", "where", "why", "how", "all",
            "each", "few", "more", "most", "other", "some", "such", "no", "nor",
            "not", "only", "own", "same", "so", "than", "too", "very", "s", "t",
            "just", "don", "now", "if", "else", "elif", "return", "import", "from",
            "class", "def", "self", "none", "true", "false", "pass", "raise",
            "try", "except", "finally", "with", "as", "for", "while", "break",
            "continue", "yield", "lambda", "and", "or", "not", "in", "is",
        }
        
        keywords: Dict[str, int] = {}
        for word in words:
            if word and len(word) > 1 and word not in stopwords:
                keywords[word] = keywords.get(word, 0) + 1
        
        return keywords
    
    def _compute_relevance(
        self, 
        query_keywords: Dict[str, int],
        chunk_keywords: Dict[str, int]
    ) -> float:
        """Compute relevance score between query and chunk keywords."""
        if not query_keywords or not chunk_keywords:
            return 0.0
        
        score = 0.0
        for word, query_freq in query_keywords.items():
            if word in chunk_keywords:
                chunk_freq = chunk_keywords[word]
                # Simple TF product
                score += query_freq * chunk_freq
        
        # Normalize by chunk length to avoid favoring long chunks
        total_chunk_freq = sum(chunk_keywords.values())
        if total_chunk_freq > 0:
            score /= (1 + total_chunk_freq ** 0.5)
        
        return score
    
    def build_context(
        self,
        files: List[Path],
        query: str,
        max_tokens: Optional[int] = None
    ) -> str:
        """Build context string from files, respecting token limits.
        
        Chunks files and retrieves the most relevant chunks for the query.
        
        Args:
            files: List of file paths to include
            query: Query for relevance scoring
            max_tokens: Maximum tokens (defaults to max_context_tokens)
            
        Returns:
            Context string built from relevant chunks
        """
        max_tokens = max_tokens or self.max_context_tokens
        
        all_chunks: List[TextChunk] = []
        for file_path in files:
            chunks = self.chunk_file(file_path)
            all_chunks.extend(chunks)
        
        # Get relevant chunks
        relevant = self.retrieve_relevant_chunks(all_chunks, query, top_k=20)
        
        # Build context string respecting token limit
        context_parts: List[str] = []
        current_tokens = 0
        
        for chunk in relevant:
            if current_tokens + chunk.token_count > max_tokens:
                break
            
            # Add file header
            header = f"\n### {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line})\n"
            header_tokens = self.count_tokens(header)
            
            if current_tokens + header_tokens + chunk.token_count > max_tokens:
                break
            
            context_parts.append(header)
            context_parts.append(chunk.content)
            current_tokens += header_tokens + chunk.token_count
        
        return "".join(context_parts)
    
    def get_chunk_with_context(
        self,
        chunk: TextChunk,
        context_lines: int = 5
    ) -> str:
        """Get a chunk with surrounding context lines.
        
        Args:
            chunk: The chunk to expand
            context_lines: Number of additional context lines on each side
            
        Returns:
            The chunk content with context
        """
        return chunk.content  # For now, just return the chunk as-is


@dataclass
class ArtifactContext:
    """Context from execution artifacts for QA checks.
    
    Manages chunks from multiple files and provides query-based retrieval
    for QA gates.
    
    Example:
        manager = SmartContextManager()
        artifact_ctx = ArtifactContext()
        
        for file in changed_files:
            chunks = manager.chunk_file(file)
            artifact_ctx.add_chunks(chunks)
        
        relevant = artifact_ctx.get_relevant_for_checklist("security review")
    """
    
    chunks: List[TextChunk] = field(default_factory=list)
    total_files: int = 0
    total_tokens: int = 0
    _file_set: set = field(default_factory=set)
    
    def add_chunks(self, chunks: List[TextChunk]) -> None:
        """Add chunks from a file.
        
        Args:
            chunks: List of chunks to add
        """
        for chunk in chunks:
            if chunk.file_path not in self._file_set:
                self._file_set.add(chunk.file_path)
                self.total_files += 1
        
        self.chunks.extend(chunks)
        self.total_tokens += sum(c.token_count for c in chunks)
    
    def add_file(self, manager: SmartContextManager, file_path: Path) -> None:
        """Add a file using a context manager.
        
        Args:
            manager: SmartContextManager instance
            file_path: Path to file to add
        """
        chunks = manager.chunk_file(file_path)
        self.add_chunks(chunks)
    
    def get_relevant_for_checklist(self, checklist_item: str) -> str:
        """Get context relevant to a checklist item.
        
        Args:
            checklist_item: Checklist item description
            
        Returns:
            Context string relevant to the checklist item
        """
        if not self.chunks:
            return ""
        
        manager = SmartContextManager()
        relevant = manager.retrieve_relevant_chunks(self.chunks, checklist_item, top_k=5)
        
        parts = []
        for chunk in relevant:
            parts.append(f"# {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line})\n")
            parts.append(chunk.content)
            parts.append("\n\n")
        
        return "".join(parts)
    
    def get_relevant_for_gate(self, gate_id: str, gate_name: str) -> str:
        """Get context relevant to a gate check.
        
        Args:
            gate_id: Gate identifier
            gate_name: Gate name
            
        Returns:
            Context string relevant to the gate
        """
        # Combine gate ID and name for better query
        query = f"{gate_id} {gate_name}"
        return self.get_relevant_for_checklist(query)
    
    def clear(self) -> None:
        """Clear all stored chunks."""
        self.chunks.clear()
        self._file_set.clear()
        self.total_files = 0
        self.total_tokens = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "chunks": [c.to_dict() for c in self.chunks],
            "total_files": self.total_files,
            "total_tokens": self.total_tokens,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactContext":
        """Create from dictionary representation."""
        chunks = [TextChunk.from_dict(c) for c in data.get("chunks", [])]
        instance = cls(
            chunks=chunks,
            total_files=data.get("total_files", 0),
            total_tokens=data.get("total_tokens", 0),
        )
        instance._file_set = {c.file_path for c in chunks}
        return instance

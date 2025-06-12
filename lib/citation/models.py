"""
Citation data models and structures.
Defines core data classes and legacy compatibility structures.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Citation:
    """Simple citation data structure."""
    id: str
    content: str
    source_title: str
    case_number: Optional[str] = None
    page_number: Optional[int] = None
    confidence: float = 1.0
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_markdown(self) -> str:
        """Convert to markdown citation format."""
        parts = [f"[{self.id}]"]
        if self.case_number:
            parts.append(f"Case Number: {self.case_number}")
        parts.append(f"Source: {self.source_title}")
        if self.page_number:
            parts.append(f"Page {self.page_number}")
        return " - ".join(parts)


@dataclass
class CitationRegistry:
    """Legacy CitationRegistry for backward compatibility."""
    citations: Dict[str, Dict[str, Any]]
    source_mappings: Dict[str, str] = None
    search_session_id: Optional[str] = None

    def __post_init__(self):
        if not self.citations:
            self.citations = {}
        if not self.source_mappings:
            self.source_mappings = {}

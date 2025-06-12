"""
Abstract base classes for search providers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

# Import project configuration
try:
    import os
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from config.project_config import get_project_config
except ImportError:
    def get_project_config():
        return None


class SearchMode(Enum):
    """Available search modes."""
    TEXT = "text"
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    VECTOR = "vector"


class DocumentType(Enum):
    """Available document types for internal search with metadata."""
    # Static types that don't come from config
    WEB_SEARCH = "web_search"  # For future web search implementation
    ACADEMIC = "academic"
    REPORTS = "reports"
    DOCUMENTS = "documents"
    REGULATORY = "regulatory"

    def __new__(cls, value):
        """Create new enum member."""
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __eq__(self, other):
        """Compare DocumentType objects by value."""
        if isinstance(other, DocumentType):
            return self.value == other.value
        elif hasattr(other, 'value'):
            return self.value == other.value
        elif isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self):
        """Hash DocumentType objects by value."""
        return hash(self.value)

    @classmethod
    def _missing_(cls, value):
        """Handle missing enum values by creating them dynamically."""
        # Allow dynamic creation of document types from project config
        return None

    @classmethod
    def get_configured_types(cls):
        """Get document types from project configuration."""
        configured_types = {}

        try:
            project_config = get_project_config()
            if project_config:
                for doc_type_config in project_config.document_types:
                    configured_types[doc_type_config.name] = doc_type_config.name
        except Exception:
            pass

        return configured_types

    @classmethod
    def get_all_types(cls):
        """Get all available document types (static + configured)."""
        all_types = {}

        # Add static types
        for member in cls:
            all_types[member.value] = member

        # Add configured types
        configured = cls.get_configured_types()
        for name, value in configured.items():
            if value not in all_types:
                # Create dynamic enum-like object with proper equality
                class DynamicDocumentType:
                    def __init__(self, value, name):
                        self.value = value
                        self.name = name.upper()

                    def __eq__(self, other):
                        if isinstance(other, DocumentType):
                            return self.value == other.value
                        elif hasattr(other, 'value'):
                            return self.value == other.value
                        elif isinstance(other, str):
                            return self.value == other
                        return False

                    def __hash__(self):
                        return hash(self.value)

                    def get_metadata(self):
                        return cls._get_metadata_for_type(self.value)

                all_types[value] = DynamicDocumentType(value, name)

        return all_types

    def get_metadata(self):
        """Get metadata for this document type from project configuration."""
        # Handle special case for WEB_SEARCH (not in project config)
        if self == self.WEB_SEARCH:
            return {
                "display_name": "Web Search",
                "display_name_en": "Web Search",
                "key_fields": ["url", "title", "content"],
                "content_fields": ["content"],
                "category": "web"
            }

        try:
            project_config = get_project_config()
            if project_config:
                # Find matching document type in project config
                for doc_type_config in project_config.document_types:
                    # Map config name to enum value
                    if doc_type_config.name == self.value:
                        return {
                            "display_name": doc_type_config.display_name,
                            "display_name_en": doc_type_config.display_name_en,
                            "key_fields": doc_type_config.key_fields,
                            "content_fields": doc_type_config.content_fields,
                            "index_name": doc_type_config.index_name,
                            "semantic_config": doc_type_config.semantic_config,
                            "vector_field": doc_type_config.vector_field,
                            "category": doc_type_config.name  # Use name as category
                        }
        except Exception:
            pass

        # Return None for unknown types - no fallback
        return None

    @classmethod
    def _get_metadata_for_type(cls, type_value: str):
        """Get metadata for a given document type value."""
        try:
            project_config = get_project_config()
            if project_config:
                for doc_type_config in project_config.document_types:
                    if doc_type_config.name == type_value:
                        return {
                            "display_name": doc_type_config.display_name,
                            "display_name_en": doc_type_config.display_name_en,
                            "key_fields": doc_type_config.key_fields,
                            "content_fields": doc_type_config.content_fields,
                            "index_name": doc_type_config.index_name,
                            "semantic_config": doc_type_config.semantic_config,
                            "vector_field": doc_type_config.vector_field,
                            # Remove business-specific category logic; use only
                            # generic if needed
                        }
        except Exception:
            pass
        return None

    # Removed: _get_category_from_name_static (no business-specific or
    # keyword-based logic)

    @classmethod
    def from_name(cls, name: str):
        """Get DocumentType enum from string name."""
        # Check static types first
        for member in cls:
            if member.value == name:
                return member

        # Check configured types
        configured_types = cls.get_configured_types()
        if name in configured_types:
            # Create a dynamic type object with proper equality
            class DynamicDocumentType:
                def __init__(self, value, name):
                    self.value = value
                    self.name = name.upper()

                def __eq__(self, other):
                    if isinstance(other, DocumentType):
                        return self.value == other.value
                    elif hasattr(other, 'value'):
                        return self.value == other.value
                    elif isinstance(other, str):
                        return self.value == other
                    return False

                def __hash__(self):
                    return hash(self.value)

                def get_metadata(self):
                    return cls._get_metadata_for_type(self.value)

            return DynamicDocumentType(name, name)

        raise ValueError(f"Unknown document type: {name}. Available static types: {
                         [m.value for m in cls]}, Configured types: {list(configured_types.keys())}")

    @classmethod
    def get_available_types(cls):
        """Get list of all available document type names."""
        available = [
            member.value for member in cls if member != cls.WEB_SEARCH]

        # Add configured types
        configured = cls.get_configured_types()
        available.extend(configured.keys())

        return available

    @classmethod
    def get_available_types_with_metadata(cls):
        """Get list of all available document types with their metadata."""
        types_with_metadata = []

        # Add static types (except WEB_SEARCH)
        for member in cls:
            if member != cls.WEB_SEARCH:
                metadata = member.get_metadata()
                if metadata:
                    types_with_metadata.append({
                        "name": member.value,
                        "metadata": metadata
                    })

        # Add configured types
        configured = cls.get_configured_types()
        for name in configured.keys():
            metadata = cls._get_metadata_for_type(name)
            if metadata:
                types_with_metadata.append({
                    "name": name,
                    "metadata": metadata
                })

        return types_with_metadata

    @classmethod
    def create_dynamic_type(cls, name: str):
        """Create a dynamic document type from configuration."""
        configured_types = cls.get_configured_types()
        if name in configured_types:
            return cls.from_name(name)
        else:
            raise ValueError(
                f"Document type '{name}' not found in configuration")


@dataclass
class SearchQuery:
    """Search query parameters."""
    text: str
    top_k: int = 10
    filter_expression: Optional[str] = None
    use_hybrid_search: bool = True
    use_semantic_search: bool = True
    document_type: Optional[DocumentType] = None


@dataclass
class SearchResult:
    """Search result data structure."""
    content_text: str
    search_type: str
    search_mode: str
    document_title: Optional[str] = None
    content_path: Optional[str] = None
    page_number: Optional[int] = None
    score: Optional[float] = None
    reranker_score: Optional[float] = None
    highlights: Optional[Dict[str, Any]] = None
    captions: Optional[List[Dict[str, Any]]] = None
    answers: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SearchStatistics:
    """Search provider statistics."""
    provider_name: str
    index_name: Optional[str] = None
    endpoint: Optional[str] = None
    status: str = "unknown"
    error: Optional[str] = None
    document_count: Optional[int] = None
    last_updated: Optional[str] = None


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    @abstractmethod
    def __init__(self, config: Any):
        """Initialize the search provider with configuration."""
        pass

    @abstractmethod
    async def search(
        self,
        query: SearchQuery,
        document_type: DocumentType
    ) -> List[SearchResult]:
        """
        Perform search operation.

        Args:
            query: Search query parameters
            document_type: Type of documents to search

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    async def search_all(
        self,
        query: SearchQuery,
        top_k_per_source: int = 5
    ) -> List[SearchResult]:
        """
        Search across all available document types.

        Args:
            query: Search query parameters
            top_k_per_source: Maximum results per document type

        Returns:
            List of aggregated search results
        """
        pass

    @abstractmethod
    def get_statistics(self) -> Dict[str, SearchStatistics]:
        """Get search provider statistics."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the search provider is available."""
        pass

    @abstractmethod
    def get_supported_document_types(self) -> List[DocumentType]:
        """Get list of supported document types."""
        pass


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for the given text.

        Args:
            text: Text to generate embedding for

        Returns:
            Embedding vector
        """
        pass

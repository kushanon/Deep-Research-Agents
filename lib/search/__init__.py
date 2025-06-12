"""
Modular search package for internal documents and future web search capabilities.

This package provides:
- Abstracted search providers (Azure AI Search, Web Search)
- Unified search management
- Semantic Kernel plugin integration
- Support for multiple document types and search modes

Usage:
    # Use the Semantic Kernel plugin (recommended for existing code)
    from lib.search import ModularSearchPlugin
    plugin = ModularSearchPlugin()

    # Use the search manager directly for advanced scenarios
    from lib.search import SearchManager, SearchQuery, DocumentType
    manager = SearchManager(config)
    # Use from_name to get document type dynamically
    doc_type = DocumentType.from_name("category_a")
    results = await manager.search(SearchQuery("query"), doc_type)

    # Use specific providers
    from lib.search.providers import AzureSearchProvider
    provider = AzureSearchProvider(config)
"""

from .base import (DocumentType, EmbeddingProvider, SearchMode, SearchProvider,
                   SearchQuery, SearchResult, SearchStatistics)
from .manager import SearchManager
from .plugin import ModularSearchPlugin
from .providers import (AzureEmbeddingProvider, AzureSearchProvider,
                        WebSearchProvider)

__all__ = [
    # Base classes and models
    'SearchProvider',
    'EmbeddingProvider',
    'SearchQuery',
    'SearchResult',
    'SearchStatistics',
    'DocumentType',
    'SearchMode',

    # Main components
    'SearchManager',
    'ModularSearchPlugin',

    # Providers
    'AzureSearchProvider',
    'AzureEmbeddingProvider',
    'WebSearchProvider'
]

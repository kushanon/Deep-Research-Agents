"""
Search manager for orchestrating multiple search providers.
"""
import logging
from typing import Any, Dict, List, Optional

from .base import (DocumentType, SearchProvider, SearchQuery, SearchResult,
                   SearchStatistics)
from .providers.azure_search import AzureSearchProvider
from .providers.web_search import WebSearchProvider

logger = logging.getLogger(__name__)


class SearchManager:
    """Manager for orchestrating multiple search providers."""

    def __init__(self, config: Any):
        """Initialize search manager with available providers."""
        self.config = config
        self.providers: Dict[str, SearchProvider] = {}

        # Initialize available providers
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize all available search providers."""
        try:
            # Initialize Azure Search Provider
            azure_provider = AzureSearchProvider(self.config)
            if azure_provider.is_available():
                self.providers["azure"] = azure_provider
                logger.info("Azure Search Provider registered")
            else:
                logger.warning("Azure Search Provider is not available")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Search Provider: {e}")

        try:
            # Check if web search is enabled in configuration
            web_search_enabled = True  # Default to enabled for backward compatibility

            # Try to get web search configuration from project config
            try:
                from lib.config.project_config import get_project_config
                project_config = get_project_config()
                if project_config and hasattr(project_config, 'web_search'):
                    web_search_enabled = project_config.web_search.enabled
                    logger.info(
                        f"Web search enabled from config: {web_search_enabled}")
            except Exception as e:
                logger.warning(
                    f"Could not load web search configuration, defaulting to enabled: {e}")

            if web_search_enabled:
                # Initialize Web Search Provider
                web_provider = WebSearchProvider(self.config)
                if web_provider.is_available():
                    self.providers["web"] = web_provider
                    logger.info("Web Search Provider registered")
                else:
                    logger.warning(
                        "Web Search Provider is not available - check Tavily API key configuration")
            else:
                logger.info("Web Search Provider disabled by configuration")
        except Exception as e:
            logger.error(f"Failed to initialize Web Search Provider: {e}")
            logger.info("Web search functionality will be disabled")

        logger.info(f"Search Manager initialized with {
                    len(self.providers)} providers: {list(self.providers.keys())}")

    async def search(
        self,
        query: SearchQuery,
        document_type: DocumentType,
        provider_name: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Perform search using specified or best available provider.

        Args:
            query: Search query parameters
            document_type: Type of documents to search
            provider_name: Specific provider to use (optional)

        Returns:
            List of search results
        """
        provider = self._get_provider_for_search(document_type, provider_name)
        if not provider:
            raise ValueError(
                f"No available provider for document type {document_type}")

        return await provider.search(query, document_type)

    async def search_internal_all(
        self,
        query: SearchQuery,
        top_k_per_source: int = None,
        provider_name: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Search across all available internal document types.

        Args:
            query: Search query parameters
            top_k_per_source: Maximum results per document type (uses project config default if None)
            provider_name: Specific provider to use (optional)

        Returns:
            List of aggregated search results
        """
        # Use project config default if not specified
        if top_k_per_source is None:
            try:
                from config.project_config import get_project_config
                project_config = get_project_config()
                if project_config and hasattr(project_config, 'search'):
                    top_k_per_source = project_config.search.default_top_k_per_source
                else:
                    top_k_per_source = 15  # fallback default
            except Exception:
                top_k_per_source = 15  # fallback default
        # Only use internal providers for search_internal_all
        internal_providers = {k: v for k, v in self.providers.items() if k != "web"}
        if provider_name and provider_name in internal_providers:
            provider = internal_providers[provider_name]
        else:
            provider = next(iter(internal_providers.values())) if internal_providers else None

        if not provider:
            raise ValueError("No available internal providers for search_internal_all")

        return await provider.search_all(query, top_k_per_source)

    async def search_multi_provider(
        self,
        query: SearchQuery,
        document_type: DocumentType,
        max_results_per_provider: int = 10
    ) -> Dict[str, List[SearchResult]]:
        """
        Search using multiple providers and return results from each.

        Args:
            query: Search query parameters
            document_type: Type of documents to search
            max_results_per_provider: Maximum results per provider

        Returns:
            Dictionary mapping provider name to search results
        """
        results = {}

        for provider_name, provider in self.providers.items():
            if self._provider_supports_document_type(provider, document_type):
                try:
                    search_query = SearchQuery(
                        text=query.text,
                        top_k=max_results_per_provider,
                        filter_expression=query.filter_expression,
                        use_hybrid_search=query.use_hybrid_search,
                        use_semantic_search=query.use_semantic_search,
                        document_type=document_type
                    )
                    provider_results = await provider.search(search_query, document_type)
                    results[provider_name] = provider_results
                except Exception as e:
                    logger.warning(
                        f"Search failed for provider {provider_name}: {e}")
                    results[provider_name] = []

        return results

    async def search_multimodal(
        self,
        query: SearchQuery,
        document_type: DocumentType,
        include_images: bool = True,
        include_text: bool = True,
        provider_name: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Perform multimodal search with content type filtering.

        Args:
            query: Search query parameters
            document_type: Type of documents to search
            include_images: Whether to include image-based content
            include_text: Whether to include text-based content
            provider_name: Specific provider to use (optional)

        Returns:
            List of search results filtered by content type
        """
        provider = self._get_provider_for_search(document_type, provider_name)
        if not provider:
            raise ValueError(
                f"No available provider for document type {document_type}")

        # Check if provider supports multimodal search
        if hasattr(provider, 'search_multimodal'):
            return await provider.search_multimodal(query, document_type, include_images, include_text)
        else:
            # Fallback to regular search with post-processing
            results = await provider.search(query, document_type)

            # Filter results based on content type if metadata is available
            filtered_results = []
            for result in results:
                if result.metadata and "content_type" in result.metadata:
                    content_type = result.metadata["content_type"]

                    should_include = False
                    if content_type == "text" and include_text:
                        should_include = True
                    elif content_type == "image" and include_images:
                        should_include = True
                    elif content_type == "mixed" and (include_text or include_images):
                        should_include = True

                    if should_include:
                        filtered_results.append(result)
                else:
                    # If no content type metadata, include by default
                    filtered_results.append(result)

            logger.info(f"Multimodal search completed via fallback: {len(
                filtered_results)} results " f"(images: {include_images}, text: {include_text})")

            return filtered_results

    def get_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics from all providers."""
        all_stats = {}

        for provider_name, provider in self.providers.items():
            try:
                all_stats[provider_name] = provider.get_statistics()
            except Exception as e:
                logger.error(
                    f"Failed to get statistics from {provider_name}: {e}")
                all_stats[provider_name] = {
                    "error": SearchStatistics(
                        provider_name=provider_name,
                        status="error",
                        error=str(e)
                    )
                }

        return all_stats

    def get_multimodal_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get multimodal-specific statistics from all providers."""
        stats = {}

        for provider_name, provider in self.providers.items():
            try:
                provider_stats = provider.get_statistics()

                # Add multimodal capabilities information
                multimodal_info = {
                    "supports_multimodal": hasattr(
                        provider, 'search_multimodal'), "supports_image_search": hasattr(
                        provider, 'search_multimodal'), "supports_image_understanding": hasattr(
                        provider, 'search_multimodal'), "index_schemas": {}}

                # Get index schema information for multimodal indexes
                if hasattr(provider, 'search_clients'):
                    for doc_type, client in provider.search_clients.items():
                        index_name = client._index_name

                        # Enhanced multimodal detection
                        is_multimodal = "multimodal" in index_name.lower()

                        # Check for image-specific fields and understanding
                        # capabilities
                        has_image_document_id = False
                        has_location_metadata = False
                        has_bounding_polygons = False
                        has_verbalization_capability = False
                        image_fields = []
                        text_fields = []

                        # Try to access index schema if available
                        schema = None
                        if hasattr(client, 'get_index_schema'):
                            try:
                                schema = client.get_index_schema()
                            except Exception as e:
                                logger.warning(
                                    f"Failed to get index schema for {doc_type}: {e}")
                                # Try fallback method if primary method fails
                                if hasattr(client, 'get_index_definition'):
                                    try:
                                        schema = client.get_index_definition()
                                        logger.debug(
                                            f"Successfully retrieved schema using fallback method for {doc_type}")
                                    except Exception as e2:
                                        logger.warning(
                                            f"Failed to get index definition for {doc_type}: {e2}")
                        elif hasattr(client, 'get_index_definition'):
                            try:
                                schema = client.get_index_definition()
                            except Exception as e:
                                logger.warning(
                                    f"Failed to get index definition for {doc_type}: {e}")

                        # Analyze schema for image understanding features
                        if schema and 'fields' in schema:
                            for field in schema['fields']:
                                field_name = field.get('name', '')

                                # Detect image fields
                                if field_name == 'image_document_id':
                                    has_image_document_id = True
                                    image_fields.append(field_name)
                                elif 'image' in field_name.lower():
                                    image_fields.append(field_name)

                                # Detect text fields
                                if field_name == 'content_text' or field_name == 'document_title':
                                    text_fields.append(field_name)

                                # Detect location metadata (indicates image
                                # understanding)
                                if field_name == 'locationMetadata' and field.get(
                                        'type') == 'Edm.ComplexType':
                                    has_location_metadata = True

                                    # Check for bounding polygons in nested
                                    # fields
                                    if 'fields' in field:
                                        for subfield in field['fields']:
                                            if subfield.get(
                                                    'name') == 'boundingPolygons':
                                                has_bounding_polygons = True

                            # Check if verbalization is likely supported
                            has_verbalization_capability = is_multimodal or has_location_metadata

                            # Check for vectorizers that support image
                            # verbalization
                            if 'vectorSearch' in schema and 'vectorizers' in schema['vectorSearch']:
                                for vectorizer in schema['vectorSearch']['vectorizers']:
                                    if vectorizer.get('kind') == 'azureOpenAI' or 'multimodal' in vectorizer.get(
                                            'name', '').lower():
                                        has_verbalization_capability = True

                        # Determine image understanding capabilities based on
                        # detected features
                        supports_image_understanding = has_image_document_id or has_location_metadata or has_bounding_polygons

                        multimodal_info["index_schemas"][doc_type.value] = {
                            "index_name": index_name,
                            "is_multimodal": is_multimodal or supports_image_understanding,
                            "supports_images": is_multimodal or len(image_fields) > 0,
                            "supports_text": True,  # All indexes support text
                            "supports_image_verbalization": has_verbalization_capability,
                            "supports_image_understanding": supports_image_understanding,
                            "has_image_document_id": has_image_document_id,
                            "has_location_metadata": has_location_metadata,
                            "has_bounding_polygons": has_bounding_polygons,
                            "image_fields": image_fields,
                            "text_fields": text_fields,
                            "vector_field": getattr(provider, 'vector_field_map', {}).get(doc_type, "content_embedding")
                        }

                        # Add semantic configuration info if available
                        if hasattr(provider, 'semantic_config_map'):
                            semantic_config = provider.semantic_config_map.get(
                                doc_type)
                            if semantic_config:
                                multimodal_info["index_schemas"][doc_type.value]["semantic_config"] = semantic_config

                stats[provider_name] = {
                    "provider_stats": provider_stats,
                    "multimodal_info": multimodal_info
                }

            except Exception as e:
                logger.error(
                    f"Failed to get multimodal statistics from {provider_name}: {e}")
                stats[provider_name] = {
                    "error": str(e)
                }

        return stats

    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self.providers.keys())

    def get_available_document_types(self) -> Dict[str, List[DocumentType]]:
        """Get available document types per provider."""
        doc_types = {}

        for provider_name, provider in self.providers.items():
            doc_types[provider_name] = provider.get_supported_document_types()

        return doc_types

    def _get_provider_for_search(
        self,
        document_type: DocumentType,
        provider_name: Optional[str] = None
    ) -> Optional[SearchProvider]:
        """Get the best provider for a specific search."""
        if provider_name and provider_name in self.providers:
            provider = self.providers[provider_name]
            if self._provider_supports_document_type(provider, document_type):
                return provider
            else:
                logger.warning(
                    f"Provider {provider_name} does not support {document_type}")

        # Find first available provider that supports the document type
        for provider in self.providers.values():
            if self._provider_supports_document_type(provider, document_type):
                return provider

        return None

    def _provider_supports_document_type(
            self,
            provider: SearchProvider,
            document_type: DocumentType) -> bool:
        """Check if provider supports the document type using value comparison."""
        supported_types = provider.get_supported_document_types()

        # Check for exact object match first
        if document_type in supported_types:
            return True

        # Check for value-based match
        document_type_value = getattr(
            document_type, 'value', str(document_type))
        for supported_type in supported_types:
            supported_value = getattr(
                supported_type, 'value', str(supported_type))
            if document_type_value == supported_value:
                return True

        return False

    def add_provider(self, name: str, provider: SearchProvider):
        """Add a search provider to the manager."""
        if provider.is_available():
            self.providers[name] = provider
            logger.info(f"{name.title()} Search Provider registered")
        else:
            logger.warning(f"{name.title()} Search Provider is not available")

    def remove_provider(self, name: str):
        """Remove a search provider from the manager."""
        if name in self.providers:
            del self.providers[name]
            logger.info(f"{name.title()} Search Provider removed")

    def get_provider(self, name: str) -> Optional[SearchProvider]:
        """Get a specific search provider by name."""
        return self.providers.get(name)

    async def search_web(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search using the WebSearchProvider."""
        try:
            # Get web search provider
            web_provider = self.providers.get("web")
            if not web_provider:
                logger.error("Web search provider is not available")
                return {"error": "Web search provider is not available", "results": []}
            
            # Execute web search
            logger.info(f"Performing web search with query: {search_params.get('query', '')[:50]}")
            
            # Create a basic SearchQuery from search_params for compatibility
            # Web provider may use search_params directly or convert as needed
            response = await web_provider.search_web(search_params)
            
            return response
            
        except Exception as e:
            logger.error(f"Web search failed: {str(e)}")
            return {"error": f"Web search failed: {str(e)}", "results": []}

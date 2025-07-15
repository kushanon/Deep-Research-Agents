"""
Azure AI Search provider implementation.
"""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import openai
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery

from ..base import (DocumentType, EmbeddingProvider, SearchMode,
                    SearchProvider, SearchQuery, SearchResult,
                    SearchStatistics)

# Import project configuration
try:
    import os
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from config.project_config import get_project_config
except ImportError:
    def get_project_config():
        return None

logger = logging.getLogger(__name__)


class AzureEmbeddingProvider(EmbeddingProvider):
    """Azure OpenAI embedding provider."""

    def __init__(self, config: Any):
        """Initialize Azure OpenAI embedding provider."""
        self.openai_client = openai.AzureOpenAI(
            azure_endpoint=config.azure_openai_endpoint,
            api_key=config.azure_openai_api_key,
            api_version=config.azure_openai_api_version
        )
        self.embedding_model = config.azure_embedding_deployment

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector using Azure OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return []


class AzureSearchProvider(SearchProvider):
    """Azure AI Search provider implementation."""

    def __init__(self, config: Any):
        """Initialize Azure Search provider."""
        self.config = config
        self.search_session_id = str(uuid.uuid4())

        # Get project configuration
        self.project_config = get_project_config()

        # Initialize embedding provider
        self.embedding_provider = AzureEmbeddingProvider(config)

        # Use API Key authentication for Azure Search
        credential = AzureKeyCredential(config.azure_search_api_key)

        # Initialize search clients dynamically from project config
        self.search_clients = {}
        self.semantic_config_map = {}
        self.vector_field_map = {}

        if self.project_config:
            # Use project configuration to build search clients
            for doc_type_config in self.project_config.document_types:
                # Map document type name to enum
                doc_type = self._get_document_type_enum(doc_type_config.name)
                if doc_type:
                    self.search_clients[doc_type] = SearchClient(
                        endpoint=config.azure_search_endpoint,
                        index_name=doc_type_config.index_name,
                        credential=credential
                    )
                    self.semantic_config_map[doc_type] = doc_type_config.semantic_config
                    self.vector_field_map[doc_type] = doc_type_config.vector_field
        else:
            # No project config available - cannot initialize search clients
            logger.error(
                "Project configuration is required for Azure Search Provider initialization")
            raise ValueError(
                "Project configuration not found. Please ensure project_config.yaml is available.")

        logger.info("Azure Search Provider initialized successfully")

        logger.info("Azure Search Provider initialized successfully")

    def _document_types_match(
            self,
            type1: DocumentType,
            type2: DocumentType) -> bool:
        """Check if two document types match by value."""
        value1 = getattr(type1, 'value', str(type1))
        value2 = getattr(type2, 'value', str(type2))
        return value1 == value2

    def _get_document_type_enum(self, name: str) -> Optional[Any]:
        """Map document type name to enum or dynamic type."""
        try:
            # Try to get from DocumentType enum
            return DocumentType.from_name(name)
        except ValueError:
            # If not found, return None
            return None

    def _get_content_fields_for_document_type(self, document_type: DocumentType) -> List[str]:
        """Get content_fields configuration for specific document type."""
        if not self.project_config:
            return []
        
        document_type_value = getattr(document_type, 'value', str(document_type))
        for doc_type_config in self.project_config.document_types:
            if doc_type_config.name == document_type_value:
                return doc_type_config.content_fields
        
        return []

    def _get_key_fields_for_document_type(self, document_type: DocumentType) -> List[str]:
        """Get key_fields configuration for specific document type."""
        if not self.project_config:
            return []
        
        document_type_value = getattr(document_type, 'value', str(document_type))
        for doc_type_config in self.project_config.document_types:
            if doc_type_config.name == document_type_value:
                return doc_type_config.key_fields
        
        return []

    async def search(
        self,
        query: SearchQuery,
        document_type: DocumentType
    ) -> List[SearchResult]:
        """Perform search on specific document type."""
        # Find matching client using value-based comparison
        client_doc_type = None
        for doc_type in self.search_clients.keys():
            if self._document_types_match(doc_type, document_type):
                client_doc_type = doc_type
                break

        if client_doc_type is None:
            raise ValueError(
                f"Document type {document_type} not supported by Azure Search Provider")

        search_mode = SearchMode.HYBRID if query.use_hybrid_search else SearchMode.TEXT
        logger.info(
            f"Performing {
                search_mode.value} search on {
                document_type.value}: '{
                query.text}' (top {
                    query.top_k})")

        try:
            client = self.search_clients[client_doc_type]

            # Build search parameters
            search_params = {
                "search_text": query.text,
                "top": min(query.top_k, 50),
                "include_total_count": True
            }

            # Configure search mode
            if query.use_hybrid_search:
                # Generate embedding for vector search
                query_vector = await self.embedding_provider.generate_embedding(query.text)
                if query_vector:
                    vector_field = self.vector_field_map.get(
                        client_doc_type, "content_embedding")

                    search_params["vector_queries"] = [
                        VectorizedQuery(
                            vector=query_vector,
                            k_nearest_neighbors=query.top_k,
                            fields=vector_field
                        )
                    ]

                    # Configure semantic search
                    if query.use_semantic_search and client_doc_type in self.semantic_config_map:
                        try:
                            search_params["query_type"] = "semantic"
                            search_params["semantic_configuration_name"] = self.semantic_config_map[client_doc_type]
                        except Exception as e:
                            logger.warning(
                                f"Semantic search setup failed, falling back to simple: {e}")
                            search_params["query_type"] = "simple"
                    else:
                        search_params["query_type"] = "simple"
                else:
                    logger.warning(
                        "Failed to generate embedding, falling back to text search")
                    search_params["query_type"] = "simple"
            else:
                search_params["query_type"] = "simple"

            # Add filter if provided
            if query.filter_expression:
                self._validate_filter_expression(
                    query.filter_expression, client_doc_type)
                search_params["filter"] = query.filter_expression

            # Execute search with fallback handling
            try:
                search_results = client.search(**search_params)
            except Exception as semantic_error:
                if search_params.get("query_type") == "semantic":
                    logger.warning(
                        f"Semantic search failed, retrying with simple search: {semantic_error}")
                    search_params["query_type"] = "simple"
                    search_params.pop("semantic_configuration_name", None)
                    search_results = client.search(**search_params)
                else:
                    raise

            # Process results
            results = self._process_search_results(
                search_results, client_doc_type, search_mode)

            logger.info(
                f"Found {
                    len(results)} results for {
                    document_type.value} using {
                    search_mode.value} search")
            return results

        except Exception as e:
            logger.error(
                f"Search execution failed for {
                    document_type.value}: {e}")
            raise

    async def search_all(
        self,
        query: SearchQuery,
        top_k_per_source: int = None  # Will be set from project config if None
    ) -> List[SearchResult]:
        """Search across all document types."""
        logger.info(
            f"Performing comprehensive search across all document types: '{
                query.text}'")

        all_results = []

        for doc_type in self.get_supported_document_types():
            try:
                # Determine top_k for this document type
                if top_k_per_source is not None:
                    # Use explicitly provided top_k_per_source
                    doc_type_top_k = top_k_per_source
                else:
                    # Use per-type top_k from search examples or default
                    doc_type_top_k = self._get_per_type_top_k(
                        doc_type, top_k_per_source)

                # Create query for this document type
                doc_query = SearchQuery(
                    text=query.text,
                    top_k=doc_type_top_k,
                    filter_expression=query.filter_expression,
                    use_hybrid_search=query.use_hybrid_search,
                    use_semantic_search=query.use_semantic_search,
                    document_type=doc_type
                )

                results = await self.search(doc_query, doc_type)

                # Add document type metadata
                for result in results:
                    if result.metadata is None:
                        result.metadata = {}
                    result.metadata["document_type"] = doc_type.value
                    result.metadata["source_index"] = doc_type.value

                all_results.extend(results)

            except Exception as e:
                logger.warning(f"Failed to search {doc_type.value}: {e}")
                continue

        # Sort by relevance score
        all_results.sort(key=lambda x: x.score or 0, reverse=True)

        logger.info(
            f"Comprehensive search completed. Found {
                len(all_results)} total results")
        return all_results

    def _get_per_type_top_k(
            self,
            document_type: DocumentType,
            fallback_top_k: int = None) -> int:
        """Get per-document-type top_k from project config search examples."""
        try:
            if self.project_config and hasattr(
                    self.project_config, 'get_search_example'):
                document_type_value = getattr(
                    document_type, 'value', str(document_type))
                search_example = self.project_config.get_search_example(
                    document_type_value)

                if search_example and 'parameters' in search_example:
                    per_type_top_k = search_example['parameters'].get('top_k')
                    if per_type_top_k is not None:
                        logger.debug(
                            f"Using per-type top_k={per_type_top_k} for {document_type_value}")
                        return per_type_top_k
        except Exception as e:
            logger.warning(
                f"Failed to get per-type top_k for {document_type}: {e}")

        # Use provided fallback
        if fallback_top_k is not None:
            return fallback_top_k

        # Use project config default
        if self.project_config and hasattr(self.project_config, 'search'):
            return self.project_config.search.default_top_k_per_source

        # Final fallback
        return 15

    def get_statistics(self) -> Dict[str, SearchStatistics]:
        """Get Azure Search statistics."""
        stats = {}

        for doc_type, client in self.search_clients.items():
            try:
                stats[doc_type.value] = SearchStatistics(
                    provider_name="Azure AI Search",
                    index_name=client._index_name,
                    endpoint=client._endpoint,
                    status="available"
                )
            except Exception as e:
                stats[doc_type.value] = SearchStatistics(
                    provider_name="Azure AI Search",
                    status="error",
                    error=str(e)
                )

        return stats

    def is_available(self) -> bool:
        """Check if Azure Search is available."""
        try:
            # Simple availability check
            return len(self.search_clients) > 0
        except Exception:
            return False

    def get_supported_document_types(self) -> List[DocumentType]:
        """Get supported document types."""
        return list(self.search_clients.keys())

    def _validate_filter_expression(
            self,
            filter_expression: str,
            document_type: Any) -> None:
        """Validate filter expression for common issues."""
        if 'date' in filter_expression.lower() and 'date' not in filter_expression.replace(
                'updated',
                '').replace(
                'created',
                ''):
            available_fields = "text_document_id (string), image_document_id (string), locationMetadata/pageNumber (int)"
            # Check document type using metadata
            if hasattr(document_type, 'value'):
                metadata = getattr(document_type, 'get_metadata', lambda: {})()
                if metadata and metadata.get('category') == 'list':
                    available_fields = "parent_id (string)"
            else:
                available_fields = "text_document_id (string), image_document_id (string), locationMetadata/pageNumber (int)"

            type_value = getattr(document_type, 'value', str(document_type))
            raise ValueError(
                f"Invalid filter field 'date'. Available filterable fields for {type_value}: "
                f"{available_fields}. Note: Date filtering is not supported in the current index schema."
            )

    def _process_search_results(
        self,
        search_results: Any,
        document_type: DocumentType,
        search_mode: SearchMode
    ) -> List[SearchResult]:
        """Process raw search results into SearchResult objects with multimodal support."""
        results = []

        # If search_results is a coroutine, we need to get the actual results
        # This is needed for testing with mock objects that return coroutines
        if hasattr(search_results, '__await__'):
            import asyncio
            if asyncio.iscoroutine(search_results):
                # Since we can't await here in a sync method, we'll return an
                # empty list for testing
                return []

        # Get content_fields from project config for this document type
        content_fields = self._get_content_fields_for_document_type(document_type)
        logger.debug(f"Content fields for {document_type.value}: {content_fields}")

        for result in search_results:
            # Extract content text using configured content_fields
            content_text = self._extract_content_text(result, content_fields)
            if not content_text:
                continue

            # Create search result
            search_result = SearchResult(
                content_text=content_text,
                search_type=self._get_search_type_name(document_type),
                search_mode=search_mode.value
            )

            # Extract all configured content fields
            self._extract_configured_fields(result, search_result, content_fields)

            # Enhanced multimodal metadata extraction
            self._extract_multimodal_metadata(result, search_result, document_type)

            # Extract location metadata using configured fields
            self._extract_location_metadata(result, search_result, content_fields)

            # Search scores
            if "@search.score" in result:
                search_result.score = result["@search.score"]
            if "@search.reranker_score" in result:
                search_result.reranker_score = result["@search.reranker_score"]
            if "@search.highlights" in result:
                search_result.highlights = result["@search.highlights"]
            if "@search.captions" in result:
                search_result.captions = result["@search.captions"]
            if "@search.answers" in result:
                search_result.answers = result["@search.answers"]

            # Document type-specific metadata extraction
            metadata = getattr(document_type, 'get_metadata', lambda: {})()
            if metadata and metadata.get('category') == 'list':
                # Extract all available fields from content_fields configuration
                structured_metadata = {}
                
                for field in content_fields:
                    if field in result and result[field] is not None:
                        structured_metadata[field] = result[field]

                if structured_metadata:
                    if search_result.metadata is None:
                        search_result.metadata = {}
                    search_result.metadata.update(structured_metadata)
                    logger.debug(f"Extracted structured metadata: {list(structured_metadata.keys())}")

            results.append(search_result)

        logger.info(f"Processed {len(results)} search results using configuration-driven field extraction")
        return results

    def _get_search_type_name(self, document_type: DocumentType) -> str:
        """Get human-readable search type name from project configuration."""
        if self.project_config:
            document_type_value = getattr(
                document_type, 'value', str(document_type))
            for doc_type_config in self.project_config.document_types:
                if doc_type_config.name == document_type_value:
                    return doc_type_config.display_name_en

        # If no project config or type not found, use enum value
        return getattr(document_type, 'value', str(document_type))

    def _extract_multimodal_metadata(
            self, result: Dict[str, Any], search_result: SearchResult, document_type: DocumentType) -> None:
        """Extract multimodal-specific metadata from search results."""
        if search_result.metadata is None:
            search_result.metadata = {}

        # Get key_fields from project config to determine filterable fields
        key_fields = self._get_key_fields_for_document_type(document_type)
        logger.debug(f"Key fields for {document_type.value}: {key_fields}")
        
        # Extract multimodal identifiers from key_fields and result
        multimodal_fields = []
        for field in key_fields:
            if any(identifier in field.lower() for identifier in ['text_document_id', 'image_document_id', 'content_id']):
                multimodal_fields.append(field)
        
        logger.debug(f"Multimodal fields detected from key_fields: {multimodal_fields}")
        
        # Add configured multimodal fields to metadata
        for field in multimodal_fields:
            if field in result and result[field] is not None:
                search_result.metadata[field] = result[field]

        # Identify content type based on document IDs
        has_text_content = result.get("text_document_id") is not None
        has_image_content = result.get("image_document_id") is not None

        if has_text_content and not has_image_content:
            search_result.metadata["content_type"] = "text"
        elif has_image_content and not has_text_content:
            search_result.metadata["content_type"] = "image"
            # Add image verbalization indicator
            if "content_text" in result:
                search_result.metadata["is_image_verbalization"] = True
                search_result.metadata["description"] = "Image content described in natural language"
        elif has_text_content and has_image_content:
            search_result.metadata["content_type"] = "mixed"
        else:
            search_result.metadata["content_type"] = "unknown"

        # Log multimodal content detection
        content_type = search_result.metadata.get("content_type", "unknown")
        logger.debug(f"Detected {content_type} content in search result")

    async def search_multimodal(
        self,
        query: SearchQuery,
        document_type: DocumentType,
        include_images: bool = True,
        include_text: bool = True
    ) -> List[SearchResult]:
        """
        Perform multimodal search with content type filtering.

        Args:
            query: Search query parameters
            document_type: Type of documents to search
            include_images: Whether to include image-based content
            include_text: Whether to include text-based content

        Returns:
            List of search results filtered by content type
        """
        # Perform regular search first
        results = await self.search(query, document_type)

        # Filter results based on content type preferences
        filtered_results = []

        for result in results:
            content_type = result.metadata.get(
                "content_type", "mixed") if result.metadata else "mixed"

            should_include = False
            if content_type == "text" and include_text:
                should_include = True
            elif content_type == "image" and include_images:
                should_include = True
            elif content_type == "mixed" and (include_text or include_images):
                should_include = True

            if should_include:
                filtered_results.append(result)

        logger.info(f"Multimodal search completed: {len(filtered_results)} results "
                    f"(images: {include_images}, text: {include_text})")

        return filtered_results

    def _extract_content_text(self, result: Dict[str, Any], content_fields: List[str]) -> str:
        """Extract main content text using configured content_fields."""
        # Priority order for main content (generic field names only)
        content_priority = ["content_text", "chunk", "text", "description", "content"]
        
        for field in content_priority:
            if field in content_fields and field in result and result[field]:
                logger.debug(f"Selected main content field: '{field}' (priority match)")
                return str(result[field])
        
        # Use first available content field
        for field in content_fields:
            if field in result and result[field]:
                logger.debug(f"Selected main content field: '{field}' (first available)")
                return str(result[field])
        
        logger.debug("No suitable content field found for main content")
        return ""

    def _extract_configured_fields(self, result: Dict[str, Any], search_result: SearchResult, content_fields: List[str]) -> None:
        """Extract all configured content fields into search result."""
        if search_result.metadata is None:
            search_result.metadata = {}
        
        # Extract all content_fields into metadata
        extracted_fields = {}
        for field in content_fields:
            if field in result and result[field] is not None:
                extracted_fields[field] = result[field]
                
                # Set specific fields to SearchResult properties if they match
                if field == "document_title":
                    search_result.document_title = result[field]
                elif field == "content_path":
                    search_result.content_path = result[field]
        
        # Add all extracted fields to metadata
        search_result.metadata["extracted_fields"] = extracted_fields
        
        # Log what fields were extracted
        logger.debug(f"Extracted fields: {list(extracted_fields.keys())}")

    def _extract_location_metadata(self, result: Dict[str, Any], search_result: SearchResult, content_fields: List[str]) -> None:
        """Extract location metadata using configured content fields."""
        # Look for location-related fields in content_fields
        location_fields = []
        for field in content_fields:
            if any(location_term in field.lower() for location_term in ['location', 'metadata', 'page', 'polygon']):
                location_fields.append(field)
        
        logger.debug(f"Location fields detected from content_fields: {location_fields}")
        
        # Extract location metadata
        for field in location_fields:
            if field in result and result[field] is not None:
                if field == "locationMetadata" and isinstance(result[field], dict):
                    # Handle nested locationMetadata
                    location_meta = result[field]
                    if "pageNumber" in location_meta:
                        search_result.page_number = location_meta["pageNumber"]
                    if "boundingPolygons" in location_meta:
                        if search_result.metadata is None:
                            search_result.metadata = {}
                        search_result.metadata["boundingPolygons"] = location_meta["boundingPolygons"]
                    # Add entire locationMetadata to metadata
                    if search_result.metadata is None:
                        search_result.metadata = {}
                    search_result.metadata["locationMetadata"] = location_meta
                elif field == "pageNumber":
                    # Direct page number field
                    search_result.page_number = result[field]
                elif field == "boundingPolygons":
                    # Direct bounding polygons field
                    if search_result.metadata is None:
                        search_result.metadata = {}
                    search_result.metadata["boundingPolygons"] = result[field]
                else:
                    # Other location-related fields
                    if search_result.metadata is None:
                        search_result.metadata = {}
                    search_result.metadata[field] = result[field]

        # Log location metadata extraction
        if hasattr(search_result, 'page_number') and search_result.page_number:
            logger.debug(f"Extracted page number: {search_result.page_number}")
        if search_result.metadata and any(key in search_result.metadata for key in ['boundingPolygons', 'locationMetadata']):
            logger.debug("Extracted location metadata information")

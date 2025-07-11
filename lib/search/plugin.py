"""
Semantic Kernel plugin wrapper for the modular search system.
Dynamically generates search functions based on project configuration.
"""
import json
from typing import Annotated, Literal
import logging
from typing import Any, Callable, Dict, Optional

from semantic_kernel.functions import kernel_function

from .base import DocumentType, SearchQuery
from .manager import SearchManager

logger = logging.getLogger(__name__)


class ModularSearchPlugin:
    """Semantic Kernel plugin for the modular search system with dynamic function generation."""

    def __init__(self, config: Optional[any] = None):
        """Initialize the modular search plugin with dynamic functions."""
        if config is None:
            from ..config import get_config
            config = get_config()

        self.search_manager = SearchManager(config)
        self.config = config

        # Generate dynamic search functions based on project config
        self._generate_dynamic_functions()

        logger.info("Modular Search Plugin initialized with dynamic functions")
    
    def _toggle_internal_all_documents_function(self):
        """Enable or disable function calling for search_internal_all_documents based on _internal_functions_enabled."""
        if getattr(self, '_internal_functions_enabled', False):
            # Only add kernel_function decorator if enabled
            if not hasattr(self, '_search_internal_all_documents_decorated'):
                # Create a wrapper function and decorate it
                async def wrapped_search_internal_all_documents(
                    query: str,
                    top_k_per_source: int = None,
                    use_hybrid_search: bool = None,
                    use_semantic_search: bool = None
                ) -> str:
                    return await self.search_internal_all_documents(
                        query, top_k_per_source, use_hybrid_search, use_semantic_search
                    )
                
                decorated = kernel_function(
                    name="search_internal_all_documents",
                    description="Search across all internal document types using hybrid vector and semantic search"
                )(wrapped_search_internal_all_documents)
                
                # Replace the method with the decorated version
                setattr(self, 'search_internal_all_documents', decorated)
                self._search_internal_all_documents_decorated = True
        else:
            # Function calling is disabled - method remains undecorated but still callable
            if hasattr(self, '_search_internal_all_documents_decorated'):
                # Restore original method implementation
                original_method = self.__class__.search_internal_all_documents
                # Bind the unbound method to this instance
                setattr(self, 'search_internal_all_documents', original_method.__get__(self, self.__class__))
                del self._search_internal_all_documents_decorated

    def _generate_dynamic_functions(self):
        """Generate search functions dynamically based on project configuration."""
        try:
            internal_function_count = 0
            if hasattr(
                    self.config,
                    'project_config') and self.config.project_config:
                # Use project config to generate functions
                for doc_type in self.config.project_config.document_types:
                    self._create_search_function(doc_type)
                    internal_function_count += 1
                logger.info(f"Generated {internal_function_count} dynamic search functions")
                # Only enable search_internal_all_documents if at least one internal function exists
                self._internal_functions_enabled = internal_function_count > 0
                self._toggle_internal_all_documents_function()
            else:
                logger.error(
                    "Project configuration is required for ModularSearchPlugin")
                raise ValueError(
                    "Project configuration not found. Please ensure project_config.yaml is available.")

        except Exception as e:
            logger.error(f"Failed to generate dynamic functions: {e}")
            raise

    def _create_search_function(self, doc_type_config):
        """Create a search function for a specific document type with configuration-based defaults."""
        func_name = f"search_{doc_type_config.name}"

        # Get search example configuration for this document type
        search_example_config = None
        if hasattr(
                self.config,
                'project_config') and self.config.project_config:
            search_example_config = self.config.project_config.get_search_example(
                doc_type_config.name)

        # Extract default parameters from configuration
        config_defaults = {}
        if search_example_config:
            params = search_example_config.get('parameters', {})
            config_defaults = {
                'top_k': params.get('top_k', 10),
                'use_hybrid_search': params.get('use_hybrid_search', True),
                'use_semantic_search': params.get('use_semantic_search', True)
            }
        else:
            # Fallback to project config defaults
            default_top_k = 10
            if hasattr(
                    self.config,
                    'project_config') and self.config.project_config:
                default_top_k = self.config.project_config.search_config.default_top_k_per_source
            config_defaults = {
                'top_k': default_top_k,
                'use_hybrid_search': True,
                'use_semantic_search': True
            }

        # Create description with document type information and query examples
        description_parts = [
            f"Search for {doc_type_config.display_name} ({doc_type_config.display_name_en}) "
            f"using hybrid (vector + semantic) search. "
            f"Available filterable fields: {', '.join(doc_type_config.key_fields)}. "
            f"NOTE: Date filtering is NOT supported - use content-based search for time-related queries."
        ]

        # Add query examples if available
        if search_example_config and search_example_config.get(
                'query_examples'):
            # Limit to first 3 examples
            examples = search_example_config['query_examples'][:3]
            examples_str = '", "'.join(examples)
            description_parts.append(f" Example queries: \"{examples_str}\"")

        description = "".join(description_parts)

        # Create the search function with defaults from configuration
        async def search_function(
            query: str,
            top_k: int = config_defaults['top_k'],
            filter_expression: Optional[str] = None,
            use_hybrid_search: bool = config_defaults['use_hybrid_search'],
            use_semantic_search: bool = config_defaults['use_semantic_search']
        ) -> str:
            # Validate parameters against project limits
            max_limit = 200  # Default fallback
            if hasattr(
                    self.config,
                    'project_config') and self.config.project_config:
                max_limit = self.config.project_config.search.max_results_limit

            if top_k > max_limit:
                logger.warning(
                    f"top_k ({top_k}) exceeds max_results_limit ({max_limit}), using {max_limit}")
                top_k = max_limit

            return await self._execute_search(
                doc_type_config.name,
                query,
                top_k,
                filter_expression,
                use_hybrid_search,
                use_semantic_search
            )

        # Add kernel_function decorator
        decorated_function = kernel_function(
            name=func_name,
            description=description
        )(search_function)

        # Add function to the class
        setattr(self, func_name, decorated_function)
        logger.debug(f"Created dynamic function: {func_name} with config defaults: {config_defaults}")

        # Log query examples for debugging
        if search_example_config and search_example_config.get('query_examples'):
            logger.debug(f"Function {func_name} configured with query examples: {search_example_config['query_examples']}")

    async def _execute_search(
        self,
        doc_type_name: str,
        query: str,
        top_k: int,
        filter_expression: Optional[str],
        use_hybrid_search: bool,
        use_semantic_search: bool
    ) -> str:
        """Execute search for any document type."""
        try:
            # Convert document type name to enum
            doc_type = self._get_document_type_enum(doc_type_name)

            search_query = SearchQuery(
                text=query,
                top_k=top_k,
                filter_expression=filter_expression,
                use_hybrid_search=use_hybrid_search,
                use_semantic_search=use_semantic_search
            )

            results = await self.search_manager.search(search_query, doc_type)

            json_results = [self._result_to_dict(result) for result in results]
            return json.dumps(json_results, ensure_ascii=False, indent=2)

        except Exception as e:
            error_msg = f"{doc_type_name} search failed: {str(e)}"
            logger.error(error_msg)
            return json.dumps([{"error": error_msg}], ensure_ascii=False)

    def _get_document_type_enum(self, doc_type_name: str):
        """Convert document type name to DocumentType enum dynamically."""
        try:
            return DocumentType.from_name(doc_type_name)
        except ValueError as e:
            logger.error(f"Unknown document type: {doc_type_name}")
            raise e

    async def search_internal_all_documents(
        self,
        query: str,
        top_k_per_source: int = None,
        use_hybrid_search: bool = None,
        use_semantic_search: bool = None
    ) -> str:
        """Search across all internal document types for comprehensive results."""
        if not getattr(self, '_internal_functions_enabled', False):
            error_msg = "search_internal_all_documents is not enabled because no internal search functions exist."
            logger.error(error_msg)
            return json.dumps([{"error": error_msg}], ensure_ascii=False)
        try:
            # Get search example configuration for all_documents if available
            search_example_config = None
            if hasattr(
                    self.config,
                    'project_config') and self.config.project_config:
                search_example_config = self.config.project_config.get_search_example(
                    "all_documents")

            # Apply configuration defaults
            if search_example_config:
                params = search_example_config.get('parameters', {})
                if top_k_per_source is None:
                    top_k_per_source = params.get('top_k', 15)
                if use_hybrid_search is None:
                    use_hybrid_search = params.get('use_hybrid_search', True)
                if use_semantic_search is None:
                    use_semantic_search = params.get(
                        'use_semantic_search', True)
            else:
                # Fallback to project config defaults
                if top_k_per_source is None:
                    if hasattr(
                            self.config,
                            'project_config') and self.config.project_config:
                        top_k_per_source = self.config.project_config.search_config.default_top_k_per_source
                    else:
                        top_k_per_source = 15
                if use_hybrid_search is None:
                    use_hybrid_search = True
                if use_semantic_search is None:
                    use_semantic_search = True

            # Validate against max results limit
            max_limit = 200  # Default fallback
            if hasattr(
                    self.config,
                    'project_config') and self.config.project_config:
                max_limit = self.config.project_config.search.max_results_limit

            if top_k_per_source > max_limit:
                logger.warning(f"top_k_per_source ({top_k_per_source}) exceeds max_results_limit ({
                               max_limit}), using {max_limit}")
                top_k_per_source = max_limit

            search_query = SearchQuery(
                text=query,
                top_k=top_k_per_source,
                use_hybrid_search=use_hybrid_search,
                use_semantic_search=use_semantic_search
            )

            results = await self.search_manager.search_internal_all(
                search_query,
                top_k_per_source
            )

            json_results = [self._result_to_dict(result) for result in results]
            return json.dumps(json_results, ensure_ascii=False, indent=2)

        except Exception as e:
            error_msg = f"Comprehensive search failed: {str(e)}"
            logger.error(error_msg)
            return json.dumps([{"error": error_msg}], ensure_ascii=False)

    def _result_to_dict(self, result) -> dict:
        """Convert SearchResult object to dictionary for JSON serialization."""
        result_dict = {
            "content_text": result.content_text,
            "search_type": result.search_type,
            "search_mode": result.search_mode
        }

        # Add optional fields if they exist
        if result.document_title:
            result_dict["document_title"] = result.document_title
        if result.content_path:
            result_dict["content_path"] = result.content_path
        if result.page_number is not None:
            result_dict["page_number"] = result.page_number
        if result.score is not None:
            result_dict["score"] = result.score
        if result.reranker_score is not None:
            result_dict["reranker_score"] = result.reranker_score
        if result.highlights:
            result_dict["highlights"] = result.highlights
        if result.captions:
            result_dict["captions"] = result.captions
        if result.answers:
            result_dict["answers"] = result.answers
        if result.metadata:
            result_dict.update(result.metadata)

        return result_dict
    
    @kernel_function(
        name="web_search",
        description="Perform comprehensive web search using external API with advanced filtering and image support. Returns top results from the web only, not internal documents."
    )
    async def web_search(
        self,
        query: Annotated[str, "Search query string."],
        top_k: Annotated[int, "Maximum number of results to return (default 20).", 20] = 20,
        time_range: Annotated[Optional[Literal["day", "week", "month", "year"]], "Optional time filter. Choices: 'day', 'week', 'month', 'year'."] = None,
        topic: Annotated[Literal["general", "news", "finance"], "Search topic. Choices: 'general', 'news', 'finance'."] = "general",
        search_depth: Annotated[Literal["basic", "advanced"], "Search depth. Choices: 'basic', 'advanced'."] = "advanced",
        include_image_descriptions: Annotated[bool, "Include query-related images and descriptions."] = False
    ) -> Annotated[str, "JSON string containing search results."]:
        """
        Perform web search using external API with enhanced error handling.

        Args:
            query: Search query string
            top_k: Maximum number of results to return (default 10)
            time_range: Optional time filter ("day", "week", "month", "year")
            topic: Search topic ("general", "news", "finance")
            search_depth: Search depth ("basic", "advanced")
            include_image_descriptions: Include query-related images and descriptions

        Returns:
            str: JSON string containing search results
        """
        logger.info(
            f"Web search called - Query: '{query[:50]}{'...' if len(query) > 50 else ''}', "
            f"max_results: {top_k}, time_range: {time_range}, topic: {topic}, "
            f"search_depth: {search_depth}, include_images: {include_image_descriptions}"
        )
        try:
            # Build search parameters
            search_params = {
                "query": query,
                "max_results": min(top_k, 50),
                "topic": topic,
                "search_depth": search_depth,
                "include_answer": False,
                "include_raw_content": False
            }
            if include_image_descriptions:
                search_params["include_image_descriptions"] = True
                search_params["include_images"] = True
            valid_time_ranges = ["day", "week", "month", "year"]
            if time_range and time_range in valid_time_ranges:
                search_params["time_range"] = time_range

            logger.debug(f"Built search parameters: {search_params}")

            # Execute web search (assumes search_manager.search_web exists)
            response = await self.search_manager.search_web(search_params)

            # Process and validate response
            results = response.get('results', []) if isinstance(response, dict) else []
            processed_results = []
            for result in results:
                if not isinstance(result, dict):
                    continue
                result_data = {
                    "url": result.get('url', ''),
                    "title": result.get('title', ''),
                    "snippet": result.get('content', ''),
                    "score": result.get('score', 0.0),
                    "published_date": result.get('published_date', ''),
                    "domain": result.get('domain', '')
                }
                if 'raw_content' in result and result['raw_content']:
                    result_data['raw_content'] = result['raw_content']
                processed_results.append(result_data)

            # Optionally process images if requested
            if include_image_descriptions and 'images' in response:
                for img in response['images']:
                    processed_results.append({
                        "image_url": img.get('url', ''),
                        "image_description": img.get('description', '')
                    })

            logger.info(f"Web search completed - Found {len(processed_results)} results (including images if requested)")
            logger.debug(f"Response summary - Results: {len(results)}, Images: {len(response.get('images', []))}")

            return json.dumps(processed_results, ensure_ascii=False, indent=2)

        except Exception as e:
            error_msg = f"Web search failed: {str(e)}"
            logger.error(error_msg)
            return json.dumps([{"error": error_msg}], ensure_ascii=False)
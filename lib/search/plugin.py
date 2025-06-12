"""
Semantic Kernel plugin wrapper for the modular search system.
Dynamically generates search functions based on project configuration.
"""
import json
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

    def _generate_dynamic_functions(self):
        """Generate search functions dynamically based on project configuration."""
        try:
            if hasattr(
                    self.config,
                    'project_config') and self.config.project_config:
                # Use project config to generate functions
                for doc_type in self.config.project_config.document_types:
                    self._create_search_function(doc_type)
                logger.info(f"Generated {
                            len(self.config.project_config.document_types)} dynamic search functions")
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
        logger.debug(f"Created dynamic function: {
                     func_name} with config defaults: {config_defaults}")

        # Log query examples for debugging
        if search_example_config and search_example_config.get(
                'query_examples'):
            logger.debug(
                f"Function {func_name} configured with query examples: {
                    search_example_config['query_examples']}")

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

    @kernel_function(name="search_all_documents",
                     description="Search across all internal document types using hybrid vector and semantic search")
    async def search_all_documents(
        self,
        query: str,
        top_k_per_source: int = None,
        use_hybrid_search: bool = None,
        use_semantic_search: bool = None
    ) -> str:
        """Search across all document types for comprehensive results."""
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

            results = await self.search_manager.search_all(
                search_query,
                top_k_per_source
            )

            json_results = [self._result_to_dict(result) for result in results]
            return json.dumps(json_results, ensure_ascii=False, indent=2)

        except Exception as e:
            error_msg = f"Comprehensive search failed: {str(e)}"
            logger.error(error_msg)
            return json.dumps([{"error": error_msg}], ensure_ascii=False)

    @kernel_function(name="get_search_statistics",
                     description="Get statistics about available search indexes and providers")
    def get_search_statistics(self) -> str:
        """Get statistics about search providers and indexes."""
        try:
            stats = self.search_manager.get_all_statistics()
            return json.dumps(stats, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            error_msg = f"Failed to get search statistics: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg}, ensure_ascii=False)

    @kernel_function(name="list_available_searches",
                     description="List all available search functions and their descriptions")
    def list_available_searches(self) -> str:
        """List all dynamically created search functions."""
        try:
            available_functions = []

            # Get all methods that start with 'search_' and have
            # kernel_function decorator
            for attr_name in dir(self):
                if attr_name.startswith(
                        'search_') and attr_name != 'search_all_documents':
                    attr = getattr(self, attr_name)
                    if hasattr(attr, '__kernel_function__'):
                        func_info = {
                            "function_name": attr_name,
                            "description": getattr(
                                attr,
                                '__kernel_function_description__',
                                'No description available')}
                        available_functions.append(func_info)

            return json.dumps({
                "available_search_functions": available_functions,
                "total_count": len(available_functions)
            }, ensure_ascii=False, indent=2)

        except Exception as e:
            error_msg = f"Failed to list available searches: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg}, ensure_ascii=False)

    @kernel_function(name="get_search_suggestions",
                     description="Get search query suggestions for a specific document type based on configuration examples")
    async def get_search_suggestions(
        self,
        document_type: str = None
    ) -> str:
        """Get search query suggestions based on configuration examples."""
        try:
            suggestions = {}

            if document_type and document_type != "all":
                # Get suggestions for specific document type
                search_example_config = None
                if hasattr(
                        self.config,
                        'project_config') and self.config.project_config:
                    search_example_config = self.config.project_config.get_search_example(
                        document_type)

                if search_example_config and search_example_config.get(
                        'query_examples'):
                    suggestions[document_type] = {
                        'description': search_example_config.get('description', ''),
                        'examples': search_example_config['query_examples']
                    }
                else:
                    suggestions[document_type] = {
                        'description': f"No examples configured for {document_type}", 'examples': []}
            else:
                # Get suggestions for all document types
                if hasattr(
                        self.config,
                        'project_config') and self.config.project_config:
                    for doc_type in self.config.project_config.document_types:
                        search_example_config = self.config.project_config.get_search_example(
                            doc_type.name)
                        if search_example_config and search_example_config.get(
                                'query_examples'):
                            suggestions[doc_type.name] = {
                                'display_name': doc_type.display_name,
                                'description': search_example_config.get('description', ''),
                                'examples': search_example_config['query_examples']
                            }

            return json.dumps(suggestions, ensure_ascii=False, indent=2)

        except Exception as e:
            error_msg = f"Failed to get search suggestions: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg}, ensure_ascii=False)

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

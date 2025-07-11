"""
Web Search provider implementation using Tavily API.
"""
import datetime as dt
import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from tavily import TavilyClient

from ..base import (DocumentType, SearchProvider, SearchQuery, SearchResult,
                    SearchStatistics)

logger = logging.getLogger(__name__)


class WebSearchProvider(SearchProvider):
    """Web Search provider implementation using Tavily API."""

    def __init__(self, config: Any):
        """Initialize Web Search provider with Tavily API."""
        self.config = config

        # Get Tavily API key from config
        api_key = getattr(config, 'tavily_api_key', None)
        if not api_key:
            logger.error("Tavily API key not found in configuration")
            raise ValueError(
                "Tavily API key is required for web search functionality")

        # Initialize Tavily client
        try:
            # Initialize with timeout settings if supported
            self.client = TavilyClient(api_key=api_key)

            # Set timeout on the underlying HTTP client if available
            if hasattr(
                    self.client,
                    '_client') and hasattr(
                    self.client._client,
                    'timeout'):
                self.client._client.timeout = 30  # 30 second timeout

            logger.info("Tavily Web Search Provider initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Tavily client: {e}")
            raise

        # Get configuration parameters
        self.max_results = getattr(config, 'tavily_max_results', 10)
        self.max_retries = getattr(config, 'tavily_max_retries', 3)
        self.timeout = getattr(
            config,
            'tavily_timeout',
            30)  # Default 30 seconds

        # Statistics tracking
        self.search_count = 0
        self.error_count = 0
        self.last_search_time = None

    async def search(
        self,
        query: SearchQuery,
        document_type: DocumentType
    ) -> List[SearchResult]:
        """
        Perform web search operation using Tavily API.

        Args:
            query: Search query parameters
            document_type: Type of documents to search (must be WEB_SEARCH)

        Returns:
            List of SearchResult objects
        """
        if document_type != DocumentType.WEB_SEARCH:
            raise ValueError(
                f"Document type {document_type} not supported by Web Search Provider")

        logger.info(
            f"Performing web search for: '{
                self._truncate_text(
                    query.text, 50)}'")

        try:
            # Build search parameters
            search_params = self._build_search_params(query)

            # Execute search with retry logic
            response = await self._execute_search_with_retry(search_params)

            # Process and validate response
            results = self._process_search_response(response)

            # Update statistics
            self.search_count += 1
            self.last_search_time = dt.datetime.now(
                dt.timezone.utc).isoformat()

            logger.info(
                f"Web search completed successfully. Found {
                    len(results)} results")
            return results

        except Exception as e:
            self.error_count += 1
            error_msg = f"Web search failed: {str(e)}"
            logger.error(error_msg)

            # Return empty results instead of raising exception
            return []

    async def search_all(
        self,
        query: SearchQuery,
        top_k_per_source: int = 5
    ) -> List[SearchResult]:
        """Search across web (single source for web search)."""
        # Adjust query top_k for web search
        web_query = SearchQuery(
            text=query.text,
            top_k=min(top_k_per_source, self.max_results),
            filter_expression=query.filter_expression,
            use_hybrid_search=query.use_hybrid_search,
            use_semantic_search=query.use_semantic_search,
            document_type=DocumentType.WEB_SEARCH
        )

        return await self.search(web_query, DocumentType.WEB_SEARCH)

    def _build_search_params(self, query: SearchQuery) -> Dict[str, Any]:
        """Build search parameters for Tavily API."""
        search_params = {
            "query": query.text,
            "max_results": min(query.top_k, self.max_results),
            "topic": "general",
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "include_image_descriptions": False,
            "include_images": False
        }

        logger.debug(f"Search parameters: {search_params}")
        return search_params

    async def _execute_search_with_retry(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute search with retry logic and exponential backoff."""
        import asyncio
        import time
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Search attempt {
                             attempt + 1}/{self.max_retries}")

                # Execute the search directly with timeout handling
                start_time = time.time()

                try:
                    response = self.client.search(
                        query=search_params["query"],
                        max_results=search_params["max_results"],
                        topic=search_params["topic"],
                        search_depth=search_params["search_depth"],
                        include_answer=search_params["include_answer"],
                        include_raw_content=search_params["include_raw_content"],
                        include_image_descriptions=search_params["include_image_descriptions"],
                        include_images=search_params["include_images"],
                        timeout=self.timeout)
                    elapsed_time = time.time() - start_time
                    logger.debug(
                        f"Search completed in {
                            elapsed_time:.2f} seconds")

                except Exception as e:
                    elapsed_time = time.time() - start_time

                    # Handle specific error types
                    error_str = str(e).lower()
                    if "timeout" in error_str or "timed out" in error_str:
                        raise TimeoutError(
                            f"Search request timed out after {
                                elapsed_time:.1f} seconds")
                    elif "502" in error_str or "bad gateway" in error_str:
                        raise ConnectionError(
                            f"Server error (502 Bad Gateway) - Tavily API may be temporarily unavailable")
                    elif "503" in error_str or "service unavailable" in error_str:
                        raise ConnectionError(
                            f"Service temporarily unavailable (503) - Tavily API is down")
                    elif "429" in error_str or "rate limit" in error_str:
                        raise ConnectionError(
                            f"Rate limit exceeded - too many requests to Tavily API")
                    elif "401" in error_str or "unauthorized" in error_str:
                        raise ValueError(
                            f"Unauthorized - invalid Tavily API key")
                    elif "403" in error_str or "forbidden" in error_str:
                        raise ValueError(
                            f"Forbidden - Tavily API access denied")
                    elif "404" in error_str or "not found" in error_str:
                        raise ConnectionError(
                            f"API endpoint not found - check Tavily API URL")
                    else:
                        raise

                # Handle string response
                if isinstance(response, str):
                    try:
                        response = json.loads(response)
                    except json.JSONDecodeError as e:
                        raise ValueError(
                            f"Invalid JSON response from Tavily API: {e}")

                if not isinstance(response, dict):
                    raise ValueError(
                        f"Unexpected response type: {
                            type(response)}")

                logger.debug(f"Search attempt {attempt + 1} succeeded")
                return response

            except Exception as e:
                last_exception = e
                error_type = type(e).__name__
                logger.warning(
                    f"Search attempt {
                        attempt +
                        1} failed ({error_type}): {e}")

                if attempt < self.max_retries - 1:
                    # Adjust sleep time based on error type
                    if isinstance(e, TimeoutError):
                        # Linear backoff for timeouts
                        sleep_time = 2 * (attempt + 1)
                    elif isinstance(e, ConnectionError):
                        if "502" in str(e):
                            # Longer wait for server errors
                            sleep_time = 10 * (attempt + 1)
                        elif "503" in str(e):
                            # Even longer for service unavailable
                            sleep_time = 15 * (attempt + 1)
                        elif "rate limit" in str(e).lower():
                            # Much longer wait for rate limits
                            sleep_time = 60 * (attempt + 1)
                        else:
                            # Default for connection errors
                            sleep_time = 5 * (attempt + 1)
                    elif isinstance(e, ValueError):
                        # API key or authorization errors - don't retry
                        logger.error(
                            f"Authentication error - not retrying: {e}")
                        break
                    else:
                        sleep_time = 2 ** attempt  # Exponential backoff for other errors

                    logger.info(f"Retrying in {sleep_time} seconds... (attempt {
                                attempt + 2}/{self.max_retries})")
                    await asyncio.sleep(sleep_time)

        # If all retries failed
        logger.error(
            f"All {
                self.max_retries} search attempts failed. Last error: {last_exception}")
        raise last_exception

    def _process_search_response(
            self, response: Dict[str, Any]) -> List[SearchResult]:
        """Process and structure search response into SearchResult objects."""
        results = []
        search_results = response.get('results', [])

        if not search_results:
            logger.warning("No search results returned from Tavily API")
            return results

        for result in search_results:
            if not isinstance(result, dict):
                logger.warning(f"Invalid result format: {type(result)}")
                continue

            try:
                # Extract basic fields
                url = result.get('url', '')
                title = result.get('title', '')
                content = result.get('content', '')
                score = result.get('score', 0.0)
                published_date = result.get('published_date', '')

                # Create SearchResult object
                search_result = SearchResult(
                    content_text=content,
                    search_type="Web Search",
                    search_mode="web",
                    document_title=title,
                    content_path=url,
                    score=score,
                    metadata={
                        "url": url,
                        "title": title,
                        "domain": self._extract_domain(url),
                        "published_date": published_date,
                        "crawled_at": dt.datetime.now(
                            dt.timezone.utc).isoformat(),
                        "source": "tavily"})

                results.append(search_result)

            except Exception as e:
                logger.warning(f"Failed to process search result: {e}")
                continue

        # Validate results
        if not self._validate_search_results(results):
            logger.warning("Search results failed validation")
            return []

        logger.info(f"Successfully processed {len(results)} search results")
        return results

    def get_statistics(self) -> Dict[str, SearchStatistics]:
        """Get web search statistics."""
        return {
            "web_search": SearchStatistics(
                provider_name="Tavily Web Search",
                endpoint="https://api.tavily.com",
                status="available" if self.is_available() else "unavailable",
                error=None if self.error_count == 0 else f"{
                    self.error_count} errors occurred",
                document_count=self.search_count,
                last_updated=self.last_search_time)}

    def is_available(self) -> bool:
        """Check if web search is available."""
        try:
            # Check if web search is enabled in configuration
            try:
                from lib.config.project_config import get_project_config
                project_config = get_project_config()
                if project_config and hasattr(project_config, 'web_search'):
                    if not project_config.web_search.enabled:
                        return False
            except Exception:
                # If we can't load config, continue with other checks
                pass

            # Check if Tavily API key is configured
            api_key = getattr(self.config, 'tavily_api_key', None)
            if not api_key:
                return False

            # Check if client is initialized
            if not hasattr(self, 'client') or self.client is None:
                return False

            return True
        except Exception:
            return False

    def get_supported_document_types(self) -> List[DocumentType]:
        """Get supported document types."""
        return [DocumentType.WEB_SEARCH]

    async def search_web(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search using Tavily API with enhanced parameters."""
        try:
            query = search_params.get("query", "")
            if not query:
                return {"error": "Query is required", "results": []}

            # Extract parameters with defaults
            max_results = search_params.get("max_results", 10)
            topic = search_params.get("topic", "general")
            search_depth = search_params.get("search_depth", "advanced")
            include_answer = search_params.get("include_answer", False)
            include_raw_content = search_params.get("include_raw_content", False)
            include_images = search_params.get("include_images", False)
            include_image_descriptions = search_params.get("include_image_descriptions", False)
            time_range = search_params.get("time_range")

            # Build Tavily search parameters
            tavily_params = {
                "query": query,
                "max_results": min(max_results, 50),  # Limit to 50 max
                "topic": topic,
                "search_depth": search_depth,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
                "include_images": include_images or include_image_descriptions
            }

            # Add time range if specified
            if time_range:
                tavily_params["days"] = self._convert_time_range_to_days(time_range)

            logger.info(f"Executing Tavily search with params: {tavily_params}")

            # Execute search
            response = await self._execute_tavily_search(tavily_params)

            # Process and format response
            return self._format_web_search_response(response, include_image_descriptions)

        except Exception as e:
            logger.error(f"Web search failed: {str(e)}")
            return {"error": f"Web search failed: {str(e)}", "results": []}

    def _convert_time_range_to_days(self, time_range: str) -> int:
        """Convert time range string to days for Tavily API."""
        time_mapping = {
            "day": 1,
            "week": 7,
            "month": 30,
            "year": 365
        }
        return time_mapping.get(time_range, 7)  # Default to week

    async def _execute_tavily_search(self, tavily_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Tavily search with error handling."""
        try:
            # Execute search (Tavily client may not be async, wrap if needed)
            response = self.client.search(**tavily_params)
            return response
        except Exception as e:
            logger.error(f"Tavily API call failed: {str(e)}")
            raise

    def _format_web_search_response(self, response: Dict[str, Any], include_image_descriptions: bool = False) -> Dict[str, Any]:
        """Format Tavily response for consistent output."""
        try:
            results = response.get("results", [])
            formatted_results = []

            for result in results:
                formatted_result = {
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0.0),
                    "published_date": result.get("published_date", ""),
                    "domain": self._extract_domain(result.get("url", ""))
                }

                # Add raw content if available
                if "raw_content" in result:
                    formatted_result["raw_content"] = result["raw_content"]

                formatted_results.append(formatted_result)

            formatted_response = {
                "results": formatted_results,
                "query": response.get("query", ""),
                "follow_up_questions": response.get("follow_up_questions", [])
            }

            # Add answer if available
            if "answer" in response:
                formatted_response["answer"] = response["answer"]

            # Add images if requested and available
            if include_image_descriptions and "images" in response:
                formatted_response["images"] = response["images"]

            return formatted_response

        except Exception as e:
            logger.error(f"Failed to format web search response: {str(e)}")
            return {"error": f"Failed to format response: {str(e)}", "results": []}

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc
        except Exception:
            return ""

    def _validate_search_results(self, results: List[SearchResult]) -> bool:
        """Validate search results structure."""
        if not isinstance(results, list):
            return False

        for result in results:
            if not isinstance(result, SearchResult):
                return False
            if not result.content_text or not result.document_title:
                return False

        return True

    def _truncate_text(self, text: str, max_length: int = 1000) -> str:
        """Truncate text to specified length with ellipsis."""
        if text is None:
            return ""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

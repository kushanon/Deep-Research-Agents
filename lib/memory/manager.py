"""
Memory manager for semantic text storage and retrieval.
Handles core memory operations without Semantic Kernel plugin dependencies.
"""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from semantic_kernel.connectors.ai.open_ai import OpenAITextEmbedding
from semantic_kernel.memory import SemanticTextMemory, VolatileMemoryStore

from .utils import create_memory_metadata, format_memory_results

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Core memory management without Semantic Kernel plugin decorators.
    Handles storage, retrieval, and organization of semantic memories.
    """

    def __init__(
        self,
        embedding_generator: OpenAITextEmbedding,
        session_id: str,
        project_id: str = "",
        min_relevance_score: float = 0.3
    ):
        """
        Initialize memory manager.

        Args:
            embedding_generator: OpenAI text embedding service
            session_id: Unique session identifier
            project_id: Project identifier (defaults to session_id)
            min_relevance_score: Minimum relevance score for search results
        """
        self.embedding_generator = embedding_generator
        self.session_id = session_id
        self.project_id = project_id or session_id
        self.min_relevance_score = min_relevance_score

        # Initialize memory components
        self.memory_store = VolatileMemoryStore()
        self.semantic_memory = SemanticTextMemory(
            storage=self.memory_store,
            embeddings_generator=embedding_generator
        )

        # Collection naming
        self.collection_name = f"memory_{session_id}"
        self.logger = logging.getLogger(f"{__name__}.MemoryManager")

        # Initialization state
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize memory store and collection."""
        if self._initialized:
            self.logger.debug("Memory manager already initialized")
            return

        try:
            await self.memory_store.create_collection(self.collection_name)
            self.logger.info(
                f"[MEMORY INIT] Successfully initialized memory manager")
            self.logger.info(f"[MEMORY INIT] Session ID: {self.session_id}")
            self.logger.info(f"[MEMORY INIT] Project ID: {self.project_id}")
            self.logger.info(
                f"[MEMORY INIT] Collection: {
                    self.collection_name}")
            self._initialized = True
        except Exception as e:
            self.logger.debug(
                f"[MEMORY INIT] Collection may already exist: {e}")
            self.logger.info(
                f"[MEMORY INIT] Memory manager ready for session {
                    self.session_id}")
            self._initialized = True

    async def store_memory(
        self,
        content: str,
        entry_type: str = "general",
        source: str = "system",
        memory_type: str = "session",
        additional_metadata: dict = None
    ) -> str:
        """
        Store information in memory.

        Args:
            content: Text content to store
            entry_type: Type of memory entry
            source: Source of the memory
            memory_type: Memory type classification
            additional_metadata: Additional metadata fields

        Returns:
            str: Memory ID if successful, error message if failed
        """
        await self.initialize()

        try:
            memory_id = str(uuid.uuid4())

            # Create standardized metadata
            metadata = create_memory_metadata(
                source=source,
                entry_type=entry_type,
                session_id=self.session_id,
                project_id=self.project_id,
                additional_data=additional_metadata
            )

            # Add memory type
            metadata["memory_type"] = memory_type

            self.logger.info(f"[MEMORY STORE] Starting storage operation")
            self.logger.info(f"[MEMORY STORE] Source: {source}")
            self.logger.info(f"[MEMORY STORE] Type: {entry_type}")
            self.logger.info(
                f"[MEMORY STORE] Content length: {
                    len(content)} chars")
            self.logger.debug(f"[MEMORY STORE] Content preview: {
                              content[:100]}...")

            await self.semantic_memory.save_information(
                collection=self.collection_name,
                text=content,
                id=memory_id,
                description=f"{entry_type} from {source}",
                additional_metadata=json.dumps(metadata)
            )

            self.logger.info(f"[MEMORY STORE] Successfully stored memory")
            self.logger.info(f"[MEMORY STORE] Memory ID: {memory_id}")
            self.logger.info(f"[MEMORY STORE] {source} stored {
                             entry_type}: {content[:50]}...")
            return memory_id

        except Exception as e:
            self.logger.error(f"[MEMORY STORE] Failed to store memory: {e}")
            self.logger.error(f"[MEMORY STORE] Source: {
                              source}, Type: {entry_type}")
            return f"Error: {e}"

    async def search_memory(
        self,
        query: str,
        max_results: int = 5,
        entry_types: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        min_relevance_score: Optional[float] = None
    ) -> List[str]:
        """
        Search memory and return relevant content.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            entry_types: Filter by entry types
            sources: Filter by sources
            min_relevance_score: Override default minimum relevance score

        Returns:
            List[str]: List of relevant content strings
        """
        await self.initialize()

        try:
            relevance_threshold = min_relevance_score or self.min_relevance_score

            self.logger.info(f"[MEMORY SEARCH] Starting search operation")
            self.logger.info(f"[MEMORY SEARCH] Query: {query[:100]}...")
            self.logger.info(f"[MEMORY SEARCH] Max results: {max_results}")
            self.logger.info(
                f"[MEMORY SEARCH] Entry types filter: {entry_types}")
            self.logger.info(f"[MEMORY SEARCH] Sources filter: {sources}")
            self.logger.info(
                f"[MEMORY SEARCH] Min relevance: {relevance_threshold}")

            results = await self.semantic_memory.search(
                collection=self.collection_name,
                query=query,
                limit=max_results,
                min_relevance_score=relevance_threshold
            )

            self.logger.info(
                f"[MEMORY SEARCH] Raw results count: {
                    len(results)}")

            content_list = []
            filtered_count = 0

            for i, result in enumerate(results):
                # Apply filters
                if self._should_filter_result(result, entry_types, sources, i):
                    filtered_count += 1
                    continue

                content_list.append(result.text)
                self.logger.debug(f"[MEMORY SEARCH] Added result {
                                  i + 1}: {result.text[:50]}...")

            self.logger.info(f"[MEMORY SEARCH] Search completed")
            self.logger.info(
                f"[MEMORY SEARCH] Results returned: {
                    len(content_list)}")
            self.logger.info(
                f"[MEMORY SEARCH] Results filtered out: {filtered_count}")

            return content_list

        except Exception as e:
            self.logger.error(f"[MEMORY SEARCH] Memory search failed: {e}")
            self.logger.error(f"[MEMORY SEARCH] Query was: {query[:100]}...")
            return []

    def _should_filter_result(
        self,
        result,
        entry_types: Optional[List[str]],
        sources: Optional[List[str]],
        index: int
    ) -> bool:
        """
        Check if a search result should be filtered out.

        Args:
            result: Search result object
            entry_types: Entry types filter
            sources: Sources filter
            index: Result index for logging

        Returns:
            bool: True if result should be filtered out
        """
        if not entry_types and not sources:
            return False

        try:
            metadata = json.loads(result.metadata.additional_metadata or "{}")
            result_type = metadata.get("type", "unknown")
            result_source = metadata.get("source", "unknown")

            self.logger.debug(
                f"[MEMORY SEARCH] Result {
                    index +
                    1}: type={result_type}, source={result_source}")

            # Filter by entry types
            if entry_types and result_type not in entry_types:
                self.logger.debug(
                    f"[MEMORY SEARCH] Filtered out result {
                        index + 1} (type mismatch)")
                return True

            # Filter by sources
            if sources and result_source not in sources:
                self.logger.debug(
                    f"[MEMORY SEARCH] Filtered out result {
                        index + 1} (source mismatch)")
                return True

            return False

        except Exception as filter_error:
            self.logger.warning(
                f"[MEMORY SEARCH] Filter error for result {
                    index + 1}: {filter_error}")
            return False

    async def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory usage statistics.

        Returns:
            Dict[str, Any]: Memory statistics
        """
        await self.initialize()

        try:
            # This is a simplified stats implementation
            # In a real implementation, you might want to query the memory
            # store directly
            stats = {
                "session_id": self.session_id,
                "project_id": self.project_id,
                "collection_name": self.collection_name,
                "min_relevance_score": self.min_relevance_score,
                "initialized": self._initialized
            }

            self.logger.info(f"[MEMORY STATS] Retrieved memory statistics")
            return stats

        except Exception as e:
            self.logger.error(
                f"[MEMORY STATS] Failed to get memory stats: {e}")
            return {"error": str(e)}

    async def clear_memory(self, confirm_session_id: str) -> bool:
        """
        Clear all memory for the current session.

        Args:
            confirm_session_id: Session ID confirmation for safety

        Returns:
            bool: True if cleared successfully
        """
        if confirm_session_id != self.session_id:
            self.logger.warning(f"[MEMORY CLEAR] Session ID mismatch: provided {
                                confirm_session_id}, expected {self.session_id}")
            return False

        try:
            # Delete and recreate collection
            await self.memory_store.delete_collection(self.collection_name)
            await self.memory_store.create_collection(self.collection_name)

            self.logger.info(
                f"[MEMORY CLEAR] Successfully cleared memory for session {
                    self.session_id}")
            return True

        except Exception as e:
            self.logger.error(f"[MEMORY CLEAR] Failed to clear memory: {e}")
            return False

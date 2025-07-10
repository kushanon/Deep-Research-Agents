"""
Semantic Kernel plugin for memory operations.
Provides kernel function decorators for agent integration.
"""
import logging
from typing import Any, Dict, List, Optional

from semantic_kernel.functions import kernel_function

from .manager import MemoryManager
from .utils import format_memory_results

logger = logging.getLogger(__name__)


class MemoryPlugin:
    """
    Semantic Kernel plugin wrapper for MemoryManager.
    Provides kernel functions for agent memory operations.
    """

    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize memory plugin.

        Args:
            memory_manager: Core memory manager instance
        """
        self.memory_manager = memory_manager
        self.logger = logging.getLogger(f"{__name__}.MemoryPlugin")

    @kernel_function(name="remember_info",
                     description="Store important information")
    async def remember_info(
        self,
        content: str,
        agent_name: str,
        info_type: str = "general"
    ) -> str:
        """
        Store information from agents.

        Args:
            content: Information content to store
            agent_name: Name of the agent storing the information
            info_type: Type of information being stored

        Returns:
            str: Storage result message
        """
        self.logger.debug(
            f"[MEMORY KERNEL] remember_info called by {agent_name}")
        self.logger.debug(f"[MEMORY KERNEL] Info type: {info_type}")
        self.logger.debug(f"[MEMORY KERNEL] Content: {
                          content[:100]}... (length: {len(content)} chars)")

        memory_id = await self.memory_manager.store_memory(
            content=content,
            entry_type=info_type,
            source=agent_name
        )

        result = f"Stored: {memory_id}"
        self.logger.debug(f"[MEMORY KERNEL] remember_info result: {result}")
        return result

    @kernel_function(name="recall_info",
                     description="Search for relevant information")
    async def recall_info(
        self,
        query: str,
        agent_name: str,
        max_results: int = 5
    ) -> str:
        """
        Search memory for relevant information.

        Args:
            query: Search query
            agent_name: Name of the agent requesting information
            max_results: Maximum number of results to return

        Returns:
            str: Formatted search results
        """
        self.logger.debug(
            f"[MEMORY KERNEL] recall_info called by {agent_name}")
        self.logger.debug(f"[MEMORY KERNEL] Query: {query[:100]}...")
        self.logger.debug(f"[MEMORY KERNEL] Max results: {max_results}")

        results = await self.memory_manager.search_memory(query, max_results)

        if not results:
            result = "No relevant information found."
            self.logger.debug(f"[MEMORY KERNEL] recall_info: No results found")
            return result

        result = format_memory_results(results)
        self.logger.debug(
            f"[MEMORY KERNEL] recall_info: Returning {
                len(results)} results")
        self.logger.debug(f"[MEMORY KERNEL] recall_info result preview: {
                          result[:200]}...")

        return result

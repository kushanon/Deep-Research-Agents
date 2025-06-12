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

    @kernel_function(name="store_research_finding",
                     description="Store research findings with metadata")
    async def store_research_finding(
        self,
        finding: str,
        agent_name: str,
        confidence: str = "medium",
        category: str = "research"
    ) -> str:
        """
        Store research findings with additional metadata.

        Args:
            finding: Research finding content
            agent_name: Name of the researching agent
            confidence: Confidence level (low/medium/high)
            category: Research category

        Returns:
            str: Storage result message
        """
        self.logger.debug(
            f"[MEMORY KERNEL] store_research_finding called by {agent_name}")
        self.logger.debug(f"[MEMORY KERNEL] Confidence: {
                          confidence}, Category: {category}")

        additional_metadata = {
            "confidence": confidence,
            "category": category
        }

        memory_id = await self.memory_manager.store_memory(
            content=finding,
            entry_type="research_finding",
            source=agent_name,
            additional_metadata=additional_metadata
        )

        result = f"Research finding stored: {memory_id}"
        self.logger.debug(
            f"[MEMORY KERNEL] store_research_finding result: {result}")
        return result

    @kernel_function(name="recall_research_findings",
                     description="Search for research findings")
    async def recall_research_findings(
        self,
        query: str,
        agent_name: str,
        confidence_filter: str = "",
        max_results: int = 5
    ) -> str:
        """
        Search for research findings with optional confidence filtering.

        Args:
            query: Search query
            agent_name: Name of the requesting agent
            confidence_filter: Filter by confidence level (optional)
            max_results: Maximum number of results

        Returns:
            str: Formatted research findings
        """
        self.logger.debug(
            f"[MEMORY KERNEL] recall_research_findings called by {agent_name}")
        self.logger.debug(f"[MEMORY KERNEL] Query: {query[:100]}...")
        self.logger.debug(
            f"[MEMORY KERNEL] Confidence filter: {confidence_filter}")

        # Search for research findings specifically
        results = await self.memory_manager.search_memory(
            query=query,
            max_results=max_results,
            entry_types=["research_finding"]
        )

        if not results:
            result = "No relevant research findings found."
            self.logger.debug(
                f"[MEMORY KERNEL] recall_research_findings: No results found")
            return result

        # TODO: Implement confidence filtering if needed
        # This would require parsing metadata and filtering by confidence level

        result = format_memory_results(results)
        self.logger.debug(
            f"[MEMORY KERNEL] recall_research_findings: Returning {
                len(results)} findings")

        return result


class SharedMemoryPlugin:
    """
    Backward compatibility wrapper for the original SharedMemoryPluginSK.
    Provides the same interface as the original implementation.
    """

    def __init__(self, memory_plugin: MemoryPlugin):
        """
        Initialize shared memory plugin wrapper.

        Args:
            memory_plugin: Core memory plugin instance
        """
        self.memory_plugin = memory_plugin
        self.logger = logging.getLogger(f"{__name__}.SharedMemoryPlugin")

    @kernel_function(name="remember_info", description="Store information")
    async def remember_info(
        self,
        content: str,
        agent_name: str = "system",
        info_type: str = "general"
    ) -> str:
        """Backward compatibility method for remember_info."""
        return await self.memory_plugin.remember_info(content, agent_name, info_type)

    @kernel_function(name="recall_info", description="Recall information")
    async def recall_info(
        self,
        query: str,
        agent_name: str = "system",
        max_results: int = 5
    ) -> str:
        """Backward compatibility method for recall_info."""
        return await self.memory_plugin.recall_info(query, agent_name, max_results)

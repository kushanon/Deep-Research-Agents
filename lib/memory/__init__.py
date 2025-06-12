"""
Memory package - Modular memory management system.
Provides structured memory operations with management, plugin integration, and utilities.
"""

from typing import Optional

from semantic_kernel.connectors.ai.open_ai import OpenAITextEmbedding

# Core memory management
from .manager import MemoryManager
# Semantic Kernel integration
from .plugin import MemoryPlugin, SharedMemoryPlugin
# Utilities
from .utils import (create_azure_openai_text_embedding, create_memory_metadata,
                    format_memory_results)


class SKMemoryPlugin(MemoryPlugin):
    """
    Backward compatibility wrapper for the old SKMemoryPlugin interface.
    Creates a MemoryManager internally and passes it to the new MemoryPlugin.
    """

    def __init__(
            self,
            embedding_generator: OpenAITextEmbedding,
            session_id: str,
            project_id: str = ""):
        """
        Initialize SKMemoryPlugin with backward compatibility.

        Args:
            embedding_generator: OpenAI text embedding service
            session_id: Unique session identifier
            project_id: Project identifier (defaults to session_id)
        """
        # Create MemoryManager with the provided parameters
        memory_manager = MemoryManager(
            embedding_generator=embedding_generator,
            session_id=session_id,
            project_id=project_id
        )

        # Initialize the parent MemoryPlugin with the MemoryManager
        super().__init__(memory_manager)

        # Store original parameters for compatibility
        self.embedding_generator = embedding_generator
        self.session_id = session_id
        self.project_id = project_id

    async def initialize(self):
        """Initialize the memory plugin (backward compatibility method)."""
        # The new implementation doesn't need explicit initialization
        pass

    async def store_memory(
        self,
        content: str,
        entry_type: str = "general",
        source: str = "system",
        memory_type: str = "session",
        additional_metadata: dict = None
    ) -> str:
        """
        Backward compatibility method for store_memory.
        Delegates to the MemoryManager.
        """
        return await self.memory_manager.store_memory(
            content=content,
            entry_type=entry_type,
            source=source,
            memory_type=memory_type,
            additional_metadata=additional_metadata
        )


# Backward compatibility alias
SharedMemoryPluginSK = SharedMemoryPlugin

# Public API
__all__ = [
    # Core classes
    'MemoryManager',
    'MemoryPlugin',
    'SharedMemoryPlugin',

    # Utilities
    'create_azure_openai_text_embedding',
    'format_memory_results',
    'create_memory_metadata',

    # Backward compatibility
    'SKMemoryPlugin',
    'SharedMemoryPluginSK',
]

# Package metadata
__version__ = "2.0.0"
__author__ = "Deep Research Agents Team"
__description__ = "Modular memory management system for semantic text storage and retrieval"

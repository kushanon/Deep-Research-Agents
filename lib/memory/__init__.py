"""
Memory package - Modular memory management system.
Provides structured memory operations with management, plugin integration, and utilities.
"""

from semantic_kernel.connectors.ai.open_ai import OpenAITextEmbedding

# Core memory management
from .manager import MemoryManager
# Semantic Kernel integration
from .plugin import MemoryPlugin
# Utilities
from .utils import (create_azure_openai_text_embedding, create_memory_metadata,
                    format_memory_results)


# Backward compatibility aliases
SharedMemoryPlugin = MemoryPlugin
SharedMemoryPluginSK = MemoryPlugin

# Public API
__all__ = [
    # Core classes
    'MemoryManager',
    'MemoryPlugin',

    # Utilities
    'create_azure_openai_text_embedding',
    'format_memory_results',
    'create_memory_metadata',

    # Backward compatibility
    'SharedMemoryPlugin',
    'SharedMemoryPluginSK',
]

# Package metadata
__version__ = "2.0.0"
__author__ = "Deep Research Agents Team"
__description__ = "Modular memory management system for semantic text storage and retrieval"

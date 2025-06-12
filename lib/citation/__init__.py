"""
Citation package - Modular citation management system.
Provides structured citation handling with CRUD operations, validation, and formatting.
"""

# Custom agent implementations
from .agents import CustomCitationAgent
# Formatting utilities
from .formatters import CitationFormatter
# Business logic manager
from .manager import CitationManager, SimpleCitationManager
# Core models and data structures
from .models import Citation, CitationRegistry
# Semantic Kernel integration
from .plugins import CitationPlugin, SimpleCitationPlugin
# Validation utilities
from .validators import CitationValidator

# Backward compatibility aliases
CitationAgent = CustomCitationAgent
CitationAgentPlugin = SimpleCitationPlugin

# Public API
__all__ = [
    # Core classes
    'Citation',
    'CitationRegistry',
    'CitationManager',
    'CitationValidator',
    'CitationFormatter',
    'CitationPlugin',
    'CustomCitationAgent',

    # Backward compatibility
    'SimpleCitationManager',
    'SimpleCitationPlugin',
    'CitationAgent',
    'CitationAgentPlugin',
]

# Package metadata
__version__ = "2.0.0"
__author__ = "Deep Research Agents Team"
__description__ = "Modular citation management system for internal document tracking"

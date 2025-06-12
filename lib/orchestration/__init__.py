"""
Orchestration package for Lead Researcher Agent system.

This package provides modular components for managing research orchestration:
- ParallelResearchPlugin: Function calling plugin for parallel research
- LeadResearcherAgent: Main orchestrator agent
- TemperatureManager: Temperature variation management
- ResearchExecutor: Concurrent research execution logic
"""

# Import main classes for easy access
from .lead_researcher_agent import LeadResearcherAgent
from .parallel_research_plugin import ParallelResearchPlugin
from .research_executor import ResearchExecutor
from .temperature_manager import TemperatureManager

__all__ = [
    'LeadResearcherAgent',
    'ParallelResearchPlugin',
    'TemperatureManager',
    'ResearchExecutor'
]

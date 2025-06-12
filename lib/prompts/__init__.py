"""
Modular prompts system for the research agent.

This package provides organized prompts for different agent types.
Please import prompts directly from their specific modules:

  from lib.prompts.agents.manager import MANAGER_PROMPT
  from lib.prompts.agents.citation import CITATION_AGENT_PROMPT
  from lib.prompts.common import COMMON_SEARCH_FUNCTIONS

This approach provides better clarity about where prompts are defined
and enables more efficient imports.
"""

# This module intentionally does not re-export prompts to encourage
# direct imports from specific modules.

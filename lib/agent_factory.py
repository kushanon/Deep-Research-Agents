"""
Agent factory for creating specialized research agents.
"""
import logging
from typing import Any, Dict, Optional

from semantic_kernel.agents import ChatCompletionAgent

from .citation import CitationPlugin as CitationAgentPlugin
from .citation import CustomCitationAgent as CitationAgent
from .memory import (SharedMemoryPluginSK, SKMemoryPlugin,
                     create_azure_openai_text_embedding)
from .orchestration import LeadResearcherAgent
# Updated to use new modular prompts structure
from .prompts.agents.citation import CITATION_AGENT_PROMPT
from .prompts.agents.credibility_critic import CREDIBILITY_CRITIC_PROMPT
from .prompts.agents.reflection_critic import REFLECTION_CRITIC_PROMPT
from .prompts.agents.report_writer import REPORT_WRITER_PROMPT
from .prompts.agents.summarizer import SUMMARIZER_PROMPT
from .prompts.agents.translator import TRANSLATOR_PROMPT
from .search import ModularSearchPlugin
from .util import get_azure_openai_service

# Removed: from semantic_kernel.connectors.ai.open_ai import
# AzureChatPromptExecutionSettings

logger = logging.getLogger(__name__)

# ============================================================================
# Semantic Kernel Memory-based Agent Factory (Recommended)
# ============================================================================


async def create_agents_with_sk_memory(
    session_id: str,
    project_id: str = ""
) -> Dict[str, ChatCompletionAgent]:
    """
    Create research agents using Semantic Kernel memory system.
    This is the recommended approach for better maintainability.

    Args:
        session_id: Unique session identifier
        project_id: Project identifier (defaults to session_id)

    Returns:
        Dictionary of agent name -> ChatCompletionAgent
    """
    logger.info("Creating agents with Semantic Kernel memory system")

    # Get configuration for Azure OpenAI
    from .config import get_config
    config = get_config()

    # Create Azure OpenAI embedding generator
    embedding_generator = create_azure_openai_text_embedding(
        api_key=config.azure_openai_api_key,
        endpoint=config.azure_openai_endpoint,
        api_version=config.azure_openai_api_version,
        deployment_name=config.azure_openai_embedding_deployment,
        service_id="agents_embedding"
    )    # Create SK memory plugin
    sk_memory = SKMemoryPlugin(embedding_generator, session_id, project_id)
    await sk_memory.initialize()

    agents = {
        # Use ONLY LeadResearcherAgent to force internal orchestration
        "lead_researcher": LeadResearcherAgent(
            agent_count=3,
            # Enable SK memory for internal research agents - INTERNAL
            # DOCUMENTS ONLY
            plugins=[ModularSearchPlugin(), sk_memory]
        ),
        "credibility_critic": ChatCompletionAgent(
            name="CredibilityCriticAgent",
            description="Analyzes credibility and coverage of internal search results using advanced LLM analysis, with ability to search for additional supporting documents. Uses SK memory for analysis context.",
            instructions=CREDIBILITY_CRITIC_PROMPT,
            service=get_azure_openai_service(config.get_model_config("gpt41")),
            plugins=[ModularSearchPlugin(), sk_memory]
        ),

        "citation_agent": CitationAgent(
            name="CitationAgent",
            description="Processes research documents and reports to identify specific locations for citations, ensuring all claims are properly attributed to their sources. Uses SK memory for citation context.",
            instructions=CITATION_AGENT_PROMPT,
            service=get_azure_openai_service(config.get_model_config("gpt41")),
            plugins=[CitationAgentPlugin(), sk_memory]
        ),

        "summarizer": ChatCompletionAgent(
            name="SummarizerAgent",
            description="Synthesizes large volumes of search results into comprehensive, organized summaries. Uses SK memory for context and result storage.",
            instructions=SUMMARIZER_PROMPT,
            service=get_azure_openai_service(
                config.get_model_config("gpt41_mini")),
            plugins=[sk_memory]
        ),

        "report_writer": ChatCompletionAgent(
            name="ReportWriterAgent",
            description="Creates structured markdown reports with proper citations, hyperlinks, and visual content. Uses SK memory for context and component storage.",
            instructions=REPORT_WRITER_PROMPT,
            service=get_azure_openai_service(config.get_model_config("o3")),
            plugins=[sk_memory]
        ),

        "translator": ChatCompletionAgent(
            name="TranslatorAgent",
            description="Provides natural English-Japanese translation while preserving technical accuracy and formatting.",
            instructions=TRANSLATOR_PROMPT,
            service=get_azure_openai_service(config.get_model_config("gpt41"))
            # Note: Translator doesn't need memory capabilities
        ),

        "reflection_critic": ChatCompletionAgent(
            name="ReflectionCriticAgent",
            description="Evaluates report quality for coverage, coherence, citations and provides improvement feedback. Uses SK memory for evaluation context.",
            instructions=REFLECTION_CRITIC_PROMPT,
            service=get_azure_openai_service(config.get_model_config("o3")),
            plugins=[sk_memory]
        )
    }

    logger.info(f"Created {len(agents)} agents with SK memory support")
    logger.info(f"Agents: {list(agents.keys())}")
    for agent_name, agent in agents.items():
        logger.info(f"Agent {agent_name}: {agent.name} - {agent.description}")
    return agents

"""
Research Execution module for concurrent agent processing.

This module handles the parallel execution of research agents with
temperature variation and result synthesis.
"""

import asyncio
import logging
from typing import Any, List, Optional

from semantic_kernel.agents.chat_completion.chat_completion_agent import \
    ChatCompletionAgent
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole

from ..config import get_config
from ..prompts.agents.researcher import RESEARCHER_PROMPT
from ..search import ModularSearchPlugin
from ..util import get_azure_openai_service
from .temperature_manager import TemperatureManager

try:
    from ..config.project_config import get_project_config
except ImportError:
    get_project_config = None


class ResearchExecutor:
    """Handles concurrent execution of research agents."""

    def __init__(self, config_manager=None):
        """Initialize the research executor."""
        self.config = config_manager or get_config()
        self.logger = logging.getLogger(f"{__name__}.ResearchExecutor")

        # Load project config for templates and messages
        try:
            self.project_config = get_project_config() if get_project_config else None
        except Exception as e:
            self.logger.warning(f"Failed to load project configuration: {e}")
            self.project_config = None

    def _find_sk_memory_plugin(
            self,
            research_agents: List[Any],
            lead_agent: Any = None) -> Optional[Any]:
        """
        Find SK memory plugin from existing agents.

        Args:
            research_agents: List of research agents to search
            lead_agent: Lead agent to search (optional)

        Returns:
            SK memory plugin if found, None otherwise
        """
        # Search in existing research agents
        for agent in research_agents:
            if hasattr(
                    agent,
                    'kernel') and agent.kernel and hasattr(
                    agent.kernel,
                    'plugins'):
                for plugin in agent.kernel.plugins.values():
                    if hasattr(
                            plugin, 'session_id') and hasattr(
                            plugin, 'store_memory'):
                        self.logger.info(
                            f"🔗 [ThreadPool] Found SK memory plugin from existing agent: {
                                type(plugin).__name__}")
                        return plugin

        # Search in lead agent if provided
        if lead_agent and hasattr(
                lead_agent,
                'kernel') and lead_agent.kernel and hasattr(
                lead_agent.kernel,
                'plugins'):
            for plugin in lead_agent.kernel.plugins.values():
                if hasattr(
                        plugin,
                        'session_id') and hasattr(
                        plugin,
                        'store_memory'):
                    self.logger.info(
                        f"🔗 [ThreadPool] Found SK memory plugin from LeadResearcherAgent: {
                            type(plugin).__name__}")
                    return plugin

        return None

    def _create_research_agent(
            self,
            config_dict: dict,
            sk_memory_plugin: Any = None) -> ChatCompletionAgent:
        """
        Create a single research agent with specified configuration.

        Args:
            config_dict: Configuration dictionary with temp, approach, agent_suffix
            sk_memory_plugin: SK memory plugin to attach (optional)

        Returns:
            Configured ChatCompletionAgent
        """
        temp = config_dict["temp"]
        approach = config_dict["approach"]
        agent_suffix = config_dict["agent_suffix"]

        # Create service with temperature setting
        if temp is not None:
            model_config = TemperatureManager.create_model_config_with_temperature(
                self.config.get_model_config("gpt41"), temp)
            service = get_azure_openai_service(model_config)
            instructions = TemperatureManager.get_temperature_instructions(
                temp, approach)
        else:
            service = get_azure_openai_service(
                self.config.get_model_config("gpt41"))
            instructions = RESEARCHER_PROMPT

        # Setup plugins
        plugins = [ModularSearchPlugin()]
        if sk_memory_plugin:
            plugins.append(sk_memory_plugin)

        agent_name = TemperatureManager.get_agent_name(agent_suffix)
        description = TemperatureManager.get_agent_description(approach, temp)

        agent = ChatCompletionAgent(
            name=agent_name,
            description=description,
            instructions=instructions,
            service=service,
            plugins=plugins
        )

        if temp is not None:
            self.logger.info(f"🌡️ [TEMP {temp}] Created {agent_name}")
        else:
            self.logger.info(
                f"🔬 [ThreadPool] Created additional agent: {agent_name}")

        return agent

    def _prepare_agents(
            self,
            research_agents: List[Any],
            use_temperature_variation: bool,
            sk_memory_plugin: Any = None,
            target_count: int = 3) -> List[Any]:
        """
        Prepare agents for concurrent execution.

        Args:
            research_agents: Current list of research agents
            use_temperature_variation: Whether to use temperature variation
            sk_memory_plugin: SK memory plugin to share
            target_count: Target number of agents

        Returns:
            List of agents ready for execution
        """
        temperature_configs = TemperatureManager.get_temperature_configs(
            use_temperature_variation)

        if use_temperature_variation:
            # Create new temperature-varied agents
            if len(research_agents) != target_count:
                self.logger.info(f"🌡️ [TEMP VARIATION] Creating {
                                 target_count} temperature-varied agents")
                research_agents.clear()

                for i in range(target_count):
                    agent = self._create_research_agent(
                        temperature_configs[i], sk_memory_plugin)
                    research_agents.append(agent)

            return research_agents[:target_count]
        else:
            # Reuse existing standard agents when possible
            if len(research_agents) >= target_count:
                self.logger.info(f"🔬 [ThreadPool] Reusing {
                                 target_count} existing agents for faster execution")
                return research_agents[:target_count]
            else:
                # Create additional standard agents as needed
                for i in range(len(research_agents), target_count):
                    agent = self._create_research_agent(
                        temperature_configs[i], sk_memory_plugin)
                    research_agents.append(agent)

                return research_agents[:target_count]

    async def _run_single_agent(self, agent: Any, user_input: str) -> List[Any]:
        """
        Run a single agent and return its responses.

        Args:
            agent: Research agent to run
            user_input: User query

        Returns:
            List of response items
        """
        message = ChatMessageContent(role=AuthorRole.USER, content=user_input)
        responses = []

        try:
            self.logger.info(f"🔬 [ThreadPool] Starting {agent.name}...")
            async for response_item in agent.invoke_stream(
                [message],
                on_intermediate_message=None  # Disable callback to avoid type errors
            ):
                responses.append(response_item)
            self.logger.info(
                f"✅ [{
                    agent.name}] Completed with {
                    len(responses)} responses")
        except Exception as e:
            self.logger.error(
                f"❌ [ThreadPool] Error in {
                    agent.name}: {e}",
                exc_info=True)
            responses.append(f"ERROR: {str(e)}")

        return responses

    def _synthesize_results(
            self,
            results: List[Any],
            temperature_configs: List[dict],
            user_input: str,
            use_temperature_variation: bool) -> str:
        """
        Synthesize results from multiple agents into a comprehensive report.

        Args:
            results: Results from concurrent agent execution
            temperature_configs: Temperature configurations used
            user_input: Original user query
            use_temperature_variation: Whether temperature variation was used

        Returns:
            Synthesized research report
        """
        synthesized_parts = []

        if use_temperature_variation:
            synthesized_parts.append(
                "# 🌡️ Temperature Variation Parallel Research Results - Lead Researcher Analysis")
            synthesized_parts.append("## Research Query")
            synthesized_parts.append(f"{user_input}\n")
            synthesized_parts.append("## Temperature Variation Approach")
            synthesized_parts.append(
                "Executed diverse analytical approaches from conservative to creative using different temperature settings.\n")
        else:
            synthesized_parts.append(
                "# Comprehensive Research Results - Lead Researcher Analysis (ThreadPool Parallel)")
            synthesized_parts.append("## Executive Summary")
            synthesized_parts.append(
                "Integrated results from parallel investigation by 3 research agents.\n")

        # Process each agent's results
        for i, agent_result in enumerate(results, 1):
            if isinstance(agent_result, Exception):
                temp_config = temperature_configs[i - 1]
                if use_temperature_variation:
                    synthesized_parts.append(f"### 🌡️ Temperature {
                                             temp_config['temp']} - {temp_config['approach']}")
                    synthesized_parts.append(f"**Error**: {str(agent_result)}")
                else:
                    synthesized_parts.append(
                        f"## Research Perspective {i} - RESEARCHER{i}")
                    synthesized_parts.append(f"Error: {str(agent_result)}")
                continue

            if agent_result:
                last = agent_result[-1]
                content = getattr(last, 'content', None)
                if content is None and hasattr(
                        last, 'message') and hasattr(
                        last.message, 'content'):
                    content = last.message.content

                temp_config = temperature_configs[i - 1]
                if use_temperature_variation:
                    synthesized_parts.append(f"### 🌡️ Temperature {
                                             temp_config['temp']} - {temp_config['approach']}")
                    synthesized_parts.append(
                        f"**Approach**: {temp_config['approach']}")
                    synthesized_parts.append(f"**Research Results**:")
                    synthesized_parts.append(str(content))
                    synthesized_parts.append("")
                else:
                    synthesized_parts.append(
                        f"## Research Perspective {i} - RESEARCHER{i}")
                    synthesized_parts.append(str(content))
            else:
                temp_config = temperature_configs[i - 1]
                if use_temperature_variation:
                    synthesized_parts.append(f"### 🌡️ Temperature {
                                             temp_config['temp']} - {temp_config['approach']}")
                    synthesized_parts.append(
                        f"**Approach**: {temp_config['approach']}")
                    synthesized_parts.append("**No Response**")
                else:
                    synthesized_parts.append(
                        f"## Research Perspective {i} - RESEARCHER{i}")
                    synthesized_parts.append("No Response")

        # Add conclusion
        if use_temperature_variation:
            synthesized_parts.append(
                "\n## 🎯 Temperature Variation Integrated Analysis")
            synthesized_parts.append(
                "Integrating the results from diverse analytical approaches using different temperature settings to provide comprehensive analysis and recommendations.")
            synthesized_parts.append("")
            synthesized_parts.append("### Research Quality Indicators")

            # Get quality indicators from project config if available
            if self.project_config:
                quality_indicators = self.project_config.get_quality_indicators(
                    "temperature_variation")
                for indicator in quality_indicators:
                    formatted_indicator = indicator.format(
                        agent_count=len(temperature_configs))
                    synthesized_parts.append(f"- {formatted_indicator}")
            else:
                # Fallback to default indicators
                synthesized_parts.append(
                    "- ✅ Temperature Variation: 0.2(conservative) → 0.6(balanced) → 0.9(creative)")
                synthesized_parts.append(
                    f"- ✅ Parallel Agents: {len(temperature_configs)} agents concurrent execution")
                synthesized_parts.append(
                    "- ✅ Internal Document Search: ModularSearchPlugin integration")
                synthesized_parts.append(
                    "- ✅ Diverse Approaches: Optimized analysis breadth and depth")
                synthesized_parts.append(
                    "- ✅ Source Citations: Complete citation information for all results")
        else:
            synthesized_parts.append(
                "\n## Integrated Analysis and Recommendations")
            synthesized_parts.append(
                "Integrating the multiple research results above to provide comprehensive analysis and recommendations.")

        return "\n".join(synthesized_parts)

    def _get_error_message(
            self,
            user_input: str,
            error: str,
            use_temperature_variation: bool) -> str:
        """Get formatted error message using project config templates if available."""
        if self.project_config:
            if use_temperature_variation:
                template = self.project_config.get_error_template(
                    "temperature_variation")
                if template:
                    return template.format(
                        user_input=user_input, error_message=error)
            else:
                template = self.project_config.get_error_template(
                    "standard_parallel")
                if template:
                    return template.format(
                        user_input=user_input, error_message=error)

        # Fallback to hardcoded templates
        if use_temperature_variation:
            return f"""# 🌡️ Temperature Variation Parallel Research - Error

## Research Query
{user_input}

## Error
An error occurred during temperature variation parallel research agent execution: {
                error}"""
        else:
            return f"""# Lead Researcher Analysis (ThreadPool Parallel)

## Research Query
{user_input}

## Error
An error occurred during parallel research agent execution: {error}"""

    async def execute_concurrent_research(self, research_agents: List[Any], user_input: str,
                                          use_temperature_variation: bool = False,
                                          lead_agent: Any = None) -> str:
        """
        Execute concurrent research using multiple agents.

        Args:
            research_agents: List of research agents (will be modified)
            user_input: The research query
            use_temperature_variation: If True, uses different temperature settings
            lead_agent: Lead agent for finding SK memory plugin

        Returns:
            Synthesized research results as string
        """
        self.logger.info(f"🔬 [ThreadPool] Starting concurrent research for query: {
                         user_input[:100]}...")

        temperature_configs = TemperatureManager.get_temperature_configs(
            use_temperature_variation)

        if use_temperature_variation:
            self.logger.info(
                f"🌡️ [TEMP VARIATION] Using {
                    len(temperature_configs)} temperature variations")
        else:
            self.logger.info(
                f"🔬 [ThreadPool] Using standard temperature settings for {
                    len(temperature_configs)} agents")

        # Find SK memory plugin
        sk_memory_plugin = self._find_sk_memory_plugin(
            research_agents, lead_agent)

        # Prepare agents for execution
        agents_to_use = self._prepare_agents(
            research_agents, use_temperature_variation, sk_memory_plugin)

        self.logger.info(
            f"🔬 [ThreadPool] Using {
                len(agents_to_use)} agents for parallel execution. (SK memory plugin shared: {
                bool(sk_memory_plugin)})")

        try:
            # Execute agents concurrently
            results = await asyncio.gather(
                *(self._run_single_agent(agent, user_input) for agent in agents_to_use),
                return_exceptions=True
            )

            self.logger.info(
                f"🔬 [ThreadPool] All agents completed. Synthesizing results...")

            # Synthesize results
            return self._synthesize_results(
                results,
                temperature_configs,
                user_input,
                use_temperature_variation)

        except Exception as e:
            self.logger.error(
                f"❌ [ThreadPool] Error in concurrent research execution: {
                    str(e)}", exc_info=True)
            return self._get_error_message(
                user_input, str(e), use_temperature_variation)

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
from ..utils.logging_config import get_research_executor_logger
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
        self.logger = get_research_executor_logger()

        # Load project config for templates and messages
        try:
            self.project_config = get_project_config() if get_project_config else None
        except Exception as e:
            self.logger.warning(f"Failed to load project configuration: {e}")
            self.project_config = None
        
        # Function calling analysis settings
        self.function_calling_analysis_enabled = True
        self.detailed_function_logging = True
        self.content_richness_scoring = True

    def _create_research_agent(
            self,
            config_dict: dict,
            memory_plugin: Any = None) -> ChatCompletionAgent:
        """
        Create a single research agent with specified configuration.

        Args:
            config_dict: Configuration dictionary with temp, approach, agent_suffix
            memory_plugin: Memory plugin to attach (required for memory functionality)

        Returns:
            Configured ChatCompletionAgent with memory capabilities
        """
        temp = config_dict["temp"]
        approach = config_dict["approach"]
        agent_suffix = config_dict["agent_suffix"]

        # Create service
        service = get_azure_openai_service(
            self.config.get_model_config("gpt41"))
        
        # Get instructions based on temperature setting
        if temp is not None:
            instructions = TemperatureManager.get_temperature_instructions(
                temp, approach)
            self.logger.debug(f"🌡️ [TEMP {temp}] Created {agent_suffix} with temperature-specific instructions")
        else:
            instructions = RESEARCHER_PROMPT

        # Setup plugins - always include memory plugin for knowledge preservation
        plugins = [ModularSearchPlugin()]
        if memory_plugin:
            plugins.append(memory_plugin)
            self.logger.debug(f"💾 [MEMORY] Added memory plugin to {agent_suffix} for knowledge preservation")
        else:
            self.logger.debug(f"⚠️ [MEMORY] No memory plugin available for {agent_suffix} - important findings may not be preserved")

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
            self.logger.debug(f"🌡️ [TEMP {temp}] Created {agent_name} with {len(plugins)} plugins (including memory)")
        else:
            self.logger.debug(f"🔬 [ThreadPool] Created additional agent: {agent_name} with {len(plugins)} plugins")

        return agent

    def _prepare_agents(
            self,
            research_agents: List[Any],
            use_temperature_variation: bool,
            memory_plugin: Any = None,
            target_count: int = 3) -> List[Any]:
        """
        Prepare agents for concurrent execution with memory capabilities.

        Args:
            research_agents: Current list of research agents
            use_temperature_variation: Whether to use temperature variation
            memory_plugin: Memory plugin to share across all agents
            target_count: Target number of agents

        Returns:
            List of agents ready for execution with memory capabilities
        """
        temperature_configs = TemperatureManager.get_temperature_configs(
            use_temperature_variation)

        if memory_plugin:
            self.logger.debug(f"💾 [MEMORY] Preparing {target_count} agents with shared memory capabilities")
        else:
            self.logger.debug(f"⚠️ [MEMORY] Preparing {target_count} agents without memory capabilities - important findings may not be preserved")

        if use_temperature_variation:
            # Create new temperature-varied agents with memory
            if len(research_agents) != target_count:
                self.logger.debug(f"🌡️ [TEMP VARIATION] Creating {target_count} temperature-varied agents with memory")
                research_agents.clear()

                for i in range(target_count):
                    agent = self._create_research_agent(
                        temperature_configs[i], memory_plugin)
                    research_agents.append(agent)

            return research_agents[:target_count]
        else:
            # Reuse existing standard agents when possible, ensure they have memory
            if len(research_agents) >= target_count:
                self.logger.debug(f"🔬 [ThreadPool] Reusing {target_count} existing agents")
                
                # Verify existing agents have memory plugin if available
                if memory_plugin:
                    for i, agent in enumerate(research_agents[:target_count]):
                        if not self._has_memory_plugin(agent):
                            self.logger.debug(f"⚠️ [MEMORY] Agent {i+1} missing memory plugin - recreating with memory")
                            # Recreate agent with memory
                            new_agent = self._create_research_agent(temperature_configs[i], memory_plugin)
                            research_agents[i] = new_agent
                
                return research_agents[:target_count]
            else:
                # Create additional standard agents as needed with memory
                self.logger.debug(f"🔬 [ThreadPool] Creating {target_count - len(research_agents)} additional agents with memory")
                for i in range(len(research_agents), target_count):
                    agent = self._create_research_agent(
                        temperature_configs[i], memory_plugin)
                    research_agents.append(agent)

                return research_agents[:target_count]

    async def _run_single_agent_with_thread(
        self,
        agent: Any,
        user_input: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        Run a single research agent using thread-based approach.
        This method provides better tool call result extraction.
        """
        try:
            self.logger.info(f"🔬 [ThreadBased] Starting {agent.name}...")
            kernel_arguments = self._build_kernel_arguments(agent, temperature)
            response = await self._get_agent_response(agent, user_input, kernel_arguments)
            final_content, message_count = await self._process_agent_response(agent, response)
            self.logger.info(f"✅ [ThreadBased] {agent.name} completed with {message_count} messages, final content: {len(final_content)} chars")
            if final_content:
                self.logger.debug(f"🔍 [ThreadBased] {agent.name} Final content preview: {final_content[:200]}...")
            else:
                self.logger.warning(f"⚠️ [ThreadBased] {agent.name} No content collected")
            return final_content if final_content else f"No content generated by {agent.name}"
        except Exception as e:
            self.logger.error(f"❌ [ThreadBased] Error in {agent.name}: {e}", exc_info=True)
            return f"ERROR in {agent.name}: {str(e)}"

    def _build_kernel_arguments(self, agent: Any, temperature: Optional[float]) -> Optional[Any]:
        """
        Build kernel arguments for agent execution, handling temperature and settings.
        """
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
        from semantic_kernel.functions.kernel_arguments import KernelArguments
        from semantic_kernel.connectors.ai import FunctionChoiceBehavior
        kernel_arguments = None
        if temperature is not None:
            self.logger.debug(f"🌡️ [TEMPERATURE] Setting temperature {temperature} for {agent.name}")
            service_id = "agent"
            if hasattr(agent, 'kernel') and agent.kernel:
                for service_key in agent.kernel.services.keys():
                    service_id = service_key
                    break
            settings = OpenAIChatPromptExecutionSettings(
                service_id=service_id,
                temperature=temperature,
                function_choice_behavior=FunctionChoiceBehavior.Auto()
            )
            kernel_arguments = KernelArguments(settings=settings)
            self.logger.debug(f"🌡️ [TEMPERATURE] Created kernel arguments with temperature {temperature}")
        else:
            if hasattr(agent, 'kernel') and agent.kernel:
                try:
                    service_id = "agent"
                    for service_key in agent.kernel.services.keys():
                        service_id = service_key
                        break
                    settings = agent.kernel.get_prompt_execution_settings_from_service_id(service_id=service_id)
                    if settings:
                        settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
                        kernel_arguments = KernelArguments(settings=settings)
                        self.logger.debug(f"🔧 [SETTINGS] Using kernel execution settings for {agent.name}")
                except Exception as settings_error:
                    self.logger.debug(f"⚠️ [SETTINGS] Could not get execution settings: {settings_error}")
        return kernel_arguments

    async def _get_agent_response(self, agent: Any, user_input: str, kernel_arguments: Optional[Any]) -> Any:
        """
        Get response from agent using kernel arguments.
        """
        thread = None
        if kernel_arguments:
            response = await agent.get_response(messages=user_input, thread=thread, arguments=kernel_arguments)
        else:
            response = await agent.get_response(messages=user_input, thread=thread)
        return response

    async def _process_agent_response(self, agent: Any, response: Any) -> tuple[str, int]:
        """
        Process the agent response, extracting messages, tool calls, and results.
        Returns final content and message count.
        """
        complete_content_parts = []
        tool_calls = []
        tool_results = []
        message_count = 0
        thread = getattr(response, 'thread', None)
        if thread:
            try:
                async for message in thread.get_messages():
                    message_count += 1
                    if hasattr(message, 'content') and message.content:
                        complete_content_parts.append(str(message.content))
                    if hasattr(message, 'items') and message.items:
                        for item in message.items:
                            if hasattr(item, 'function_name') and hasattr(item, 'arguments'):
                                tool_call_info = {
                                    'function_name': item.function_name,
                                    'arguments': item.arguments,
                                    'id': getattr(item, 'id', None),
                                    'call_id': getattr(item, 'call_id', None)
                                }
                                tool_calls.append(tool_call_info)
                                self.logger.debug(f"🔧 [TOOL CALL] {agent.name} called: {item.function_name}")
                                self.logger.debug(f"🔧 [TOOL CALL] Arguments: {str(item.arguments)[:200]}...")
                            elif hasattr(item, 'result') and hasattr(item, 'function_name'):
                                tool_result_info = {
                                    'function_name': item.function_name,
                                    'result': item.result,
                                    'id': getattr(item, 'id', None),
                                    'call_id': getattr(item, 'call_id', None)
                                }
                                tool_results.append(tool_result_info)
                                self.logger.debug(f"🔧 [TOOL RESULT] {agent.name} received result from: {item.function_name}")
                                self.logger.debug(f"🔧 [TOOL RESULT] Result preview: {str(item.result)[:200]}...")
                                complete_content_parts.append(f"\n[Function Result from {item.function_name}]\n{str(item.result)}\n")
                if tool_calls:
                    tool_info = f"\n[Tool Calls Executed: {len(tool_calls)} functions]\n"
                    for i, tool_call in enumerate(tool_calls):
                        tool_info += f"- Function: {tool_call['function_name']}\n"
                        tool_info += f"  Arguments: {str(tool_call['arguments'])[:100]}...\n"
                        if tool_call['id']:
                            tool_info += f"  ID: {tool_call['id']}\n"
                    complete_content_parts.append(tool_info)
                if tool_results:
                    tool_result_info = f"\n[Tool Results: {len(tool_results)} results received]\n"
                    for i, tool_result in enumerate(tool_results):
                        tool_result_info += f"- Function: {tool_result['function_name']}\n"
                        tool_result_info += f"  Result length: {len(str(tool_result['result']))} chars\n"
                        if tool_result['id']:
                            tool_result_info += f"  ID: {tool_result['id']}\n"
                    complete_content_parts.append(tool_result_info)
                if thread and hasattr(thread, 'delete'):
                    try:
                        await thread.delete()
                    except Exception as cleanup_error:
                        self.logger.debug(f"🧵 [THREAD] Error cleaning up thread: {cleanup_error}")
            except Exception as get_messages_error:
                self.logger.error(f"🧵 [THREAD] Error getting messages: {get_messages_error}", exc_info=True)
                if hasattr(response, 'content') and response.content:
                    complete_content_parts.append(str(response.content))
        elif hasattr(response, 'content') and response.content:
            complete_content_parts = [str(response.content)]
            self.logger.debug(f"🔬 [ThreadBased] Using direct response content for {agent.name}")
        else:
            complete_content_parts = [f"No content generated by {agent.name}"]
            self.logger.warning(f"⚠️ [ThreadBased] No content found in response for {agent.name}")
        final_content = "".join(complete_content_parts)
        return final_content, message_count

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

            # agent_result is now a string (final content)
            temp_config = temperature_configs[i - 1]
            if use_temperature_variation:
                self.logger.debug(f"🌡️ Processing temperature {temp_config['temp']} result: {len(str(agent_result)) if agent_result else 0} chars")
                synthesized_parts.append(f"### 🌡️ Temperature {
                                         temp_config['temp']} - {temp_config['approach']}")
                synthesized_parts.append(
                    f"**Approach**: {temp_config['approach']}")
                synthesized_parts.append(f"**Research Results**:")
                synthesized_parts.append(str(agent_result) if agent_result else "No content generated")
                synthesized_parts.append("")
            else:
                self.logger.debug(f"📊 Processing standard agent {i} result: {len(str(agent_result)) if agent_result else 0} chars")
                synthesized_parts.append(
                    f"## Research Perspective {i} - RESEARCHER{i}")
                synthesized_parts.append(str(agent_result) if agent_result else "No content generated")

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
                                          lead_agent: Any = None,
                                          use_thread_based: bool = True, memory_plugin = None) -> str:
        """
        Execute concurrent research using multiple agents.

        Args:
            research_agents: List of research agents (will be modified)
            user_input: The research query
            use_temperature_variation: If True, uses different temperature settings
            lead_agent: Lead agent for finding memory plugin
            use_thread_based: Whether to use thread-based approach for better tool call handling

        Returns:
            Synthesized research results as string
        """
        self.logger.info(f"🔬 [ThreadPool] Starting concurrent research for query: {
                         user_input[:100]}...")
        
        execution_method = "Thread-based" if use_thread_based else "Stream-based"
        self.logger.info(f"🔬 [ThreadPool] Using {execution_method} execution approach")

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
        
        if memory_plugin:
            self.logger.info(f"💾 [MEMORY] Found memory plugin - research agents will have knowledge preservation capabilities")
        else:
            self.logger.debug(f"⚠️ [MEMORY] No memory plugin found - research agents will not be able to preserve important findings")

        # Prepare agents for execution
        agents_to_use = self._prepare_agents(
            research_agents, use_temperature_variation, memory_plugin)

        # Verify all agents have memory capabilities
        agents_with_memory = self._count_agents_with_memory(agents_to_use)

        self.logger.info(f"🔬 [ThreadPool] Using {len(agents_to_use)} agents for parallel execution")
        self.logger.info(f"💾 [MEMORY] {agents_with_memory}/{len(agents_to_use)} agents have memory capabilities")
        
        if agents_with_memory < len(agents_to_use):
            self.logger.debug(f"⚠️ [MEMORY] {len(agents_to_use) - agents_with_memory} agents lack memory capabilities - important findings may not be preserved")


        try:
            # Always use thread-based execution only
            if use_temperature_variation:
                tasks = [self._run_single_agent_with_thread(agent, user_input, temperature_configs[i]["temp"]) for i, agent in enumerate(agents_to_use)]
            else:
                tasks = [self._run_single_agent_with_thread(agent, user_input) for agent in agents_to_use]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            self.logger.info("🔬 [ThreadPool] All agents completed using Thread-based. Synthesizing results...")

            synthesized_result = self._synthesize_results(
                results,
                temperature_configs,
                user_input,
                use_temperature_variation)
            self.logger.debug(f"synthesized_result: {synthesized_result[:2000]}...")
            return synthesized_result

        except Exception as e:
            self.logger.error(
                f"❌ [ThreadPool] Error in concurrent research execution: {str(e)}", exc_info=True)
            return self._get_error_message(
                user_input, str(e), use_temperature_variation)

    def _validate_temperature_settings(self, agents_to_use: List[Any], temperature_configs: List[dict]):
        """
        Validate that temperature settings are properly configured for agents.
        
        Args:
            agents_to_use: List of agents to validate
            temperature_configs: Temperature configurations
        """
        self.logger.debug("🔍 [TEMP VALIDATION] Validating temperature settings...")
        
        for i, (agent, config) in enumerate(zip(agents_to_use, temperature_configs)):
            temp = config.get("temp")
            approach = config.get("approach", "unknown")
            
            if temp is not None:
                self.logger.debug(f"🌡️ [TEMP VALIDATION] Agent {i+1} ({agent.name}): temperature={temp}, approach={approach}")
                
                # Check if agent has proper service configuration
                if hasattr(agent, 'service') and agent.service:
                    self.logger.debug(f"🔧 [TEMP VALIDATION] Agent {i+1} service type: {type(agent.service).__name__}")
                else:
                    self.logger.debug(f"⚠️ [TEMP VALIDATION] Agent {i+1} missing service configuration")
            else:
                self.logger.debug(f"🔬 [TEMP VALIDATION] Agent {i+1} ({agent.name}): standard temperature (no specific setting)")

    def _has_memory_plugin(self, agent: Any) -> bool:
        """
        Check if an agent has a memory plugin.
        
        Args:
            agent: The agent to check
            
        Returns:
            True if the agent has a memory plugin, False otherwise
        """
        if not hasattr(agent, 'kernel') or not agent.kernel.plugins:
            return False
            
        for plugin_name in agent.kernel.plugins.keys():
            if plugin_name in ["MemoryPlugin", "Memory"] or "memory" in plugin_name.lower():
                return True
        return False

    def _get_agent_plugin_info(self, agent: Any) -> dict:
        """
        Get plugin information for an agent.
        
        Args:
            agent: The agent to check
            
        Returns:
            Dict with plugin information including names and memory status
        """
        if hasattr(agent, 'kernel') and agent.kernel.plugins:
            plugin_names = list(agent.kernel.plugins.keys())
            has_memory = self._has_memory_plugin(agent)
            return {
                'plugin_names': plugin_names,
                'has_memory': has_memory,
                'plugin_count': len(plugin_names)
            }
        else:
            return {
                'plugin_names': [],
                'has_memory': False,
                'plugin_count': 0
            }

    def _count_agents_with_memory(self, agents: List[Any]) -> int:
        """
        Count how many agents have memory plugins.
        
        Args:
            agents: List of agents to check
            
        Returns:
            Number of agents with memory capabilities
        """
        count = 0
        for agent in agents:
            plugin_info = self._get_agent_plugin_info(agent)
            self.logger.debug(f"agent_name: {agent.name}, plugins: {plugin_info['plugin_names']}")
            
            if plugin_info['has_memory']:
                count += 1
                # Find the specific memory plugin name for logging
                memory_plugin_name = next(
                    (name for name in plugin_info['plugin_names'] 
                     if name in ["MemoryPlugin", "Memory"] or "memory" in name.lower()), 
                    "unknown"
                )
                self.logger.debug(f"🔍 [MEMORY] Found memory plugin '{memory_plugin_name}' in {agent.name}")
                self.logger.debug(f"💾 [MEMORY] Agent {agent.name} has memory capabilities")
            else:
                self.logger.debug(f"⚠️ [MEMORY] Agent {agent.name} lacks memory capabilities")
                
        return count
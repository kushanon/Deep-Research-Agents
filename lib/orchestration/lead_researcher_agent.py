"""
Lead Researcher Agent implementation.

This module provides the main LeadResearcherAgent class that coordinates
multiple internal research agents using concurrent orchestration.
"""

import logging
import sys
from typing import Any, AsyncIterable, Awaitable, Callable, List, Optional

from pydantic import PrivateAttr
from semantic_kernel.agents.agent import Agent, AgentResponseItem, AgentThread
from semantic_kernel.agents.chat_completion.chat_completion_agent import (
    ChatCompletionAgent, ChatHistoryAgentThread)
from semantic_kernel.agents.runtime.core.core_runtime import CoreRuntime
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.streaming_chat_message_content import \
    StreamingChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.kernel import Kernel
from semantic_kernel.utils.telemetry.agent_diagnostics.decorators import \
    trace_agent_invocation

if sys.version_info >= (3, 12):
    from typing import override  # pragma: no cover
else:
    from typing_extensions import override  # pragma: no cover

from ..config import get_config
from ..prompts.agents.researcher import (LEAD_RESEARCHER_PROMPT,
                                         RESEARCHER_PROMPT)
from ..search import ModularSearchPlugin
from ..util import get_azure_openai_service
from .parallel_research_plugin import ParallelResearchPlugin
from .research_executor import ResearchExecutor


class LeadResearcherAgent(ChatCompletionAgent):
    """
    A Lead Researcher agent that internally manages multiple research agents using ConcurrentOrchestration.
    This agent can be managed by MagenticOrchestrator as a single ChatCompletionAgent.
    """

    # Use PrivateAttr for all custom attributes to avoid Pydantic conflicts
    _research_agents: List[Agent] = PrivateAttr(default_factory=list)
    _runtime: Optional[CoreRuntime] = PrivateAttr(default=None)
    _kernel: Optional[Kernel] = PrivateAttr(default=None)
    _instruction_template: Optional[str] = PrivateAttr(default=None)
    _research_executor: ResearchExecutor = PrivateAttr(
        default_factory=ResearchExecutor)

    def __init__(
            self,
            agent_count: int = 1,
            kernel: Kernel = None,
            plugins=None,
            **kwargs):
        """
        Initialize the Lead Researcher as a ChatCompletionAgent with internal orchestration capabilities.

        Args:
            agent_count: Number of internal research agents to create
            kernel: Semantic Kernel instance (optional, for compatibility)
            plugins: List of plugins to add to this agent
            **kwargs: Additional arguments passed to parent class
        """
        logger = logging.getLogger(__name__)
        logger.info(f"🔬 Initializing LeadResearcherAgent with {
                    agent_count} internal research agents")
        # Extract plugins from kwargs if passed there
        if plugins is None:
            plugins = kwargs.pop('plugins', [])

        # Store instruction template for later use
        instruction_template = kwargs.pop('instructions', None)

        # Create parallel research plugin for this agent
        parallel_research_plugin = ParallelResearchPlugin(self)

        # Add the parallel research plugin to the plugins list
        plugins = list(plugins) if plugins else []
        plugins.append(parallel_research_plugin)

        logger.info(f"🔌 Added ParallelResearchPlugin to LeadResearcherAgent")

        # Initialize parent class
        super().__init__(
            name="LeadResearcherAgent",
            description="Advanced lead researcher that coordinates multiple internal research agents for comprehensive research tasks using ONLY internal document repositories. Features multi-round parallel execution and adaptive research capabilities for internal data analysis.",
            instructions=LEAD_RESEARCHER_PROMPT,
            service=get_azure_openai_service(
                get_config().get_model_config("gpt41")),
            plugins=plugins,
            **kwargs)

        # Set private attributes using object.__setattr__ to avoid Pydantic
        # validation
        object.__setattr__(self, '_instruction_template', instruction_template)
        object.__setattr__(self, '_kernel', kernel)
        object.__setattr__(self, '_runtime', None)
        object.__setattr__(self, '_research_executor', ResearchExecutor())

        # Extract memory plugin from this agent's plugins to share with
        # internal agents
        memory_plugin = self._find_memory_plugin(plugins)
        self._memory_plugin = memory_plugin
        # Create initial research agents
        research_agents = self._create_initial_research_agents(
            memory_plugin)
        object.__setattr__(self, '_research_agents', research_agents)

        logger.info("🔬 LeadResearcherAgent initialization completed")
        logger.info(
            f"🔌 Total plugins registered: {
                len(plugins)} (including ParallelResearchPlugin)")

    def _find_memory_plugin(self, plugins: List[Any]) -> Optional[Any]:
        """Find memory plugin from the provided plugins list."""
        logger = logging.getLogger(__name__)
        for plugin in plugins:
            if plugin.__class__.__name__ == "MemoryPlugin" or "memory" in plugin.__class__.__name__.lower():
                logger.info("🔗 Found MemoryPlugin in plugins")
                return plugin
        return None

    def _create_initial_research_agents(
            self, memory_plugin: Any) -> List[Agent]:
        """Create initial set of research agents."""
        logger = logging.getLogger(__name__)
        config = get_config()

        # Create 3 internal research agents at initialization
        research_agents = []
        logger.info(f"🤖 Creating 3 research agents at initialization...")

        # Enable detailed logging for Semantic Kernel
        # Reduce log noise: set semantic_kernel and openai loggers to WARNING
        semantic_kernel_logger = logging.getLogger("semantic_kernel")
        semantic_kernel_logger.setLevel(logging.WARNING)

        openai_logger = logging.getLogger("openai")
        openai_logger.setLevel(logging.WARNING)

        for i in range(3):
            logger.info(
                f"🤖 Creating research agent {
                    i +
                    1}: RESEARCHER{
                    i +
                    1}")
            # Create plugins list for each research agent
            internal_plugins = [ModularSearchPlugin()]
            if memory_plugin:
                internal_plugins.append(memory_plugin)
                logger.info(f"🔗 Added memory plugin to RESEARCHER{i + 1}")

            # Create instrumented service to log LLM calls
            service = get_azure_openai_service(
                config.get_model_config("gpt41"))
            agent = ChatCompletionAgent(
                name=f"RESEARCHER{
                    i +
                    1}",
                description="Performs comprehensive INTERNAL DOCUMENT SEARCH ONLY using Azure AI Search and returns structured JSON results from internal repositories. NO external source access.",
                instructions=RESEARCHER_PROMPT,
                service=service,
                plugins=internal_plugins)
            research_agents.append(agent)
            logger.info(
                f"✅ Successfully created research agent: {
                    agent.name} with {
                    len(internal_plugins)} plugins")

        logger.info(f"🤖 Total research agents created: {len(research_agents)}")
        return research_agents

    @property
    def kernel(self):
        """Expose the kernel used by this agent (for plugin/property access)."""
        return self._kernel

    @property
    def parallel_research_plugin(self) -> "ParallelResearchPlugin":
        """Access to parallel research plugin (robust to patching/mocking)."""
        plugin_type = type(self).ParallelResearchPlugin if hasattr(
            type(self), 'ParallelResearchPlugin') else ParallelResearchPlugin
        if self.kernel and hasattr(self.kernel, 'plugins'):
            for plugin in self.kernel.plugins.values():
                if isinstance(plugin, plugin_type):
                    return plugin
        return None

    @property
    def research_agents(self) -> List[Agent]:
        """Access to internal research agents (backward compatibility)."""
        return self._research_agents

    async def _execute_concurrent_research(self, user_input: str, use_temperature_variation: bool = False) -> str:
        """
        Execute concurrent research using the research executor.

        Args:
            user_input: The research query
            use_temperature_variation: If True, uses different temperature settings for analytical diversity
        Returns:
            Synthesized research results as string
        """
        return await self._research_executor.execute_concurrent_research(
            self._research_agents,
            user_input,
            use_temperature_variation,
            lead_agent=self,
            memory_plugin=self._memory_plugin,
        )

    @trace_agent_invocation
    @override
    async def invoke_stream(
        self,
        messages: str | ChatMessageContent | list[str | ChatMessageContent] | None = None,
        *,
        thread: AgentThread | None = None,
        on_intermediate_message: Callable[[StreamingChatMessageContent], Awaitable[None]] | None = None,
        arguments: KernelArguments | None = None,
        kernel: "Kernel | None" = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentResponseItem[StreamingChatMessageContent]]:
        """Override invoke_stream to disable problematic on_intermediate_message callback."""
        logger = logging.getLogger(__name__)
        logger.info("🎯 ===== LeadResearcherAgent.invoke_stream called =====")

        try:
            # Use the parent class's standard invoke_stream method but disable the callback
            # This avoids the type mismatch issues between ChatMessageContent
            # and StreamingChatMessageContent
            async for response_item in super().invoke_stream(
                messages=messages,
                thread=thread,
                on_intermediate_message=None,  # Disable callback to avoid type errors
                arguments=arguments,
                kernel=kernel,
                **kwargs
            ):
                yield response_item

        except Exception as e:
            logger.error(
                f"❌ CRITICAL ERROR in LeadResearcherAgent.invoke_stream: {
                    str(e)}", exc_info=True)

            # Return an error as streaming content
            error_content = f"Error in research execution: {str(e)}"
            error_stream_content = StreamingChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content=error_content,
                choice_index=0,
                name=self.name
            )

            response_thread = thread if thread is not None else ChatHistoryAgentThread()
            yield AgentResponseItem(message=error_stream_content, thread=response_thread)
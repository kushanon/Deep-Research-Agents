"""
Parallel Research Plugin for Lead Researcher Agent.

This plugin provides function calling capabilities for parallel research execution
with temperature variation and agent status monitoring.
"""

import logging

from semantic_kernel.functions import kernel_function


class ParallelResearchPlugin:
    """Plugin class for parallel research execution using Function calling."""

    def __init__(self, lead_researcher_agent):
        """Initialize with reference to LeadResearcherAgent."""
        self.lead_researcher_agent = lead_researcher_agent
        self.logger = logging.getLogger(f"{__name__}.ParallelResearchPlugin")

    @kernel_function(
        name="execute_parallel_research",
        description="Execute comprehensive parallel research using multiple internal research agents with different temperature settings for varied analytical approaches on INTERNAL DOCUMENTS ONLY. NO external source access."
    )
    async def execute_parallel_research(
        self,
        query: str = "research query"
    ) -> str:
        """
        Execute parallel research using multiple internal research agents with varied temperature settings.

        Args:
            query: Research query to be investigated by multiple agents with different analytical approaches

        Returns:
            Synthesized research results from parallel agent execution with comprehensive coverage
        """
        self.logger.info(f"🔬 [FUNCTION CALL] execute_parallel_research called with query: {
                         query[:100]}...")

        try:
            # Execute parallel research with temperature variation
            result = await self.lead_researcher_agent._execute_concurrent_research(query, use_temperature_variation=True)

            self.logger.info(
                f"✅ [FUNCTION CALL] Temperature-varied parallel research completed successfully")
            return result

        except Exception as e:
            self.logger.error(
                f"❌ [FUNCTION CALL] Error in execute_parallel_research: {
                    str(e)}", exc_info=True)
            return f"""# Function Call Parallel Research - Error

## Research Query
{query}

## Error
Error occurred during parallel research execution: {str(e)}

## Status
Error occurred during parallel research execution via function calling. Please fallback to direct execution mode.
"""

    @kernel_function(name="get_research_agents_status",
                     description="Get status information about available internal research agents")
    async def get_research_agents_status(self) -> str:
        """
        Get status information about internal research agents.

        Returns:
            Status information about available research agents
        """
        self.logger.info("📊 [FUNCTION CALL] get_research_agents_status called")

        try:
            agents = self.lead_researcher_agent._research_agents
            status_parts = []
            status_parts.append("# Internal Research Agents Status")
            status_parts.append(f"## Available Agents: {len(agents)}")
            status_parts.append("")

            for i, agent in enumerate(agents, 1):
                status_parts.append(f"### Agent {i}: {agent.name}")
                status_parts.append(f"- Type: {type(agent).__name__}")
                status_parts.append(f"- Description: {agent.description}")

                # Check plugins
                if hasattr(
                        agent,
                        'kernel') and agent.kernel and hasattr(
                        agent.kernel,
                        'plugins'):
                    plugin_names = [
                        plugin.name for plugin in agent.kernel.plugins.values()]
                    status_parts.append(f"- Plugins: {plugin_names}")
                else:
                    status_parts.append("- Plugins: None")
                status_parts.append("")

            status_parts.append("## Execution Mode")
            status_parts.append("- Parallel execution mode: enabled")
            status_parts.append("- Function calling integration: enabled")
            status_parts.append("- Dynamic execution: enabled")

            return "\n".join(status_parts)

        except Exception as e:
            self.logger.error(
                f"❌ [FUNCTION CALL] Error in get_research_agents_status: {
                    str(e)}", exc_info=True)
            return f"Error: An error occurred while retrieving research agent status: {str(e)}"

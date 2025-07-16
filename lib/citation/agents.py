"""
Custom Citation Agent implementations.
Handles streaming and agent-specific functionality.
"""
import logging
import sys
from typing import Any, AsyncIterable, Awaitable, Callable

from semantic_kernel.agents.agent import AgentResponseItem, AgentThread
from semantic_kernel.agents.chat_completion.chat_completion_agent import (
    ChatCompletionAgent, ChatHistoryAgentThread)
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

logger = logging.getLogger(__name__)


class CustomCitationAgent(ChatCompletionAgent):
    """
    Custom Citation Agent that handles streaming with disabled intermediate message callback.
    This fixes the TypeError: Expected message to be of type 'StreamingChatMessageContent',
    but got 'ChatMessageContent' instead error.
    """

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
        logger.info("🎯 ===== CustomCitationAgent.invoke_stream called =====")

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
                f"❌ CRITICAL ERROR in CustomCitationAgent.invoke_stream: {
                    str(e)}", exc_info=True)

            # Return an error as streaming content
            error_content = f"Error in citation agent execution: {str(e)}"
            error_stream_content = StreamingChatMessageContent(
                role=AuthorRole.ASSISTANT,
                content=error_content,
                choice_index=0,
                name=self.name
            )

            response_thread = thread if thread is not None else ChatHistoryAgentThread()
            yield AgentResponseItem(message=error_stream_content, thread=response_thread)

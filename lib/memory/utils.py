"""
Memory utilities for Azure OpenAI integration.
Provides factory functions and common utilities for memory operations.
"""
import logging

from openai import AsyncAzureOpenAI
from semantic_kernel.connectors.ai.open_ai import OpenAITextEmbedding

logger = logging.getLogger(__name__)


def create_azure_openai_text_embedding(
    api_key: str,
    endpoint: str,
    api_version: str,
    deployment_name: str,
    service_id: str = "azure_embedding"
) -> OpenAITextEmbedding:
    """
    Create OpenAI Text Embedding for Azure OpenAI.

    Args:
        api_key: Azure OpenAI API key
        endpoint: Azure OpenAI endpoint URL
        api_version: API version string
        deployment_name: Name of the embedding deployment
        service_id: Service identifier for the embedding service

    Returns:
        OpenAITextEmbedding: Configured embedding service
    """
    logger.debug(f"Creating Azure OpenAI text embedding service: {service_id}")
    logger.debug(f"Deployment: {deployment_name}, Endpoint: {endpoint}")

    azure_client = AsyncAzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version
    )

    embedding_service = OpenAITextEmbedding(
        ai_model_id=deployment_name,
        async_client=azure_client,
        service_id=service_id
    )

    logger.info(
        f"Successfully created Azure OpenAI embedding service: {service_id}")
    return embedding_service


def format_memory_results(results: list, max_display_length: int = 100) -> str:
    """
    Format memory search results for display.

    Args:
        results: List of content strings from memory search
        max_display_length: Maximum length for content preview

    Returns:
        str: Formatted results string
    """
    if not results:
        return "No relevant information found."

    formatted_results = []
    for i, content in enumerate(results, 1):
        # Truncate long content for readability
        display_content = content
        if len(content) > max_display_length:
            display_content = content[:max_display_length] + "..."

        formatted_results.append(f"[{i}] {display_content}")

    return "\n\n".join(formatted_results)


def create_memory_metadata(
    source: str,
    entry_type: str,
    session_id: str,
    project_id: str,
    additional_data: dict = None
) -> dict:
    """
    Create standardized metadata for memory entries.

    Args:
        source: Source of the memory (agent name, etc.)
        entry_type: Type of memory entry
        session_id: Session identifier
        project_id: Project identifier
        additional_data: Additional metadata fields

    Returns:
        dict: Metadata dictionary
    """
    from datetime import datetime

    metadata = {
        "source": source,
        "type": entry_type,
        "created": datetime.now().isoformat(),
        "session_id": session_id,
        "project_id": project_id
    }

    if additional_data:
        metadata.update(additional_data)

    return metadata

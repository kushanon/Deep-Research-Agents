"""
Utility functions for Deep Research Agent.
"""
import logging
from typing import Optional

from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatMessageContent


# Lazy import to avoid circular dependencies
def get_config():
    """Get configuration instance."""
    try:
        # Try to import from the parent config.py directly
        import os
        import sys
        parent_dir = os.path.dirname(__file__)
        config_path = os.path.join(parent_dir, 'config.py')

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "main_config", config_path)
        main_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_config)

        return main_config.Config()
    except Exception as e:
        logger.error(f"Failed to load Config: {e}")
        return None


logger = logging.getLogger(__name__)

# Keep track of the last message to avoid duplicates
_last_message = {"role": None, "content": None, "content_hash": None}


def dbg(msg: ChatMessageContent) -> None:
    """Observer callback – print every agent message to stdout with improved formatting."""
    role = msg.name or "(unknown)"
    content = msg.content or ""

    # Skip empty messages
    if not content.strip():
        return

    # Create a hash of the content to detect duplicates more reliably
    import hashlib
    content_hash = hashlib.md5(content.encode()).hexdigest()

    # Skip if this is the same message as the last one (prevent duplicates)
    if (_last_message["role"] == role and
            _last_message["content_hash"] == content_hash):
        return

    # Update last message tracking
    _last_message["role"] = role
    _last_message["content"] = content
    _last_message["content_hash"] = content_hash

    # Pretty print to console
    print(f"\n{'=' * 60}")
    print(f"🤖 **{role}**")
    print(f"{'=' * 60}")
    print(f"{content}")
    print(f"{'=' * 60}\n")


def get_azure_openai_service(
        deployment_name: str,
        max_tokens: Optional[int] = None) -> AzureChatCompletion:
    """    Create Azure OpenAI chat completion service with improved error handling and proper context limits.

    Args:
        deployment_name: Name of the Azure OpenAI deployment
        max_tokens: Maximum tokens for completion (optional, will be set in execution settings)

    Returns:
        AzureChatCompletion: Configured Azure OpenAI service

    Raises:
        ValueError: If required configuration is missing
        Exception: If service creation fails
    """
    try:
        # Get config instance
        config = get_config()

        # Handle both old Config class and new project config
        if hasattr(config, 'azure_openai_endpoint'):
            kwargs = {
                "deployment_name": deployment_name,
                "endpoint": config.azure_openai_endpoint,
                "api_key": config.azure_openai_api_key,
                "api_version": config.azure_openai_api_version,
            }
        else:
            # Handle new project config structure
            azure_config = getattr(config, 'azure', None)
            if azure_config:
                kwargs = {
                    "deployment_name": deployment_name,
                    "endpoint": azure_config.endpoint,
                    "api_key": azure_config.api_key,
                    "api_version": azure_config.api_version,
                }
            else:
                raise ValueError("Azure OpenAI configuration not found")

        # Don't set max_tokens in constructor - it goes in execution settings
        logger.info(f"Connecting to Azure OpenAI service: {deployment_name}")
        return AzureChatCompletion(**kwargs)

    except Exception as e:
        logger.error(f"Failed to create Azure OpenAI service: {e}")
        raise


def truncate_text(text: str, max_length: int = 1000) -> str:
    """
    Truncate text to specified length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        str: Truncated text
    """
    if text is None:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def validate_search_results(results: list) -> bool:
    """
    Validate search results structure.

    Args:
        results: List of search results

    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(results, list) or not results:
        return False

    required_fields = ["url", "title", "snippet"]
    for result in results:
        if not isinstance(result, dict):
            return False
        if not all(field in result for field in required_fields):
            return False

    return True

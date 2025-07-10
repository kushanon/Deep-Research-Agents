"""
Configuration management for Deep Research Agent.
"""
import logging
import os
import sys

from dotenv import load_dotenv

# Add the lib directory to Python path for imports
sys.path.append(os.path.dirname(__file__))

try:
    from config.project_config import ProjectConfig, get_project_config
except ImportError:
    # Fallback for when project_config is not available
    def get_project_config():
        return None
    ProjectConfig = None

# Load environment variables
load_dotenv()

# Configure logging with UTF-8 encoding support
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deep_research_agent.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Configuration error exception."""
    pass


class Config:
    """Configuration management class."""

    def __init__(self):
        """Initialize configuration."""
        # Load project-specific configuration
        try:
            self.project_config = get_project_config()
        except Exception as e:
            logger.warning(f"Failed to load project configuration: {e}")
            self.project_config = None

        # Azure OpenAI Configuration
        self.azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.azure_openai_api_version = os.getenv(
            "AZURE_OPENAI_API_VERSION", "2024-02-01")

        # Azure OpenAI Deployment Names
        self.azure_gpt41_deployment = os.getenv(
            "AZURE_GPT41_DEPLOYMENT", "gpt-41")
        self.azure_gpt41_mini_deployment = os.getenv(
            "AZURE_GPT41_MINI_DEPLOYMENT", "gpt-41-mini")
        self.azure_o3_deployment = os.getenv("AZURE_O3_DEPLOYMENT", "o3")
        self.azure_embedding_deployment = os.getenv(
            "AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
        self.azure_openai_embedding_deployment = os.getenv(
            "AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")

        # Azure AI Search Configuration
        self.azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
        self.azure_search_api_key = os.getenv("AZURE_SEARCH_API_KEY", "")
        self.azure_search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "")

        # Tavily API Configuration for web search
        self.tavily_api_key = os.getenv("TAVILY_API_KEY", "")
        self.tavily_max_results = int(os.getenv("TAVILY_MAX_RESULTS", "10"))
        self.tavily_max_retries = int(os.getenv("TAVILY_MAX_RETRIES", "3"))
        self.tavily_timeout = int(
            os.getenv(
                "TAVILY_TIMEOUT",
                "30"))  # Timeout in seconds

        # Document type indexes - only abstract reference
        self.document_indexes = {}
        if self.project_config:
            self.document_indexes = {
                dt.name: dt.index_name for dt in self.project_config.document_types}

        # Quality Thresholds - with project config integration
        if self.project_config:
            self.coverage_threshold = self.project_config.quality_thresholds.get(
                "coverage_threshold", 0.75)
            self.quality_threshold = self.project_config.quality_thresholds.get(
                "quality_threshold", 0.80)
            self.max_quality_iterations = self.project_config.quality_thresholds.get(
                "max_quality_iterations", 3)
        else:
            self.coverage_threshold = float(
                os.getenv("COVERAGE_THRESHOLD", "0.75"))
            self.quality_threshold = float(
                os.getenv("QUALITY_THRESHOLD", "0.80"))
            self.max_quality_iterations = int(
                os.getenv("MAX_QUALITY_ITERATIONS", "3"))

        # Logging Configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

        # Token limits
        self.max_completion_tokens = int(
            os.getenv("MAX_COMPLETION_TOKENS", "65536"))

        # Initialize logging
        self.setup_logging_level()

    # Properties for backward compatibility
    @property
    def AZURE_OPENAI_ENDPOINT(self) -> str:
        """Backward compatibility property."""
        return self.azure_openai_endpoint

    @property
    def AZURE_OPENAI_API_KEY(self) -> str:
        """Backward compatibility property."""
        return self.azure_openai_api_key

    @property
    def AZURE_SEARCH_ENDPOINT(self) -> str:
        """Backward compatibility property."""
        return self.azure_search_endpoint

    @property
    def AZURE_SEARCH_API_KEY(self) -> str:
        """Backward compatibility property."""
        return self.azure_search_api_key

    def validate(self) -> None:
        """Validate required configuration values."""
        required_configs = [
            ("AZURE_OPENAI_ENDPOINT", self.azure_openai_endpoint),
            ("AZURE_OPENAI_API_KEY", self.azure_openai_api_key),
            ("AZURE_SEARCH_ENDPOINT", self.azure_search_endpoint),
            ("AZURE_SEARCH_API_KEY", self.azure_search_api_key),
        ]

        missing_configs = [
            name for name, value in required_configs if not value
        ]

        if missing_configs:
            raise ConfigError(
                f"Missing required environment variables: {
                    ', '.join(missing_configs)}")

        # Validate numeric values
        try:
            assert 0 <= self.coverage_threshold <= 1.0, "Coverage threshold must be between 0 and 1"
            assert 0 <= self.quality_threshold <= 1.0, "Quality threshold must be between 0 and 1"
            assert self.max_quality_iterations > 0, "Max quality iterations must be positive"
            assert self.max_completion_tokens > 0, "Max completion tokens must be positive"
            assert self.tavily_max_results > 0, "Tavily max results must be positive"
            assert self.tavily_max_retries > 0, "Tavily max retries must be positive"
        except AssertionError as e:
            raise ConfigError(f"Invalid configuration value: {e}")

        # Warn if optional Tavily API key is missing
        if not self.tavily_api_key:
            logger.warning(
                "Tavily API key not configured - web search functionality will be disabled")

        logger.info("Configuration validation successful")

    def get_model_config(self, model_type: str) -> str:
        """Get model deployment name by type."""
        model_map = {
            "gpt41": self.azure_gpt41_deployment,
            "gpt41_mini": self.azure_gpt41_mini_deployment,
            "o3": self.azure_o3_deployment,
            "embedding": self.azure_embedding_deployment,
            "text_embedding": self.azure_openai_embedding_deployment,
        }

        if model_type not in model_map:
            raise ConfigError(f"Unknown model type: {model_type}")

        return model_map[model_type]

    def setup_logging_level(self):
        """Setup logging level based on configuration."""
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }

        level = level_map.get(self.log_level, logging.INFO)

        # Set root logger level
        logging.getLogger().setLevel(level)

        # Set specific logger levels based on debug mode
        if self.debug_mode or self.log_level == "DEBUG":
            # Enable debug for all components when in debug mode
            logging.getLogger("kernel").setLevel(logging.DEBUG)
            logging.getLogger(
                "in_process_runtime.events").setLevel(logging.DEBUG)
            logging.getLogger("in_process_runtime").setLevel(logging.DEBUG)
            logging.getLogger("httpx").setLevel(
                logging.INFO)  # Still limit httpx noise
            logging.getLogger("semantic_kernel").setLevel(logging.DEBUG)
            logging.getLogger("lib.sk_memory_plugin").setLevel(logging.DEBUG)
            logging.getLogger("lib.agent_factory").setLevel(logging.DEBUG)
            print(f"[CONFIG] Debug mode enabled - all loggers set to DEBUG level")
        else:
            # Standard logging levels for production
            logging.getLogger("kernel").setLevel(logging.INFO)
            logging.getLogger("in_process_runtime.events").setLevel(
                logging.WARNING)
            logging.getLogger("in_process_runtime").setLevel(logging.WARNING)
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("semantic_kernel").setLevel(logging.WARNING)

    def get_azure_config(self) -> dict:
        """Get Azure configuration as a dictionary."""
        return {
            "endpoint": self.azure_openai_endpoint,
            "api_key": self.azure_openai_api_key,
            "api_version": self.azure_openai_api_version,
        }

    def get_search_config(self) -> dict:
        """Get Azure Search configuration as a dictionary."""
        return {
            "endpoint": self.azure_search_endpoint,
            "api_key": self.azure_search_api_key,
            "default_index": self.azure_search_index_name,
        }

    def get_document_indexes(self) -> dict:
        """Get all document type indexes (abstract, from project config)."""
        return self.document_indexes


# Global configuration instance
_config = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
        try:
            _config.validate()
        except ConfigError as e:
            logger.error(f"Configuration validation failed: {e}")
            # Don't raise in get_config to allow partial functionality
            logger.warning(
                "Proceeding with partial configuration - some features may not work")
    return _config


def reset_config():
    """Reset the global configuration instance (useful for testing)."""
    global _config
    _config = None


# Initialize configuration on import
try:
    get_config()
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to initialize configuration: {e}")
    # Continue anyway - let individual components handle missing config

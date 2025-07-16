"""
Project-specific configuration management with restructured YAML support.
Handles loading and parsing of the new agent-centric project_config.yaml structure.
"""
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class FieldMappingsConfig:
    """Generic field mappings configuration (accepts any fields from YAML)."""

    def __init__(self, **kwargs):
        # Accept any fields from YAML but don't expose business-specific ones
        # in lib code
        for key, value in kwargs.items():
            setattr(self, key, value)


@dataclass
class CompanyConfig:
    """Company-specific configuration."""
    name: str = ""
    display_name: str = ""
    language: str = "en"
    region: str = "US"


@dataclass
class DocumentTypeConfig:
    """Document type configuration."""
    name: str = ""
    display_name: str = ""
    display_name_en: str = ""
    func_description: str = ""
    index_name: str = ""
    semantic_config: str = ""
    vector_field: str = ""
    key_fields: List[str] = None
    content_fields: List[str] = None

    def __post_init__(self):
        if self.key_fields is None:
            self.key_fields = []
        if self.content_fields is None:
            self.content_fields = []


@dataclass
class SearchDefaultConfig:
    """Search default settings configuration."""
    default_top_k: int = 20
    default_top_k_per_source: int = 5
    max_results_limit: int = 100
    enable_hybrid: bool = True
    enable_semantic: bool = True
    fallback_to_simple: bool = True


@dataclass
class ExtractionConfig:
    """Content extraction configuration."""
    content_truncate_length: int = 1000
    fallback_filename: str = "unknown_file"
    supported_extensions: List[str] = None

    def __post_init__(self):
        if self.supported_extensions is None:
            self.supported_extensions = ['.pdf', '.txt', '.docx']


@dataclass
class SearchExampleConfig:
    """Search example configuration for each document type."""
    description: str = ""
    function_name: str = ""
    query_examples: List[str] = None
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.query_examples is None:
            self.query_examples = []
        if self.parameters is None:
            self.parameters = {}


@dataclass
class DomainTerminologyConfig:
    """Domain-specific terminology configuration."""
    record_id_field: str = ""
    case_number_format: str = ""
    key_concepts: Dict[str, List[str]] = None

    def __post_init__(self):
        if self.key_concepts is None:
            self.key_concepts = {}


@dataclass
class AgentTemperatureConfig:
    """Agent temperature variation configuration."""
    temp: float = 0.3
    approach: str = ""
    description: str = ""


@dataclass
class ResearcherConfig:
    """Researcher agent configuration."""
    quality_thresholds: Dict[str, Any] = None
    default_model_settings: Dict[str, Any] = None
    report_indicators: Dict[str, List[str]] = None

    def __post_init__(self):
        if self.quality_thresholds is None:
            self.quality_thresholds = {}
        if self.default_model_settings is None:
            self.default_model_settings = {}
        if self.report_indicators is None:
            self.report_indicators = {}


@dataclass
class ReportWriterConfig:
    """Report writer agent configuration."""
    quality_requirements: Dict[str, Any] = None
    sections: Dict[str, List[str]] = None
    templates: Dict[str, Dict[str, str]] = None

    def __post_init__(self):
        if self.quality_requirements is None:
            self.quality_requirements = {}
        if self.sections is None:
            self.sections = {}
        if self.templates is None:
            self.templates = {}


@dataclass
class CitationConfig:
    """Citation agent configuration."""
    processing: Dict[str, Any] = None
    extraction_settings: Dict[str, Any] = None

    def __post_init__(self):
        if self.processing is None:
            self.processing = {}
        if self.extraction_settings is None:
            self.extraction_settings = {}


@dataclass
class CredibilityCriticConfig:
    """Credibility critic agent configuration."""
    assessment: Dict[str, Any] = None

    def __post_init__(self):
        if self.assessment is None:
            self.assessment = {}


@dataclass
class ReflectionCriticConfig:
    """Reflection critic agent configuration."""
    evaluation_criteria: Dict[str, str] = None
    improvement_suggestions: Dict[str, str] = None

    def __post_init__(self):
        if self.evaluation_criteria is None:
            self.evaluation_criteria = {}
        if self.improvement_suggestions is None:
            self.improvement_suggestions = {}


@dataclass
class SummarizerConfig:
    """Summarizer agent configuration."""
    summarization_settings: Dict[str, Any] = None
    output_format: Dict[str, List[str]] = None

    def __post_init__(self):
        if self.summarization_settings is None:
            self.summarization_settings = {}
        if self.output_format is None:
            self.output_format = {}


@dataclass
class TranslatorConfig:
    """Translator agent configuration."""
    supported_languages: List[str] = None
    translation_settings: Dict[str, bool] = None

    def __post_init__(self):
        if self.supported_languages is None:
            self.supported_languages = []
        if self.translation_settings is None:
            self.translation_settings = {}


@dataclass
class ModelConfig:
    """Model configuration."""
    default_settings: Dict[str, Any] = None
    agent_specific: Dict[str, Dict[str, Any]] = None

    def __post_init__(self):
        if self.default_settings is None:
            self.default_settings = {}
        if self.agent_specific is None:
            self.agent_specific = {}


@dataclass
class SystemConfig:
    """System-level configuration."""
    company: CompanyConfig
    logging: Dict[str, Any]


@dataclass
class WebSearchConfig:
    """Web search configuration."""
    enabled: bool = False
    fallback_enabled: bool = True
    max_results: int = 10
    timeout: int = 30


@dataclass
class DataSourcesConfig:
    """Data sources configuration."""
    web_search: WebSearchConfig
    document_types: Dict[str, DocumentTypeConfig]


@dataclass
class SearchConfig:
    """Complete search configuration."""
    default_settings: SearchDefaultConfig
    extraction: ExtractionConfig
    examples: Dict[str, SearchExampleConfig]

    @property
    def default_top_k(self) -> int:
        """Get default top k from settings."""
        return self.default_settings.default_top_k

    @property
    def default_top_k_per_source(self) -> int:
        """Get default top k per source from settings."""
        return self.default_settings.default_top_k_per_source

    @property
    def max_results_limit(self) -> int:
        """Get max results limit from settings."""
        return self.default_settings.max_results_limit

    @property
    def enable_hybrid(self) -> bool:
        """Get enable hybrid from settings."""
        return self.default_settings.enable_hybrid

    @property
    def enable_semantic(self) -> bool:
        """Get enable semantic from settings."""
        return self.default_settings.enable_semantic

    @property
    def fallback_to_simple(self) -> bool:
        """Get fallback to simple from settings."""
        return self.default_settings.fallback_to_simple


@dataclass
class AgentsConfig:
    """All agents configuration."""
    temperature_variations: Dict[str, AgentTemperatureConfig]
    researcher: ResearcherConfig
    report_writer: ReportWriterConfig
    citation: CitationConfig
    credibility_critic: CredibilityCriticConfig
    reflection_critic: ReflectionCriticConfig
    summarizer: SummarizerConfig
    translator: Optional[TranslatorConfig] = None


class ProjectConfig:
    """Project-specific configuration manager with restructured YAML support."""

    def __init__(self, config_file: str = None):
        """Initialize project configuration (only supports new agent-centric YAML)."""
        if config_file is None:
            workspace_root = self._find_workspace_root()
            config_file = os.path.join(
                workspace_root, "config", "project_config.yaml")
        self.config_file = config_file
        self.config = self._load_config()

        # Parse new format only
        system_config = self.config.get('system', {})
        self.company = CompanyConfig(**system_config.get('company', {}))
        self.logging = system_config.get('logging', {})

        data_sources = self.config.get('data_sources', {})

        # Web search configuration
        web_search_config = data_sources.get('web_search', {})
        self.web_search = WebSearchConfig(**web_search_config)

        # Document types configuration
        doc_types_config = data_sources.get('document_types', {})
        self.document_types = []
        for name, config in doc_types_config.items():
            doc_config = DocumentTypeConfig(
                name=name,
                display_name=config.get('display_name', ''),
                display_name_en=config.get('display_name_en', ''),
                func_description=config.get('func_description', ''),
                index_name=config['index_name'],
                semantic_config=config['semantic_config'],
                vector_field=config['vector_field'],
                key_fields=config['key_fields'],
                content_fields=config['content_fields']
            )
            self.document_types.append(doc_config)

        field_mappings_data = data_sources.get('field_mappings', {})
        self.field_mappings = FieldMappingsConfig(**field_mappings_data)

        domain_terminology_data = data_sources.get('domain_terminology', {})
        self.domain_terms = DomainTerminologyConfig(**domain_terminology_data)

        search_config = self.config.get('search', {})
        self.search_config = SearchConfig(
            default_settings=SearchDefaultConfig(**search_config.get('default_settings', {})),
            extraction=ExtractionConfig(**search_config.get('extraction', {})),
            examples={
                name: SearchExampleConfig(**config)
                for name, config in search_config.get('examples', {}).items()
            }
        )
        self.search = self.search_config.default_settings
        self.extraction = self.search_config.extraction
        self.search_examples = self.search_config.examples

        agents_config = self.config.get('agents', {})
        temp_variations = agents_config.get('temperature_variations', {})
        self.agents = {
            name: AgentTemperatureConfig(
                **config) for name,
            config in temp_variations.items()}
        self.temperature_variations = self.agents  # Alias for easy access

        self.researcher_config = ResearcherConfig(
            **agents_config.get('researcher', {}))
        self.report_writer_config = ReportWriterConfig(
            **agents_config.get('report_writer', {}))
        self.citation_config = CitationConfig(
            **agents_config.get('citation', {}))
        self.credibility_config = CredibilityCriticConfig(
            **agents_config.get('credibility_critic', {}))
        self.reflection_config = ReflectionCriticConfig(
            **agents_config.get('reflection_critic', {}))
        self.summarizer_config = SummarizerConfig(
            **agents_config.get('summarizer', {}))
        translator_config = agents_config.get('translator')
        self.translator_config = TranslatorConfig(
            **translator_config) if translator_config else None

        models_config = self.config.get('models', {})
        self.model_config = ModelConfig(**models_config)

        # Compatibility property
        citation_processing = self.citation_config.processing
        self.citations = type('CitationConfig', (), {
            'internal_document_label': citation_processing.get('internal_document_label', ''),
            'no_citations_text': citation_processing.get('no_citations_text', ''),
            'reference_section_title': citation_processing.get('reference_section_title', {}),
            'language_indicators': citation_processing.get('language_indicators', {})
        })()
        self.quality_thresholds = self.researcher_config.quality_thresholds
        self.credibility = self.credibility_config.assessment
        self.report_quality = self.report_writer_config.quality_requirements
        self.report_quality['sections'] = self.report_writer_config.sections
        self.report_templates = {
            'error_template': self.report_writer_config.templates,
            'quality_indicators': self.researcher_config.report_indicators
        }

        logger.info(f"Project configuration loaded for {
                    self.company.name} (new format only)")

    def _is_file_restructured(self, config_file: str) -> bool:
        """Check if the config file uses the new restructured format."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return 'system' in config and 'data_sources' in config and 'agents' in config
        except BaseException:
            return False

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(
                f"Loaded project configuration from {
                    self.config_file}")
            return config
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Project configuration file not found: {
                    self.config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")

    # === Existing methods for backward compatibility ===

    def get_document_type(self, name: str) -> Optional[DocumentTypeConfig]:
        """Get document type configuration by name."""
        for dt in self.document_types:
            if dt.name == name:
                return dt
        return None

    def get_document_types_by_index(self) -> Dict[str, DocumentTypeConfig]:
        """Get mapping of index names to document types."""
        return {dt.index_name: dt for dt in self.document_types}

    def get_semantic_config_map(self) -> Dict[str, str]:
        """Get mapping of document type names to semantic configurations."""
        return {dt.name: dt.semantic_config for dt in self.document_types}

    def get_vector_field_map(self) -> Dict[str, str]:
        """Get mapping of document type names to vector fields."""
        return {dt.name: dt.vector_field for dt in self.document_types}

    def get_content_fields(self, document_type_name: str) -> List[str]:
        """Get content fields for a specific document type."""
        dt = self.get_document_type(document_type_name)
        return dt.content_fields if dt else []

    def get_citation_reference_title(self, language: str = None) -> str:
        """Get reference section title for citations."""
        if language is None:
            language = self.company.language

        return self.citations.reference_section_title.get(
            language,
            self.citations.reference_section_title.get('ja', 'References')
        )

    def detect_language(self, text: str) -> str:
        """Detect language based on text content."""
        for lang, indicators in self.citations.language_indicators.items():
            if any(indicator in text for indicator in indicators):
                return lang
        return self.company.language

    def get_logging_message(self, key: str) -> str:
        """Get company-specific logging message."""
        return self.logging.get('company_specific_messages', {}).get(key, "")

    def is_supported_file_extension(self, filename: str) -> bool:
        """Check if file extension is supported."""
        return any(ext in filename.lower()
                   for ext in self.extraction.supported_extensions)

    def get_field_mappings(self, key: str) -> list:
        """Get field mappings for a given key."""
        return getattr(self.field_mappings, key, [])

    def get_agent_config(
            self,
            agent_type: str) -> Optional[AgentTemperatureConfig]:
        """Get agent configuration by type."""
        return self.agents.get(agent_type)

    def get_error_template(self, template_type: str) -> str:
        """Get error template by type."""
        return self.report_templates.get(
            'error_template', {}).get(
            template_type, "")

    def get_quality_indicators(self, indicator_type: str) -> List[str]:
        """Get quality indicators by type."""
        return self.report_templates.get(
            'quality_indicators', {}).get(
            indicator_type, [])

    def get_search_example(
            self, document_type: str) -> Optional[Dict[str, Any]]:
        """Get search example configuration for a document type as a dictionary."""
        search_example_config = self.search_examples.get(document_type)
        if search_example_config:
            # Convert SearchExampleConfig to dictionary
            return {
                'description': search_example_config.description,
                'function_name': search_example_config.function_name,
                'query_examples': search_example_config.query_examples,
                'parameters': search_example_config.parameters
            }
        return None

    def get_domain_key_concepts(self, concept_category: str) -> List[str]:
        """Get domain key concepts by category."""
        return self.domain_terms.key_concepts.get(concept_category, [])

    def get_credibility_score_range(self, level: str) -> str:
        """Get credibility score range for a level (high/medium/low)."""
        return self.credibility.get('score_ranges', {}).get(level, "")

    def get_credibility_criteria(self, criterion: str) -> str:
        """Get credibility evaluation criterion description."""
        return self.credibility.get(
            'evaluation_criteria', {}).get(
            criterion, "")

    def get_credibility_quality_indicators(self) -> List[str]:
        """Get credibility quality indicators."""
        return self.credibility.get('quality_indicators', [])

    def get_required_report_sections(self) -> List[str]:
        """Get required report sections."""
        return self.report_quality.get('sections', {}).get('required', [])

    def get_optional_report_sections(self) -> List[str]:
        """Get optional report sections."""
        return self.report_quality.get('sections', {}).get('optional', [])

    def is_citation_verification_mandatory(self) -> bool:
        """Check if citation verification is mandatory."""
        return self.report_quality.get('citation_verification_mandatory', True)

    def is_internal_sources_only(self) -> bool:
        """Check if only internal sources are allowed."""
        return self.report_quality.get('internal_sources_only', True)

    def get_case_number_format(self) -> str:
        """Get the standard case number format."""
        return self.domain_terms.case_number_format

    def get_record_id_field_name(self) -> str:
        """Get the record ID field name."""
        return self.domain_terms.record_id_field

    def get_prid_field_name(self) -> str:
        """Get the record ID field name (legacy compatibility)."""
        return self.get_record_id_field_name()

    # === New methods for restructured config ===

    def get_agent_model_settings(self, agent_name: str) -> Dict[str, Any]:
        """Get model settings for a specific agent."""
        if hasattr(self, 'model_config'):
            agent_settings = self.model_config.agent_specific.get(
                agent_name, {})
            default_settings = self.model_config.default_settings
            # Merge with defaults
            settings = default_settings.copy()
            settings.update(agent_settings)
            return settings
        return {}

    def get_researcher_quality_thresholds(self) -> Dict[str, Any]:
        """Get researcher quality thresholds."""
        if hasattr(self, 'researcher_config'):
            return self.researcher_config.quality_thresholds
        return self.quality_thresholds

    def get_report_writer_sections(self) -> Dict[str, List[str]]:
        """Get report writer section configuration."""
        if hasattr(self, 'report_writer_config'):
            return self.report_writer_config.sections
        return self.report_quality.get('sections', {})

    def get_citation_processing_config(self) -> Dict[str, Any]:
        """Get citation processing configuration."""
        if hasattr(self, 'citation_config'):
            return self.citation_config.processing
        return {}

    def get_credibility_assessment_config(self) -> Dict[str, Any]:
        """Get credibility assessment configuration."""
        if hasattr(self, 'credibility_config'):
            return self.credibility_config.assessment
        return self.credibility

    def get_summarizer_settings(self) -> Dict[str, Any]:
        """Get summarizer configuration."""
        if hasattr(self, 'summarizer_config'):
            return self.summarizer_config.summarization_settings
        return {}

    def get_reflection_criteria(self) -> Dict[str, Any]:
        """Get reflection critic evaluation criteria."""
        if hasattr(self, 'reflection_config'):
            return self.reflection_config.evaluation_criteria
        return {}

    def get_reflection_improvement_suggestions(self) -> Dict[str, Any]:
        """Get reflection critic improvement suggestions."""
        if hasattr(self, 'reflection_config'):
            return self.reflection_config.improvement_suggestions
        return {}

    def get_report_writer_config(self) -> Dict[str, Any]:
        """Get report writer configuration."""
        if hasattr(self, 'report_writer_config'):
            return {
                'quality_requirements': self.report_writer_config.quality_requirements,
                'sections': self.report_writer_config.sections,
                'templates': self.report_writer_config.templates}
        # Fallback for legacy config
        return {
            'quality_requirements': self.report_quality.get(
                'quality_requirements', {}), 'sections': self.report_quality.get(
                'sections', {}), 'templates': self.report_templates}

    def get_citation_config(self) -> Dict[str, Any]:
        """Get citation agent configuration."""
        if hasattr(self, 'citation_config'):
            return {
                'processing': self.citation_config.processing,
                'extraction_settings': self.citation_config.extraction_settings
            }
        # Fallback for legacy config
        citation_processing = getattr(self, 'citations', None)
        if citation_processing:
            return {
                'processing': {
                    'internal_document_label': citation_processing.internal_document_label,
                    'no_citations_text': citation_processing.no_citations_text,
                    'reference_section_title': citation_processing.reference_section_title,
                    'language_indicators': citation_processing.language_indicators},
                'extraction_settings': {}}
        return {'processing': {}, 'extraction_settings': {}}

    def get_credibility_config(self) -> Dict[str, Any]:
        """Get credibility critic configuration."""
        if hasattr(self, 'credibility_config'):
            return {
                'assessment': self.credibility_config.assessment
            }
        return {'assessment': self.credibility}

    def get_summarizer_config(self) -> Dict[str, Any]:
        """Get summarizer agent configuration."""
        if hasattr(self, 'summarizer_config'):
            return {
                'summarization_settings': self.summarizer_config.summarization_settings,
                'output_format': self.summarizer_config.output_format}
        return {'summarization_settings': {}, 'output_format': {}}

    def get_translator_config(self) -> Dict[str, Any]:
        """Get translator agent configuration."""
        if hasattr(self, 'translator_config') and self.translator_config:
            return {
                'supported_languages': self.translator_config.supported_languages,
                'translation_settings': self.translator_config.translation_settings}
        return {
            'supported_languages': [
                'ja',
                'en'],
            'translation_settings': {}}

    def get_index_names(self) -> Dict[str, str]:
        """Get mapping of document type names to their index names."""
        index_mapping = {}
        for doc_type in self.document_types:
            index_mapping[doc_type.name] = doc_type.index_name
        return index_mapping


    def _find_workspace_root(self) -> str:
        """Find the workspace root directory by looking for key files."""
        # Start from the current file's directory
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # Look for workspace indicators (main.py, pyproject.toml, etc.)
        workspace_indicators = [
            'main.py',
            'pyproject.toml',
            'requirements.txt',
            '.git']

        # Traverse up the directory tree
        while current_dir != os.path.dirname(current_dir):  # Not at root
            for indicator in workspace_indicators:
                if os.path.exists(os.path.join(current_dir, indicator)):
                    return current_dir
            current_dir = os.path.dirname(current_dir)

        # Fallback to the traditional method if indicators not found
        fallback_root = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__)))
        logger.warning(
            f"Workspace root not found via indicators, using fallback: {fallback_root}")
        return fallback_root


# Global project configuration instance
_project_config = None


def get_project_config() -> ProjectConfig:
    """Get the global project configuration instance."""
    global _project_config
    if _project_config is None:
        _project_config = ProjectConfig()
    return _project_config

"""
Common prompt constants and shared elements.
Provides reusable components for all agent prompts.
Now uses configuration-based values instead of hardcoded constants.
"""

from datetime import datetime
from lib.config.project_config import ProjectConfig
from lib.utils.prompt_manager import PromptManager


# Initialize configuration-based prompt manager
def get_prompt_manager() -> PromptManager:
    """Get prompt manager instance with project configuration."""
    try:
        config = ProjectConfig()
        return PromptManager(config)
    except Exception:
        # Fallback for cases where config is not available
        return None


# ============================================================================
# EXECUTION CONTEXT INFORMATION
# ============================================================================

def get_execution_context() -> str:
    """Get current execution context including date and time."""
    now = datetime.now()
    return f"""## EXECUTION CONTEXT
📅 **Current Date**: {now.strftime('%Y-%m-%d (%A)')}
🕐 **Current Time**: {now.strftime('%H:%M:%S')}
"""


# ============================================================================
# DYNAMIC CONFIGURATION-BASED REQUIREMENTS
# ============================================================================

def get_common_internal_only_requirement() -> str:
    """Get internal-only requirement text from configuration."""
    prompt_manager = get_prompt_manager()
    if prompt_manager:
        return prompt_manager.get_internal_only_requirement()
    else:
        # Fallback text
        return "**INTERNAL SOURCES ONLY**: All research must be based exclusively on internal documents. NO external information or assumptions permitted."


def get_common_search_functions() -> str:
    """Get search functions section from configuration."""
    prompt_manager = get_prompt_manager()
    if prompt_manager:
        return f"## AVAILABLE SEARCH FUNCTIONS\n{
            prompt_manager.get_search_functions_section()}"
    else:
        # Fallback text
        return """## AVAILABLE SEARCH FUNCTIONS
✅ **search_category_a**: Category A reports (Function A)
✅ **search_category_b**: Category B reports (Function B)
✅ **search_category_c**: Historical lists (9+ years with ID numbers)
✅ **search_research_findings**: Research institute findings and reports
✅ **search_all_documents**: Comprehensive search across all available document types"""


def get_common_output_format() -> str:
    """Get output formatting standards from configuration."""
    prompt_manager = get_prompt_manager()
    if prompt_manager:
        company_context = prompt_manager.get_company_context()
        record_id_field = prompt_manager.get_record_id_field()
        return f"""## OUTPUT FORMATTING STANDARDS
- Use clear {company_context['company_language']}
            language for internal {
            company_context['company_display_name']} documentation
- Include specific {record_id_field} numbers and case references when available
- Maintain professional industry terminology
- Provide structured, well-organized responses
- Include confidence levels for findings when applicable"""
    else:
        # Fallback text
        return """## OUTPUT FORMATTING STANDARDS
- Use clear Japanese language for internal documentation
- Include specific record ID numbers and case references when available
- Maintain professional industry terminology
- Provide structured, well-organized responses
- Include confidence levels for findings when applicable"""


# ============================================================================
# CONSTANT ELEMENTS (NOT CONFIGURATION-DEPENDENT)
# ============================================================================

COMMON_SEARCH_POLICY = """🚫 **BALANCED SEARCH POLICY**:
⚠️ **Technical Limitation**: Maximum 3 searches per turn to prevent token overflow
- ✅ Each search uses top_k=50 for maximum information retrieval
- ✅ Strategic keyword selection for optimal coverage within turn limits
- ✅ Efficient search planning to maximize comprehensiveness
- ❌ Do NOT restrict search scope due to cost or time concerns
- ❌ Do NOT terminate early claiming "sufficient results"
- ❌ Do NOT impose arbitrary result limits beyond technical constraints"""

COMMON_MEMORY_INTEGRATION = """## MEMORY INTEGRATION REQUIREMENTS
**Session-Based Memory**: Memory is volatile and session-based - no persistent cross-session storage
**Pre-Operation**: Use search_memory() to check for relevant context ONLY if session is ongoing
**Post-Operation**: Use store_memory() to preserve valuable results and patterns for session continuity"""

# ============================================================================
# CRITICAL REQUIREMENTS TEMPLATE
# ============================================================================


def get_critical_requirements_template() -> str:
    """Get critical requirements template from configuration."""
    internal_only = get_common_internal_only_requirement()
    execution_context = get_execution_context()
    return f"""{execution_context}

## CRITICAL REQUIREMENTS - NON-NEGOTIABLE
{internal_only}
**EXHAUSTIVE SEARCH**: Conduct comprehensive searches across all available document types without arbitrary limits.
**MAXIMUM RESULTS**: Always use top_k=50 for maximum information retrieval.
**TECHNICAL LIMITATION**: Maximum 3 searches per turn to avoid token overflow (technical constraint, not quality limitation).

{COMMON_SEARCH_POLICY}

{COMMON_MEMORY_INTEGRATION}"""


# ============================================================================
# BACKWARD COMPATIBILITY CONSTANTS
# ============================================================================

# Keep old constants for backward compatibility, but they now use dynamic
# functions
COMMON_INTERNAL_ONLY_REQUIREMENT = get_common_internal_only_requirement()
COMMON_SEARCH_FUNCTIONS = get_common_search_functions()
CRITICAL_REQUIREMENTS_TEMPLATE = get_critical_requirements_template()
COMMON_OUTPUT_FORMAT = get_common_output_format()
EXECUTION_CONTEXT = get_execution_context()  # Add execution context as constant

# ============================================================================
# IMAGE MANAGEMENT CONSTANTS
# ============================================================================

IMAGE_MANAGEMENT_FUNCTIONS = {
    "list_images": "List all registered images in the system",
    "get_image": "Retrieve image content by reference",
    "validate_images": "Validate image references in text content",
    "image_feedback": "Get user feedback on image usage",
    "convert_paths": "Convert image references to local paths"
}

IMAGE_HANDLING_RULES = """## IMAGE HANDLING RULES
- **Image References**: Always use format data/images/IMGxxx.jpg for local images
- **Path Preservation**: NEVER modify existing image paths in documents
- **No Invention**: NEVER create/invent image content or references
- **Validation Required**: Always use validate_image_references_in_text() before processing
- **MANDATORY**: All image operations must use IMAGE_MANAGEMENT_FUNCTIONS
- **Error Handling**: If validation fails, request user clarification
- **Local Only**: Only reference images that exist in the data/images/ directory"""

# ============================================================================
# TEMPERATURE-SPECIFIC SEARCH STRATEGY
# ============================================================================

TEMPERATURE_SEARCH_STRATEGY = """🚫 **TEMPERATURE-SPECIFIC SEARCH STRATEGY**:
⚠️ **Technical Constraints**: Please ensure to execute the following balanced investigation
- ⚠️ **Do not perform more than 3 searches in one turn** (technical constraint due to token limits)
- ✅ Always use top_k=50 for search results (quality maximization)
- ✅ Strategically select keywords and search efficiently up to 3 times maximum
- ✅ Use top_k=50 for each search to maximize information retrieval
- ✅ Achieve maximum comprehensiveness with limited search queries
- ❌ Do not restrict research due to cost or time constraints
- ❌ Do not terminate early with "sufficient results" """

# ============================================================================
# OUTPUT FORMATTING STANDARDS - NOW DYNAMIC
# ============================================================================

# Replaced with dynamic function get_common_output_format() above

# ============================================================================
# SEARCH RESULT HANDLING STANDARDS
# ============================================================================

SEARCH_RESULT_STANDARDS = """## SEARCH RESULT HANDLING
- **Comprehensive Analysis**: Analyze ALL provided search results thoroughly
- **Source Attribution**: Properly cite internal document sources
- **Quality Assessment**: Evaluate relevance and reliability of findings
- **Metadata Preservation**: Maintain all source identifiers and references
- **Professional Standards**: Follow industry documentation practices
- **Gap Identification**: Identify areas where additional searches may be needed
- **Result Synthesis**: Combine findings from multiple sources effectively"""

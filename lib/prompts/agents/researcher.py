"""
Researcher Agent Prompts

This module contains all prompts related to the researcher agents
including individual researchers, lead researchers, and temperature-specific variations.
"""
import logging
from typing import Optional

from lib.config.project_config import get_project_config
from lib.utils.prompt_manager import PromptManager

logger = logging.getLogger(__name__)


def get_researcher_prompt() -> str:
    """Generate dynamic researcher prompt from configuration."""
    try:
        config = get_project_config()
        prompt_manager = PromptManager(config)
        company_context = prompt_manager.get_company_context()

        return f"""📝 RESEARCHER AGENT - INTERNAL DOCUMENT SPECIALIST 📝

You are an individual research agent specializing in comprehensive internal document analysis.

## ROLE & PURPOSE
Expert researcher performing exhaustive analysis of internal {
            company_context['company_name']}
            documents using Azure AI Search. You work as part of a team of 3 parallel researchers, each with different analytical approaches.

## CRITICAL REQUIREMENTS
**INTERNAL SOURCES ONLY**: All research must be based exclusively on internal {company_context['company_name']}
            documents. NO external information or assumptions permitted.
**FILE NAME PRESERVATION**: When generating answers, referenced file names must NEVER be changed and MUST include their original extensions exactly as found in the search results.
**SEARCH RESULT FIDELITY**: Only reference information that is explicitly included in the search results - do NOT reference or infer information that is not present in the actual search results.

## SEARCH CAPABILITIES
✅ **Available Search Functions**:
{prompt_manager.get_search_functions_section()}

## SEARCH STRATEGY
🔍 **COMPREHENSIVE INVESTIGATION**:
- Use multiple search keywords and variations
- Search across all available document types
- Apply different analytical perspectives based on your temperature setting
- Cross-reference findings across document sources
- Ensure no relevant information is missed within 3 search limit

## OUTPUT REQUIREMENTS
📊 **STRUCTURED RESULTS**: Return comprehensive analysis with:
- Detailed findings from all searches performed
- Source attribution for all information
- Complete preservation of case numbers, dates, and specifics
- Clear indication of search strategy used
- Acknowledgment of any limitations encountered

🎯 **COMPREHENSIVE COVERAGE**:
- Provide thorough analysis within search limits
- Include all relevant cases and examples found
- Cross-reference information between different document types
- Highlight any gaps or areas requiring additional investigation

## CRITICAL LIMITATIONS
⚠️ CRITICAL LIMITATION: You can ONLY search internal {company_context['company_name']} document repositories. You CANNOT access external websites, public databases, or internet sources.

## ANALYTICAL APPROACH
Based on your assigned temperature setting, apply the appropriate analytical approach:
- **Conservative (0.2)**: Focus on verified facts and established patterns
- **Balanced (0.6)**: Combine factual analysis with reasonable inferences
- **Creative (0.9)**: Explore broader implications and innovative perspectives

Remember: Your role is to conduct thorough research within the available internal document ecosystem and provide comprehensive, well-sourced analysis for research and development decision-making.

IMPORTANT: Always clarify to users that you can only search internal {company_context['company_name']} documents."""
    except Exception as e:
        logger.error(f"Error generating researcher prompt: {e}")
        return "Error generating prompt - please check configuration"


def get_lead_researcher_prompt() -> str:
    """Generate dynamic lead researcher prompt from configuration."""
    try:
        config = get_project_config()
        prompt_manager = PromptManager(config)
        company_context = prompt_manager.get_company_context()

        return f"""🔬 LEAD RESEARCHER AGENT - COMPREHENSIVE ANALYSIS COORDINATOR 🔬

You are the Lead Researcher coordinating comprehensive research analysis.

## PRIMARY ROLE
Senior research coordinator managing exhaustive internal document analysis across all available {
            company_context['company_name']} repositories using Azure AI Search capabilities.

## CRITICAL REQUIREMENTS
**INTERNAL SOURCES ONLY**: All research must be based exclusively on internal {company_context['company_name']}
            documents. NO external information or assumptions permitted.
**FILE NAME PRESERVATION**: When generating answers, referenced file names must NEVER be changed and MUST include their original extensions exactly as found in the search results.
**SEARCH RESULT FIDELITY**: Only reference information that is explicitly included in the search results - do NOT reference or infer information that is not present in the actual search results.

## SEARCH CAPABILITIES & STRATEGY
- Searches ONLY internal {company_context['company_name']} document repositories **COMPREHENSIVELY**
- Utilizes ALL available search functions for maximum coverage
- Coordinates multiple search approaches for thorough investigation
- Cross-references findings across different document types and time periods

## Available Search Functions:
{prompt_manager.get_search_functions_section()}

## COMPREHENSIVE RESEARCH FRAMEWORK
🎯 **SYSTEMATIC APPROACH**:
1. **Initial Broad Search**: Cast wide net across all document types
2. **Targeted Deep-Dive**: Focus on specific areas based on initial findings
3. **Cross-Validation**: Verify findings across multiple sources
4. **Gap Analysis**: Identify and address information gaps within search limits

📊 **QUALITY STANDARDS**:
- Exhaustive coverage within 3-search limitation
- Complete case preservation with full details
- Source attribution for all findings
- Clear documentation of search strategy and limitations

IMPORTANT: Always clarify to users that you can only search internal {company_context['company_name']} documents."""
    except Exception as e:
        logger.error(f"Error generating lead researcher prompt: {e}")
        return "Error generating prompt - please check configuration"


def get_temperature_researcher_prompt(
        temperature_type: str = "balanced") -> str:
    """Generate temperature-specific researcher prompt from configuration."""
    try:
        config = get_project_config()
        prompt_manager = PromptManager(config)
        company_context = prompt_manager.get_company_context()

        # Get temperature configuration
        agent_config = config.get_agent_config(temperature_type)
        if not agent_config:
            agent_config = config.get_agent_config("balanced")  # fallback

        temp_approach = agent_config.approach if agent_config else "Balanced Analysis"
        temp_description = agent_config.description if agent_config else "Comprehensive analysis balancing facts and insights"

        return f"""🌡️ {
            temp_approach.upper()} RESEARCHER AGENT 🌡️

## SPECIALIZED ANALYTICAL APPROACH
**Temperature Setting**: {temperature_type.title()}
**Analysis Style**: {temp_approach}
**Focus**: {temp_description}

## ROLE & PURPOSE
Specialized researcher performing {temp_approach.lower()} of internal {company_context['company_name']} documents using Azure AI Search.

## CRITICAL REQUIREMENTS
**INTERNAL SOURCES ONLY**: All research must be based exclusively on internal {company_context['company_name']}
                                           documents. NO external information or assumptions permitted.

## Available Search Functions:
{prompt_manager.get_search_functions_section()}

## ANALYTICAL FRAMEWORK
Based on your {temperature_type} temperature setting:
{temp_description}

## OUTPUT REQUIREMENTS
📊 **SPECIALIZED ANALYSIS**: Provide research results that reflect your {temperature_type} analytical approach:
- Apply your specialized perspective to all findings
- Maintain scientific rigor appropriate for research and development
- Include complete source attribution and case details
- Clearly indicate your analytical approach in the results

IMPORTANT: Always clarify to users that you can only search internal {company_context['company_name']} documents."""
    except Exception as e:
        logger.error(f"Error generating temperature researcher prompt: {e}")
        return "Error generating prompt - please check configuration"


# Backward compatibility - expose the prompts as constants
# These are initialized lazily to avoid import-time configuration loading
_researcher_prompt = None
_lead_researcher_prompt = None
_conservative_researcher_prompt = None
_balanced_researcher_prompt = None
_creative_researcher_prompt = None


def _get_researcher_prompt_cached():
    global _researcher_prompt
    if _researcher_prompt is None:
        _researcher_prompt = get_researcher_prompt()
    return _researcher_prompt


def _get_lead_researcher_prompt_cached():
    global _lead_researcher_prompt
    if _lead_researcher_prompt is None:
        _lead_researcher_prompt = get_lead_researcher_prompt()
    return _lead_researcher_prompt


def _get_conservative_researcher_prompt_cached():
    global _conservative_researcher_prompt
    if _conservative_researcher_prompt is None:
        _conservative_researcher_prompt = get_temperature_researcher_prompt(
            "conservative")
    return _conservative_researcher_prompt


def _get_balanced_researcher_prompt_cached():
    global _balanced_researcher_prompt
    if _balanced_researcher_prompt is None:
        _balanced_researcher_prompt = get_temperature_researcher_prompt(
            "balanced")
    return _balanced_researcher_prompt


def _get_creative_researcher_prompt_cached():
    global _creative_researcher_prompt
    if _creative_researcher_prompt is None:
        _creative_researcher_prompt = get_temperature_researcher_prompt(
            "creative")
    return _creative_researcher_prompt

# For better backward compatibility, make the constant versions available


def __getattr__(name):
    """Dynamic attribute access for backward compatibility."""
    if name == 'RESEARCHER_PROMPT':
        return _get_researcher_prompt_cached()
    elif name == 'LEAD_RESEARCHER_PROMPT':
        return _get_lead_researcher_prompt_cached()
    elif name == 'CONSERVATIVE_RESEARCHER_PROMPT':
        return _get_conservative_researcher_prompt_cached()
    elif name == 'BALANCED_RESEARCHER_PROMPT':
        return _get_balanced_researcher_prompt_cached()
    elif name == 'CREATIVE_RESEARCHER_PROMPT':
        return _get_creative_researcher_prompt_cached()
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

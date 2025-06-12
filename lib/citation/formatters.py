"""
Citation formatting utilities.
Handles markdown generation, report integration, and multi-language support.
"""
import logging
import os
from typing import Any, Dict, List, Optional

from .models import Citation

# Import project configuration
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from config.project_config import get_project_config
except ImportError:
    def get_project_config():
        return None

logger = logging.getLogger(__name__)


class CitationFormatter:
    """Handles formatting of citations for various output formats."""

    @staticmethod
    def extract_proper_filename(result: Dict[str, Any]) -> str:
        """
        Extract proper filename from search result, avoiding Document IDs.
        Priority: actual filename > document_title > descriptive name
        """
        # Debug: Log available fields for filename extraction
        logger.debug(
            f"[DEBUG] Extracting filename from fields: {
                list(
                    result.keys())}")

        # Get project configuration
        project_config = get_project_config()

        # Get case number (project-specific key field)
        case_number = result.get("record_id")

        # Try document_title first for more specific filenames
        document_title = result.get("document_title", "")
        if document_title:
            filename = os.path.basename(document_title)
            if project_config and project_config.is_supported_file_extension(
                    filename):
                logger.debug(
                    f"[DEBUG] Using document_title filename: {filename}")
                return f"{filename}, Record ID: {
                    case_number}" if case_number else filename

        # Final fallback - use project config or default
        if project_config:
            fallback_filename = project_config.extraction.fallback_filename
        else:
            fallback_filename = "Internal Document"

        logger.debug(f"[DEBUG] Using fallback filename: {fallback_filename}")
        return fallback_filename

    @staticmethod
    def generate_citation_list(citations: Dict[str, Citation]) -> str:
        """Generate formatted citation list."""
        if not citations:
            project_config = get_project_config()
            if project_config:
                return project_config.citations.no_citations_text
            else:
                return "*No citations available*"

        citation_list = []
        for citation in citations.values():
            citation_list.append(citation.to_markdown())

        return "\n\n".join(citation_list)

    @staticmethod
    def process_report_citations(
        report_text: str,
        citations: Dict[str, Citation],
        language_detection: bool = True
    ) -> str:
        """
        Process citations for a complete report with language detection.

        Args:
            report_text: The draft report text
            citations: Dictionary of citations
            language_detection: Whether to auto-detect language

        Returns:
            str: Report with proper citations and reference section
        """
        # Get project configuration
        project_config = get_project_config()

        if project_config:
            log_msg = project_config.get_logging_message('citation_processing')
            logger.info(log_msg or "=== Citation Processing for Report ===")
        else:
            logger.info(
                "=== Citation Processing for Report (INTERNAL SOURCES ONLY) ===")

        # Validate that we have citations to work with
        if not citations:
            if project_config:
                warning_msg = project_config.get_logging_message(
                    'no_internal_citations')
                logger.warning(
                    warning_msg or "No citations available for processing")
            else:
                logger.warning(
                    "No INTERNAL citations available for processing - report will be returned without citations")
            return report_text

        # Generate citation list (all from internal sources)
        citation_list = CitationFormatter.generate_citation_list(citations)

        # Add reference section to report with proper language detection
        if "## References" not in report_text and "## References" not in report_text:
            if language_detection and project_config:
                # Use project config for language detection
                detected_language = project_config.detect_language(report_text)
                ref_title = project_config.get_citation_reference_title(
                    detected_language)
                report_with_citations = report_text + \
                    f"\n\n## {ref_title}\n\n" + citation_list
            elif language_detection:
                # Fallback language detection
                japanese_indicators = ["である", "です", "ます", "について", "により", "として"]
                is_japanese = any(
                    indicator in report_text for indicator in japanese_indicators)

                if is_japanese or len(citations) > 0:
                    report_with_citations = report_text + \
                        "\n\n## References (Internal Documents Only)\n\n" + citation_list
                else:
                    report_with_citations = report_text + \
                        "\n\n## References (Internal Documents Only)\n\n" + citation_list
            else:
                # Default to English format
                report_with_citations = report_text + \
                    "\n\n## References (Internal Documents Only)\n\n" + citation_list
        else:
            # Replace existing reference section
            if project_config:
                ref_title = project_config.get_citation_reference_title()
            else:
                ref_title = "References (Internal Documents Only)"

            if "## References" in report_text:
                parts = report_text.split("## References")
                report_with_citations = parts[0] + \
                    f"## {ref_title}\n\n" + citation_list
            elif "## References" in report_text:
                parts = report_text.split("## References")
                report_with_citations = parts[0] + \
                    f"## {ref_title}\n\n" + citation_list
            else:
                report_with_citations = report_text

        logger.info(
            f"Citation processing completed with {
                len(citations)} total citations")

        if project_config:
            grounding_msg = project_config.get_logging_message(
                'citation_grounding')
            no_external_msg = project_config.get_logging_message(
                'no_external_info')
            if grounding_msg:
                logger.info(grounding_msg)
            if no_external_msg:
                logger.info(no_external_msg)
        else:
            logger.info(
                "CRITICAL: All citations are strictly grounded to INTERNAL AI Search results only")
            logger.info(
                "NO external links or external information included in citations")

        return report_with_citations

    @staticmethod
    def format_citation_summary(citations: Dict[str, Citation]) -> str:
        """
        Generate a summary of citations for display.

        Args:
            citations: Dictionary of citations

        Returns:
            Formatted summary string
        """
        if not citations:
            return "No citations found"

        result = f"Found {len(citations)} citations:\n\n"
        for citation in citations.values():
            result += f"{citation.to_markdown()}\n"
        return result

    @staticmethod
    def extract_content_from_search_result(result: Dict[str, Any]) -> str:
        """
        Extract content text from search result with priority order.

        Args:
            result: Search result dictionary

        Returns:
            Extracted content text (truncated to 200 chars + ...)
        """
        # Get project configuration
        project_config = get_project_config()

        # Look for content in any available field
        content = ""
        content_fields = ["content_text", "Details", "content", "chunk", "text", "body", "summary"]
        for field in content_fields:
            if result.get(field):
                content = str(result[field])
                break
        
        # If no content found in standard fields, try any field with substantial text
        if not content:
            for key, value in result.items():
                if key not in ['score', 'search_type', 'content_path', 'document_title'] and value:
                    text_value = str(value).strip()
                    if len(text_value) > 50:  # Minimum content length
                        content = text_value
                        break

        # Truncate long content using project config
        if project_config:
            max_length = project_config.extraction.content_truncate_length
        else:
            max_length = 200

        if len(content) > max_length:
            return content[:max_length] + "..."
        return content

"""
Citation validation utilities.
Handles internal source validation and data integrity checks.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CitationValidator:
    """Handles validation of citations and search results."""

    @staticmethod
    def is_valid_internal_source(result: Dict[str, Any]) -> bool:
        """
        Validate that a search result is from internal AI Search sources only.

        Args:
            result: Search result dictionary

        Returns:
            bool: True if valid internal source, False otherwise
        """
        # Debug: Log the structure of the search result
        logger.info(f"[DEBUG] Search result structure: {list(result.keys())}")
        logger.info(f"[DEBUG] Sample field values:")
        for key in [
            'search_type',
            'content_text',
            'Details',
            'text_document_id',
            'record_id',
            'document_title',
            'content',
                'score']:
            if key in result:
                value = result[key]
                if isinstance(value, str) and len(value) > 100:
                    logger.info(f"  {key}: {value[:100]}...")
                else:
                    logger.info(f"  {key}: {value}")
            else:
                logger.info(f"  {key}: NOT PRESENT")

        # Check for external URL indicators (reject external sources)
        content_path = result.get("content_path", "")
        if content_path and any(
            indicator in content_path.lower() for indicator in [
                "http://",
                "https://",
                "www.",
                ".com",
                ".org"]):
            logger.warning(f"Rejected external URL source: {content_path}")
            return False

        # Check for document title that looks like external source
        document_title = result.get("document_title", "")
        if document_title and any(
            indicator in document_title.lower() for indicator in [
                "http", "www", ".com", ".org", "external", "web"]):
            logger.warning(
                f"Rejected external document title: {document_title}")
            return False

        # Check for at least some content - look for any non-empty field
        has_content = any(
            value and str(value).strip() 
            for key, value in result.items() 
            if key not in ['score', 'search_type', 'content_path', 'document_title']
        )
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Has content check: {has_content}")
            content_fields = [k for k, v in result.items() if v and str(v).strip()]
            if content_fields:
                logger.debug(f"Found content in fields: {content_fields[:5]}...")  # Show first 5 fields

        if not has_content:
            logger.warning("Missing content fields - empty search result")
            return False

        # For now, accept any search result that has content and is not external
        # We'll refine this based on what we see in the debug logs
        logger.debug(f"Accepted internal source with content")
        return True

    @staticmethod
    def validate_citation_data(citation_data: Dict[str, Any]) -> List[str]:
        """
        Validate citation data for completeness and correctness.

        Args:
            citation_data: Citation data dictionary

        Returns:
            List of validation error messages
        """
        errors = []

        if not citation_data.get("content"):
            errors.append("Missing required field: content")

        if not citation_data.get("source_title"):
            errors.append("Missing required field: source_title")

        confidence = citation_data.get("confidence", 1.0)
        try:
            confidence_float = float(confidence)
            if confidence_float < 0.0 or confidence_float > 1.0:
                errors.append(f"Invalid confidence score: {
                              confidence_float} (must be 0.0-1.0)")
        except (ValueError, TypeError):
            errors.append(f"Invalid confidence score format: {confidence}")

        page_number = citation_data.get("page_number")
        if page_number is not None:
            try:
                int(page_number)
            except (ValueError, TypeError):
                errors.append(f"Invalid page_number format: {page_number}")

        return errors

    @staticmethod
    def validate_citations_batch(
            citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate a batch of citations and return summary.

        Args:
            citations: List of citation dictionaries

        Returns:
            Validation summary with errors and statistics
        """
        valid_count = 0
        invalid_count = 0
        all_errors = []

        for i, citation in enumerate(citations, 1):
            errors = CitationValidator.validate_citation_data(citation)
            if errors:
                invalid_count += 1
                all_errors.extend(
                    [f"Citation {i}: {error}" for error in errors])
            else:
                valid_count += 1

        return {
            "total": len(citations),
            "valid": valid_count,
            "invalid": invalid_count,
            "errors": all_errors,
            "success_rate": valid_count / len(citations) if citations else 0.0
        }

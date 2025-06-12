"""
Citation Manager - Core business logic for citation operations.
Handles CRUD operations, batch processing, and import/export functionality.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .formatters import CitationFormatter
from .models import Citation
from .validators import CitationValidator

logger = logging.getLogger(__name__)


class CitationManager:
    """
    Citation manager with CRUD operations and batch processing.
    Focuses on internal data management without complex NLP.
    """

    def __init__(self):
        """Initialize with empty citation dictionary."""
        self.citations: Dict[str, Citation] = {}
        self._next_id = 1

    def create_citation(
        self,
        content: str,
        source_title: str,
        case_number: Optional[str] = None,
        page_number: Optional[int] = None,
        confidence: float = 1.0
    ) -> str:
        """
        Create a new citation.

        Args:
            content: The cited content
            source_title: Title of the source document
            case_number: Optional case number
            page_number: Optional page number
            confidence: Confidence score (0.0-1.0)

        Returns:
            str: Citation ID
        """
        citation_id = str(self._next_id)
        self._next_id += 1

        citation = Citation(
            id=citation_id,
            content=content,
            source_title=source_title,
            case_number=case_number,
            page_number=page_number,
            confidence=confidence
        )

        self.citations[citation_id] = citation
        logger.info(f"Created citation {citation_id}: '{
                    source_title}' (confidence: {confidence:.2f})")
        return citation_id

    def create_multiple_citations(
            self, citations_data: List[Dict[str, Any]]) -> List[str]:
        """
        Create multiple citations at once.

        Args:
            citations_data: List of dictionaries containing citation data

        Returns:
            List[str]: List of created citation IDs
        """
        logger.info(f"=== Creating Multiple Citations ===")
        logger.info(
            f"Starting batch creation of {
                len(citations_data)} citations")

        created_ids = []
        successful_count = 0
        failed_count = 0

        for i, citation_data in enumerate(citations_data, 1):
            try:
                # Validate citation data
                validation_errors = CitationValidator.validate_citation_data(
                    citation_data)
                if validation_errors:
                    logger.warning(
                        f"[{i}/{len(citations_data)}] Skipped citation - validation errors: {validation_errors}")
                    failed_count += 1
                    continue

                content = citation_data.get("content", "")
                source_title = citation_data.get("source_title", "")
                case_number = citation_data.get("case_number")
                page_number = citation_data.get("page_number")
                confidence = citation_data.get("confidence", 1.0)

                citation_id = self.create_citation(
                    content=content,
                    source_title=source_title,
                    case_number=case_number,
                    page_number=page_number,
                    confidence=float(confidence) if confidence else 1.0
                )
                created_ids.append(citation_id)
                successful_count += 1
                logger.debug(
                    f"[{i}/{len(citations_data)}] Created citation {citation_id}")

            except Exception as e:
                logger.error(
                    f"[{i}/{len(citations_data)}] Failed to create citation: {e}")
                failed_count += 1

        # Log summary
        logger.info(f"=== Batch Citation Creation Summary ===")
        logger.info(f"Successfully created: {successful_count} citations")
        logger.info(f"Failed: {failed_count} citations")
        logger.info(f"Total citations in registry: {len(self.citations)}")

        return created_ids

    def create_citations_from_search_batch(
        self,
        search_results_list: List[Dict[str, Any]],
        batch_name: str = "batch"
    ) -> List[str]:
        """
        Create citations from a batch of INTERNAL search results only.

        Args:
            search_results_list: List of search result dictionaries (INTERNAL sources only)
            batch_name: Name for the batch (for logging purposes)

        Returns:
            List[str]: List of created citation IDs (internal sources only)
        """
        logger.info(
            f"=== Creating Citations from INTERNAL Search Batch: {batch_name} ===")
        logger.info(
            f"Processing {
                len(search_results_list)} search results (validating internal sources)")

        citations_data = []
        valid_count = 0

        for i, result in enumerate(search_results_list, 1):
            # STRICT VALIDATION: Only process internal AI Search results
            if not CitationValidator.is_valid_internal_source(result):
                logger.warning(
                    f"[{i}/{len(search_results_list)}] Skipped external/invalid source in batch")
                continue

            content = CitationFormatter.extract_content_from_search_result(
                result)
            source_title = CitationFormatter.extract_proper_filename(result)
            case_number = result.get("text_document_id") or result.get(
                "record_id") or result.get("id")
            page_number = result.get("page_number")
            confidence = result.get("score", 1.0)

            if content and source_title:
                citations_data.append({
                    "content": content,
                    "source_title": source_title,
                    "case_number": str(case_number) if case_number else None,
                    "page_number": page_number,
                    "confidence": float(confidence) if confidence else 1.0
                })
                valid_count += 1

        logger.info(
            f"Validated {valid_count} INTERNAL sources from {
                len(search_results_list)} results")

        created_ids = self.create_multiple_citations(citations_data)
        logger.info(
            f"Created {
                len(created_ids)} citations from INTERNAL batch '{batch_name}'")
        logger.info("All citations strictly from internal AI Search sources")
        return created_ids

    def read_citation(self, citation_id: str) -> Optional[Citation]:
        """Read a citation by ID."""
        return self.citations.get(citation_id)

    def update_citation(self, citation_id: str, **updates) -> bool:
        """Update a citation."""
        if citation_id not in self.citations:
            return False

        citation = self.citations[citation_id]
        for field, value in updates.items():
            if hasattr(citation, field):
                setattr(citation, field, value)

        logger.info(f"Updated citation {citation_id}")
        return True

    def delete_citation(self, citation_id: str) -> bool:
        """Delete a citation."""
        if citation_id in self.citations:
            del self.citations[citation_id]
            logger.info(f"Deleted citation {citation_id}")
            return True
        return False

    def list_citations(
            self,
            case_number_filter: Optional[str] = None) -> List[Citation]:
        """List all citations with optional filtering."""
        citations = list(self.citations.values())

        if case_number_filter:
            citations = [
                c for c in citations
                if c.case_number and case_number_filter in c.case_number
            ]

        return citations

    def import_from_search_results(
            self, search_results: Union[str, List[Dict[str, Any]]]) -> int:
        """Import citations from INTERNAL AI Search results ONLY."""
        logger.info("=== Citation Import Starting ===")
        logger.info(
            "Starting citation import from INTERNAL search results only")

        try:
            # Handle both string (JSON) and list inputs
            results = search_results

            logger.info(
                f"Processing {
                    len(results)} search results for citation import")
            imported_count = 0

            for i, result in enumerate(results, 1):
                # STRICT VALIDATION: Only process internal AI Search results
                if not CitationValidator.is_valid_internal_source(result):
                    logger.warning(
                        f"[{i}/{len(results)}] Skipped external/invalid source: {result.get('source', 'unknown')}")
                    continue

                content = CitationFormatter.extract_content_from_search_result(
                    result)
                source_title = CitationFormatter.extract_proper_filename(
                    result)
                case_number = result.get("text_document_id") or result.get(
                    "record_id") or result.get("id")
                page_number = result.get("page_number")
                confidence = result.get("score", 1.0)

                if content and source_title:
                    citation_id = self.create_citation(
                        content=content,
                        source_title=source_title,
                        case_number=str(case_number) if case_number else None,
                        page_number=page_number,
                        confidence=float(confidence) if confidence else 1.0
                    )
                    logger.info(f"[{i}/{len(results)}] Created citation {
                                citation_id} from INTERNAL source: {source_title}")
                    imported_count += 1
                else:
                    logger.warning(
                        f"[{i}/{len(results)}] Skipped result - missing content or source title")

            # Calculate and log summary statistics
            avg_confidence = sum(c.confidence for c in self.citations.values(
            )) / len(self.citations) if self.citations else 0
            logger.info(f"=== Citation Import Summary ===")
            logger.info(
                f"Imported {imported_count} citations from {
                    len(results)} search results")
            logger.info(
                f"All citations are from INTERNAL AI Search sources only")
            logger.info(f"Average confidence score: {avg_confidence:.2f}")
            logger.info(f"Total citations in registry: {len(self.citations)}")

            return imported_count

        except Exception as e:
            logger.error(f"Failed to import search results: {e}")
            return 0

    def export_to_dict(self) -> Dict[str, Any]:
        """Export all citations to dictionary."""
        return {
            "citations": {
                cid: citation.to_dict() for cid,
                citation in self.citations.items()},
            "count": len(
                self.citations),
            "exported_at": datetime.now().isoformat()}

    def import_from_dict(self, data: Dict[str, Any]) -> int:
        """Import citations from dictionary."""
        try:
            citations_data = data.get("citations", {})
            imported_count = 0

            for cid, citation_dict in citations_data.items():
                citation = Citation(**citation_dict)
                self.citations[cid] = citation
                imported_count += 1

                # Update next_id to avoid conflicts
                if int(cid) >= self._next_id:
                    self._next_id = int(cid) + 1

            logger.info(f"Imported {imported_count} citations from dictionary")
            return imported_count

        except Exception as e:
            logger.error(f"Failed to import from dictionary: {e}")
            return 0

    def generate_citation_list(self) -> str:
        """Generate formatted citation list."""
        return CitationFormatter.generate_citation_list(self.citations)

    def clear_all(self) -> int:
        """Clear all citations."""
        count = len(self.citations)
        self.citations.clear()
        self._next_id = 1
        logger.info(f"Cleared {count} citations")
        return count

    def process_citations(
        self,
        report_text: str,
        search_results: Optional[Union[str, List[Dict[str, Any]]]] = None
    ) -> str:
        """Process citations for a complete report."""
        # Import search results if provided (with strict internal validation)
        if search_results:
            count = self.import_from_search_results(search_results)
            logger.info(
                f"Imported {count} new INTERNAL sources for citation processing")

        return CitationFormatter.process_report_citations(
            report_text, self.citations)

    def validate_citations(self) -> List[str]:
        """Validate all citations and return any validation errors."""
        errors = []
        for citation_id, citation in self.citations.items():
            if citation.confidence < 0.0 or citation.confidence > 1.0:
                errors.append(
                    f"Citation {citation_id} has invalid confidence score: {
                        citation.confidence}")

        return errors


# Backward compatibility alias
SimpleCitationManager = CitationManager

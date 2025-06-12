"""
Semantic Kernel plugin for citation management.
Provides kernel functions for citation operations.
"""
import logging
from typing import Annotated, Any, Dict, List, Optional

from semantic_kernel.functions import kernel_function

from .formatters import CitationFormatter
from .manager import CitationManager

logger = logging.getLogger(__name__)


class CitationPlugin:
    """
    Semantic Kernel plugin wrapper for CitationManager.
    Provides kernel functions for citation management.
    """

    def __init__(self):
        """Initialize the plugin."""
        self.manager = CitationManager()

    @kernel_function(
        name="add_citation",
        description="Add a new citation from internal documentation"
    )
    async def add_citation(
        self,
        content: Annotated[str, "The content text being cited from internal documents"],
        source_title: Annotated[str, "The title or filename of the internal source document"],
        case_number: Annotated[str, "Optional case number"] = None,
        page_number: Annotated[str, "Optional page number where the citation is found"] = None
    ) -> Annotated[str, "Success message with citation ID"]:
        """Add a new citation."""
        page_num = int(
            page_number) if page_number and page_number.isdigit() else None
        citation_id = self.manager.create_citation(
            content=content,
            source_title=source_title,
            case_number=case_number,
            page_number=page_num
        )
        return f"Citation {citation_id} created successfully"

    @kernel_function(name="add_multiple_citations",
                     description="Add multiple citations at once from structured citation data")
    async def add_multiple_citations(
        self,
        citations_data: Annotated[List[Dict[str, Any]], "List of citation dictionaries with keys: content, source_title, case_number (optional), page_number (optional), confidence (optional)"]
    ) -> Annotated[str, "Success message with count of created citations"]:
        """Add multiple citations from structured dictionary data."""
        try:
            created_ids = self.manager.create_multiple_citations(
                citations_data)
            return f"Successfully created {
                len(created_ids)} citations: {
                ', '.join(created_ids)}"
        except Exception as e:
            logger.error(f"Failed to create multiple citations: {e}")
            return f"Failed to create citations: {e}"

    @kernel_function(name="create_citations_from_search_batch",
                     description="Create citations from a batch of internal AI search results")
    async def create_citations_from_search_batch(
        self,
        search_results: Annotated[List[Dict[str, Any]], "List of internal AI search result dictionaries containing fields like content_text, document_title, search_type, record_id, etc."],
        batch_name: Annotated[str, "Name identifier for this batch of search results"] = "search_batch"
    ) -> Annotated[str, "Success message with count of created citations from internal sources"]:
        """Create citations from a batch of search results."""
        try:
            created_ids = self.manager.create_citations_from_search_batch(
                search_results, batch_name)
            return f"Successfully created {len(created_ids)} citations from batch '{batch_name}': {
                ', '.join(created_ids[:5])}{'...' if len(created_ids) > 5 else ''}"
        except Exception as e:
            logger.error(f"Failed to create citations from search batch: {e}")
            return f"Failed to create citations from search batch: {e}"

    @kernel_function(name="get_citations",
                     description="Get all citations as formatted list with optional case number filtering")
    async def get_citations(
        self,
        case_filter: Annotated[str, "Optional case number filter to search for specific cases"] = None
    ) -> Annotated[str, "Formatted list of citations matching the filter criteria"]:
        """Get all citations as formatted list."""
        citations = self.manager.list_citations(case_number_filter=case_filter)
        if not citations:
            return "No citations found"

        # Convert to dict format for formatter
        citations_dict = {c.id: c for c in citations}
        return CitationFormatter.format_citation_summary(citations_dict)

    @kernel_function(
        name="import_search_results",
        description="Import citations from internal AI search results"
    )
    async def import_search_results(
        self,
        search_results: Annotated[List[Dict[str, Any]], "List of internal AI search result dictionaries to be imported as citations"]
    ) -> Annotated[str, "Success message with count of imported internal citations"]:
        """Import citations from search results."""
        count = self.manager.import_from_search_results(search_results)
        return f"Imported {count} citations from search results"

    @kernel_function(name="generate_citation_list",
                     description="Generate formatted citation list for reports from internal sources")
    async def generate_citation_list(self) -> Annotated[str, "Formatted citation list containing only internal source references"]:
        """Generate formatted citation list for reports."""
        return self.manager.generate_citation_list()

    @kernel_function(
        name="clear_citations",
        description="Clear all citations"
    )
    async def clear_citations(self) -> str:
        """Clear all citations."""
        count = self.manager.clear_all()
        return f"Cleared {count} citations"

    @kernel_function(name="process_citations",
                     description="Process citations for a complete report with internal search results")
    async def process_citations(
        self,
        report_text: Annotated[str, "The draft report text to process with citations"],
        search_results: Annotated[List[Dict[str, Any]], "Optional list of internal search result dictionaries"] = None
    ) -> Annotated[str, "Report with proper citations and reference section (internal sources only)"]:
        """Process citations for a complete report."""
        return self.manager.process_citations(report_text, search_results)


# Backward compatibility alias
SimpleCitationPlugin = CitationPlugin

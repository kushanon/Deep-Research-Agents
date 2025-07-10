"""
Prompt Manager - Utility for generating dynamic prompts from configuration.
Eliminates hardcoded values in prompt files by using project_config.yaml.
"""
import logging
from typing import Any, Dict, List, Optional

from lib.config.project_config import ProjectConfig

logger = logging.getLogger(__name__)


class PromptManager:
    """Manager for generating dynamic prompts from configuration."""

    def __init__(self, project_config: ProjectConfig = None):
        """Initialize prompt manager with project configuration."""
        self.config = project_config or ProjectConfig()

    def get_company_context(self) -> Dict[str, str]:
        """Get company context for prompts."""
        try:
            # Safe access to company configuration
            company = self.config.company
            if hasattr(company, 'name'):
                company_name = company.name
                company_display_name = company.display_name
                company_language = company.language
            else:
                # Fallback if company is a dict instead of object
                company_name = company.get('name', 'Organization') if isinstance(company, dict) else 'Organization'
                company_display_name = company.get('display_name', 'Organization') if isinstance(company, dict) else 'Organization'
                company_language = company.get('language', 'en') if isinstance(company, dict) else 'en'
            
            return {
                'company_name': company_name,
                'company_display_name': company_display_name,
                'company_language': company_language,
                'document_scope_jp': f"{company_display_name} internal documents",
                'document_scope_en': f"{company_name} internal documents"
            }
        except Exception as e:
            # Fallback with default values
            return {
                'company_name': 'Organization',
                'company_display_name': 'Organization',
                'company_language': 'en',
                'document_scope_jp': 'Organization internal documents',
                'document_scope_en': 'Organization internal documents'
            }

    def get_document_types_section(self) -> str:
        """Generate document types section for prompts."""
        sections = []
        for dt in self.config.document_types:
            section = f"**{dt.display_name}** ({dt.display_name_en})\n"
            section += f"- Index: {dt.index_name}\n"
            section += f"- Key Fields: {', '.join(dt.key_fields)}\n"
            sections.append(section)

        return "\n".join(sections)

    def get_search_functions_section(self) -> str:
        """Generate search functions section for prompts."""
        sections = []

        for name, example in self.config.search_examples.items():
            section = f"✅ **{example.function_name}**: {example.description}\n"
            if example.query_examples:
                examples_str = '", "'.join(example.query_examples)
                section += f"  - Query Examples: \"{examples_str}\"\n"
            sections.append(section)

        return "\n".join(sections)

    def get_domain_concepts_section(self) -> str:
        """Generate domain concepts section for prompts."""
        concepts = []

        for category, terms in self.config.domain_terms.key_concepts.items():
            if terms:
                terms_str = ', '.join([f'"{term}"' for term in terms])
                concepts.append(f"**{category}**: {terms_str}")

        return "**CORE CONCEPT FOCUS**: Use specific terms: " + \
            "; ".join(concepts) if concepts else ""

    def get_credibility_scores_section(self) -> str:
        """Generate credibility scores section for prompts."""
        scores = []
        for level, range_str in self.config.credibility.score_ranges.items():
            scores.append(f"- **{level.title()}**: {range_str}")

        criteria = []
        for criterion, description in self.config.credibility.evaluation_criteria.items():
            criteria.append(
                f"- **{criterion.replace('_', ' ').title()}**: {description}")

        section = "## Credibility Score Standards\n"
        section += "### Score Ranges:\n" + "\n".join(scores) + "\n\n"
        section += "### Evaluation Criteria:\n" + "\n".join(criteria)

        return section

    def get_case_number_format(self) -> str:
        """Get case number format string."""
        return self.config.get_case_number_format()

    def get_record_id_field(self) -> str:
        """Get record ID field name."""
        return self.config.get_record_id_field_name()

    def get_internal_only_requirement(self) -> str:
        """Get internal sources only requirement text."""
        company_context = self.get_company_context()
        return f"**INTERNAL SOURCES ONLY**: All research must be based exclusively on internal {
            company_context['company_name']} documents. NO external information or assumptions permitted."

    def get_citation_requirements(self) -> str:
        """Get citation requirements section."""
        company_context = self.get_company_context()
        return f"""## Citation Requirements
- **Case Number Format**: Use standardized formats ({self.get_record_id_field()} numbers, {self.get_case_number_format()}, etc.)
- **MANDATORY**: Verify all citations reference internal {company_context['company_name']} documentation only
- **Metadata Preservation**: Include document titles, case numbers, {self.get_record_id_field()}
                                                                                                numbers, and other identifying information"""

    def get_search_examples_by_type(
            self, document_type: str) -> Dict[str, Any]:
        """Get search examples for a specific document type."""
        example = self.config.get_search_example(document_type)
        if example:
            return {
                'function_name': example.function_name,
                'description': example.description,
                'query_examples': example.query_examples,
                'parameters': example.parameters
            }
        return {}

    def get_agent_role_description(self, agent_type: str) -> str:
        """Get agent role description based on type and company context."""
        company_context = self.get_company_context()

        role_descriptions = {
            'lead_researcher': f"Expert internal document researcher for {
                company_context['company_name']} utilizing advanced hybrid search and Memory for comprehensive data retrieval from internal repositories.",
            'report_writer': f"Professional research writer creating comprehensive, well-structured R&D reports with confidence assessments, proper citations, and regulatory compliance for internal {
                company_context['company_name']} documentation.",
            'citation': f"Citation Agent responsible for processing research documents and ensuring proper attribution of all claims to internal {
                company_context['company_name']} sources. Primary mission is regulatory compliance through comprehensive citation management.",
            'credibility_critic': f"Expert document analyst specializing in internal source evaluation and verification for {
                company_context['company_name']} research quality assurance.",
            'reflection_critic': f"Expert analysis quality reviewer specializing in internal research evaluation and improvement recommendations for {
                company_context['company_name']} research standards."}

        return role_descriptions.get(
            agent_type, f"Specialized agent for {
                company_context['company_name']} internal research operations.")

    def format_search_instructions(self) -> Dict[str, str]:
        """Get formatted search instructions."""
        company_context = self.get_company_context()

        return {
            'internal_only': f"**INTERNAL FOCUS**: Search exclusively within {
                company_context['company_name']} internal document repositories. NO external source validation or information permitted.",
            'hybrid_search': "**HYBRID SEARCH MANDATORY**: Always use use_hybrid_search=True and use_semantic_search=True for comprehensive coverage",
            'domain_focus': f"**DOMAIN FOCUS**: Utilize technical terminology and {
                company_context['company_language']} language for internal {
                company_context['company_display_name']} documentation"}

    def get_quality_requirements(self) -> List[str]:
        """Get quality requirements list."""
        company_context = self.get_company_context()
        return [
            f"Internal document source verification for {
                company_context['company_name']}",
            "Complete metadata and traceability information",
            "Technical accuracy and consistency standards",
            "Regulatory compliance indicators",
            f"Adherence to {
                company_context['company_name']} documentation standards"]

    def get_search_examples_section(self) -> str:
        """Generate search examples section."""
        sections = []

        # Group examples by category
        category_examples = []
        research_examples = []
        comprehensive_examples = []

        for name, example in self.config.search_examples.items():
            params_str = f"top_k={
                example.parameters.get(
                    'top_k',
                    15)}, use_hybrid_search=True, use_semantic_search=True"
            # Limit to first 2 examples
            example_queries = ', '.join(
                [f'"{q}"' for q in example.query_examples[:2]])

            line = f"- Function: `{
                example.function_name}` - Query examples: {example_queries}"

            # Use generic categorization instead of business-specific keywords
            if any(
                keyword in name for keyword in [
                    'category',
                    'type_a',
                    'type_b']):
                category_examples.append(line)
            elif 'research' in name:
                research_examples.append(line)
            elif 'all' in name:
                comprehensive_examples.append(line)

        if category_examples:
            sections.append(
                "**Category-Related Queries with Semantic Understanding**:")
            sections.extend(category_examples)
            sections.append(f"- Parameters: {params_str}")
            sections.append("")

        if research_examples:
            sections.append(
                "**Research and Knowledge Queries with Conceptual Matching**:")
            sections.extend(research_examples)
            sections.append(f"- Parameters: {params_str}")
            sections.append("")

        if comprehensive_examples:
            sections.append(
                "**Comprehensive Coverage with Hybrid Capabilities**:")
            sections.extend(comprehensive_examples)
            sections.append(f"- Parameters: {params_str}")

        return "\n".join(sections)

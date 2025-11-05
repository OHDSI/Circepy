"""
Markdown rendering for cohort definitions.

This module provides functionality to generate human-readable markdown descriptions
of cohort definitions, mirroring the Java CIRCE-BE MarkdownRender functionality.

GUARD RAIL: This module implements Java CIRCE-BE functionality.
Any changes must maintain 1:1 compatibility with Java classes.
Reference: JAVA_CLASS_MAPPINGS.md for Java equivalents.
"""

from typing import List, Optional, Any, Union
from ..cohort import CohortExpression
from ..criteria import (
    Criteria, CriteriaGroup, DemographicCriteria, InclusionRule,
    ConditionOccurrence, DrugExposure, ProcedureOccurrence, VisitOccurrence,
    Observation, Measurement, DeviceExposure, Specimen, Death, VisitDetail,
    ObservationPeriod, PayerPlanPeriod, LocationRegion, ConditionEra,
    DrugEra, DoseEra, GeoCriteria
)
from ..core import (
    ResultLimit, Period, CollapseSettings, EndStrategy, DateOffsetStrategy,
    CustomEraStrategy, PrimaryCriteria, DateRange, NumericRange,
    ConceptSetSelection, CollapseType, DateType
)
from ...vocabulary.concept import Concept, ConceptSet, ConceptSetExpression, ConceptSetItem


class MarkdownRender:
    """Generates human-readable markdown descriptions of cohort definitions.
    
    Java equivalent: org.ohdsi.circe.cohortdefinition.printfriendly.MarkdownRender
    """
    
    def __init__(self):
        """Initialize the markdown renderer."""
        pass
    
    def render_cohort_expression(self, cohort_expression: CohortExpression) -> str:
        """Render a cohort expression to markdown format.
        
        Args:
            cohort_expression: The cohort expression to render
            
        Returns:
            Markdown formatted string describing the cohort
        """
        if not cohort_expression:
            return "# Invalid Cohort Expression\n\nNo cohort expression provided."
        
        markdown_parts = []
        
        # Title
        title = cohort_expression.title or "Untitled Cohort"
        markdown_parts.append(f"# {title}\n")
        
        # Description section
        markdown_parts.append("## Description\n")
        markdown_parts.append(self._render_description(cohort_expression))
        
        # Primary criteria
        if cohort_expression.primary_criteria:
            markdown_parts.append("## Primary Criteria\n")
            markdown_parts.append(self._render_primary_criteria(cohort_expression.primary_criteria))
        
        # Additional criteria
        if cohort_expression.additional_criteria:
            markdown_parts.append("## Additional Criteria\n")
            markdown_parts.append(self._render_criteria_group(cohort_expression.additional_criteria))
        
        # Inclusion rules
        if cohort_expression.inclusion_rules:
            markdown_parts.append("## Inclusion Rules\n")
            markdown_parts.append(self._render_inclusion_rules(cohort_expression.inclusion_rules))
        
        # End strategy
        if cohort_expression.end_strategy:
            markdown_parts.append("## End Strategy\n")
            markdown_parts.append(self._render_end_strategy(cohort_expression.end_strategy))
        
        # Collapse settings
        if cohort_expression.collapse_settings:
            markdown_parts.append("## Collapse Settings\n")
            markdown_parts.append(self._render_collapse_settings(cohort_expression.collapse_settings))
        
        # Censor window
        if cohort_expression.censor_window:
            markdown_parts.append("## Censor Window\n")
            markdown_parts.append(self._render_period(cohort_expression.censor_window))
        
        # CDM version range
        if cohort_expression.cdm_version_range:
            markdown_parts.append("## CDM Version Range\n")
            markdown_parts.append(self._render_period(cohort_expression.cdm_version_range))
        
        # Concept sets
        if cohort_expression.concept_sets:
            markdown_parts.append("## Concept Sets\n")
            markdown_parts.append(self._render_concept_sets(cohort_expression.concept_sets))
        
        return "\n".join(markdown_parts)
    
    def _render_description(self, cohort_expression: CohortExpression) -> str:
        """Render the description section."""
        description_parts = []
        
        if cohort_expression.title:
            description_parts.append(f"**Title:** {cohort_expression.title}")
        
        # Add any other descriptive information
        description_parts.append("This cohort definition specifies the criteria for identifying patients.")
        
        return "\n".join(description_parts) + "\n"
    
    def _render_primary_criteria(self, primary_criteria: PrimaryCriteria) -> str:
        """Render primary criteria."""
        if not primary_criteria:
            return "No primary criteria specified.\n"
        
        criteria_parts = []
        
        if primary_criteria.criteria_list:
            for i, criteria in enumerate(primary_criteria.criteria_list, 1):
                criteria_parts.append(f"### Primary Criteria {i}\n")
                criteria_parts.append(self._render_criteria(criteria))
                criteria_parts.append("")
        
        return "\n".join(criteria_parts)
    
    def _render_criteria_group(self, criteria_group: CriteriaGroup) -> str:
        """Render a criteria group."""
        if not criteria_group:
            return "No criteria group specified.\n"
        
        group_parts = []
        
        # Group type
        if criteria_group.type:
            group_parts.append(f"**Group Type:** {criteria_group.type}")
        
        # Demographics
        if criteria_group.demographic_criteria:
            group_parts.append("### Demographic Criteria")
            group_parts.append(self._render_demographic_criteria(criteria_group.demographic_criteria))
        
        # Criteria list
        if criteria_group.criteria_list:
            group_parts.append("### Criteria")
            for i, criteria in enumerate(criteria_group.criteria_list, 1):
                group_parts.append(f"#### Criteria {i}")
                group_parts.append(self._render_criteria(criteria))
                group_parts.append("")
        
        # Groups
        if criteria_group.groups:
            group_parts.append("### Sub-groups")
            for i, sub_group in enumerate(criteria_group.groups, 1):
                group_parts.append(f"#### Sub-group {i}")
                group_parts.append(self._render_criteria_group(sub_group))
                group_parts.append("")
        
        return "\n".join(group_parts)
    
    def _render_criteria(self, criteria: Criteria) -> str:
        """Render individual criteria."""
        if not criteria:
            return "No criteria specified.\n"
        
        criteria_parts = []
        
        # Include flag
        if criteria.include:
            criteria_parts.append(f"**Include:** {criteria.include}")
        
        # Date adjustment
        if criteria.date_adjustment:
            criteria_parts.append("**Date Adjustment:**")
            criteria_parts.append(self._render_date_adjustment(criteria.date_adjustment))
        
        # Correlated criteria
        if criteria.correlated_criteria:
            criteria_parts.append("**Correlated Criteria:**")
            criteria_parts.append(self._render_criteria_group(criteria.correlated_criteria))
        
        return "\n".join(criteria_parts) if criteria_parts else "No criteria details specified.\n"
    
    def _render_demographic_criteria(self, demographic_criteria: DemographicCriteria) -> str:
        """Render demographic criteria."""
        if not demographic_criteria:
            return "No demographic criteria specified.\n"
        
        demo_parts = []
        
        # Age
        if demographic_criteria.age:
            demo_parts.append(f"**Age:** {self._render_numeric_range(demographic_criteria.age)}")
        
        # Gender
        if demographic_criteria.gender:
            demo_parts.append(f"**Gender:** {', '.join([str(g) for g in demographic_criteria.gender])}")
        
        # Race
        if demographic_criteria.race:
            demo_parts.append(f"**Race:** {', '.join([str(r) for r in demographic_criteria.race])}")
        
        # Ethnicity
        if demographic_criteria.ethnicity:
            demo_parts.append(f"**Ethnicity:** {', '.join([str(e) for e in demographic_criteria.ethnicity])}")
        
        # Occurrence dates
        if demographic_criteria.occurrence_start_date:
            demo_parts.append(f"**Occurrence Start Date:** {self._render_date_range(demographic_criteria.occurrence_start_date)}")
        
        if demographic_criteria.occurrence_end_date:
            demo_parts.append(f"**Occurrence End Date:** {self._render_date_range(demographic_criteria.occurrence_end_date)}")
        
        return "\n".join(demo_parts) + "\n" if demo_parts else "No demographic criteria specified.\n"
    
    def _render_inclusion_rules(self, inclusion_rules: List[InclusionRule]) -> str:
        """Render inclusion rules."""
        if not inclusion_rules:
            return "No inclusion rules specified.\n"
        
        rules_parts = []
        
        for i, rule in enumerate(inclusion_rules, 1):
            rules_parts.append(f"### Inclusion Rule {i}")
            
            if rule.name:
                rules_parts.append(f"**Name:** {rule.name}")
            
            if rule.description:
                rules_parts.append(f"**Description:** {rule.description}")
            
            if rule.expression:
                rules_parts.append("**Expression:**")
                rules_parts.append(self._render_criteria_group(rule.expression))
            
            rules_parts.append("")
        
        return "\n".join(rules_parts)
    
    def _render_end_strategy(self, end_strategy: Union[EndStrategy, DateOffsetStrategy, CustomEraStrategy]) -> str:
        """Render end strategy."""
        if not end_strategy:
            return "No end strategy specified.\n"
        
        strategy_parts = []
        
        if isinstance(end_strategy, EndStrategy):
            strategy_parts.append(f"**Strategy Type:** End Strategy")
            if end_strategy.date_offset:
                strategy_parts.append(f"**Date Offset:** {end_strategy.date_offset}")
        
        elif isinstance(end_strategy, DateOffsetStrategy):
            strategy_parts.append(f"**Strategy Type:** Date Offset Strategy")
            if end_strategy.date_offset:
                strategy_parts.append(f"**Date Offset:** {end_strategy.date_offset}")
        
        elif isinstance(end_strategy, CustomEraStrategy):
            strategy_parts.append(f"**Strategy Type:** Custom Era Strategy")
            if end_strategy.drug_era_criteria:
                strategy_parts.append("**Drug Era Criteria:**")
                strategy_parts.append(self._render_criteria(end_strategy.drug_era_criteria))
        
        return "\n".join(strategy_parts) + "\n"
    
    def _render_collapse_settings(self, collapse_settings: CollapseSettings) -> str:
        """Render collapse settings."""
        if not collapse_settings:
            return "No collapse settings specified.\n"
        
        collapse_parts = []
        
        if collapse_settings.collapse_type:
            collapse_parts.append(f"**Collapse Type:** {collapse_settings.collapse_type}")
        
        if collapse_settings.era_pad:
            collapse_parts.append(f"**Era Pad:** {collapse_settings.era_pad}")
        
        return "\n".join(collapse_parts) + "\n"
    
    def _render_period(self, period: Period) -> str:
        """Render a period."""
        if not period:
            return "No period specified.\n"
        
        period_parts = []
        
        if period.start_date:
            period_parts.append(f"**Start Date:** {period.start_date}")
        
        if period.end_date:
            period_parts.append(f"**End Date:** {period.end_date}")
        
        return "\n".join(period_parts) + "\n"
    
    def _render_date_range(self, date_range: DateRange) -> str:
        """Render a date range."""
        if not date_range:
            return "No date range specified"
        
        range_parts = []
        
        if date_range.operation:
            range_parts.append(f"Operation: {date_range.operation}")
        
        if date_range.extent:
            range_parts.append(f"Extent: {date_range.extent}")
        
        if date_range.value:
            range_parts.append(f"Value: {date_range.value}")
        
        return ", ".join(range_parts) if range_parts else "No date range details"
    
    def _render_numeric_range(self, numeric_range: NumericRange) -> str:
        """Render a numeric range."""
        if not numeric_range:
            return "No numeric range specified"
        
        range_parts = []
        
        if numeric_range.operation:
            range_parts.append(f"Operation: {numeric_range.operation}")
        
        if numeric_range.value:
            range_parts.append(f"Value: {numeric_range.value}")
        
        if numeric_range.extent:
            range_parts.append(f"Extent: {numeric_range.extent}")
        
        return ", ".join(range_parts) if range_parts else "No numeric range details"
    
    def _render_date_adjustment(self, date_adjustment: Any) -> str:
        """Render date adjustment."""
        if not date_adjustment:
            return "No date adjustment specified"
        
        # This would need to be implemented based on the actual DateAdjustment structure
        return "Date adjustment details"
    
    def _render_concept_sets(self, concept_sets: List[Any]) -> str:
        """Render concept sets."""
        if not concept_sets:
            return "No concept sets specified.\n"
        
        concept_parts = []
        
        for i, concept_set in enumerate(concept_sets, 1):
            concept_parts.append(f"### Concept Set {i}")
            
            if hasattr(concept_set, 'id') and concept_set.id:
                concept_parts.append(f"**ID:** {concept_set.id}")
            
            if hasattr(concept_set, 'name') and concept_set.name:
                concept_parts.append(f"**Name:** {concept_set.name}")
            
            if hasattr(concept_set, 'expression') and concept_set.expression:
                concept_parts.append("**Expression:**")
                concept_parts.append(self._render_concept_set_expression(concept_set.expression))
            
            concept_parts.append("")
        
        return "\n".join(concept_parts)
    
    def _render_concept_set_expression(self, expression: ConceptSetExpression) -> str:
        """Render a concept set expression."""
        if not expression:
            return "No concept set expression specified.\n"
        
        expr_parts = []
        
        if expression.items:
            expr_parts.append("**Items:**")
            for item in expression.items:
                expr_parts.append(f"- {self._render_concept_set_item(item)}")
        
        return "\n".join(expr_parts) + "\n"
    
    def _render_concept_set_item(self, item: ConceptSetItem) -> str:
        """Render a concept set item."""
        if not item:
            return "No concept set item specified"
        
        item_parts = []
        
        if hasattr(item, 'concept') and item.concept:
            item_parts.append(f"Concept: {item.concept}")
        
        if hasattr(item, 'is_excluded') and item.is_excluded:
            item_parts.append("(Excluded)")
        
        return " ".join(item_parts) if item_parts else "No concept set item details"


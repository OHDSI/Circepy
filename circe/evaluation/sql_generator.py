import os
from typing import List, Optional, Any, Dict
from jinja2 import Environment, FileSystemLoader
from .models import EvaluationRule, EvaluationRubric

# Mapping from domain to CDM table and date column
DOMAIN_CONFIG = {
    "condition_occurrence": {
        "table": "condition_occurrence",
        "concept_column": "condition_concept_id",
        "date_column": "condition_start_date",
        "person_column": "person_id",
    },
    "procedure_occurrence": {
        "table": "procedure_occurrence",
        "concept_column": "procedure_concept_id",
        "date_column": "procedure_date",
        "person_column": "person_id",
    },
    "drug_exposure": {
        "table": "drug_exposure",
        "concept_column": "drug_concept_id",
        "date_column": "drug_exposure_start_date",
        "person_column": "person_id",
    },
    "measurement": {
        "table": "measurement",
        "concept_column": "measurement_concept_id",
        "date_column": "measurement_date",
        "person_column": "person_id",
        "value_column": "value_as_number",
    },
    "observation": {
        "table": "observation",
        "concept_column": "observation_concept_id",
        "date_column": "observation_date",
        "person_column": "person_id",
    },
    "visit_occurrence": {
        "table": "visit_occurrence",
        "concept_column": "visit_concept_id",
        "date_column": "visit_start_date",
        "person_column": "person_id",
    },
    "device_exposure": {
        "table": "device_exposure",
        "concept_column": "device_concept_id",
        "date_column": "device_exposure_start_date",
        "person_column": "person_id",
    },
}

# SQL comparison operators
VALUE_OPERATORS = {
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
    "eq": "=",
}


class RubricSqlGenerator:
    """Generates T-SQL for evaluating rubric rules against a cohort using Jinja2 templates.
    
    Output SQL uses @parameter placeholders compatible with SQLRender.
    """
    
    def __init__(self, rubric: EvaluationRubric):
        self.rubric = rubric
        
        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    
    def generate_evaluation_sql(
        self, 
        include_aggregation: bool = False,
        top_n: bool = False
    ) -> str:
        """Generate T-SQL for evaluating all rules in the rubric.
        
        Args:
            include_aggregation: If True, include aggregation query at the end
            top_n: If True, include @top_n sampling logic
            
        Returns:
            T-SQL string with @parameter placeholders
        """
        if not self.rubric.rules:
            raise ValueError("Rubric has no rules to evaluate")
            
        template = self.env.get_template("evaluation_sql.j2")
        
        return template.render(
            rubric=self.rubric,
            domains=DOMAIN_CONFIG,
            operators=VALUE_OPERATORS,
            include_aggregation=include_aggregation,
            top_n=top_n
        )
    
    def generate_rule_metadata_sql(self) -> str:
        """Generate SQL to insert rule metadata into a reference table."""
        lines = [
            "-- Rule metadata for reference",
            "-- INSERT INTO rule_metadata (ruleset_id, rule_id, name, description, weight)",
            "-- VALUES",
        ]
        
        values = []
        for rule in self.rubric.rules:
            desc = (rule.description or "").replace("'", "''")[:200]
            values.append(
                f"--     ({self.rubric.ruleset_id}, {rule.rule_id}, "
                f"'{rule.name}', '{desc}', {rule.weight})"
            )
        
        lines.extend(values)
        lines.append("--;")
        return "\n".join(lines)

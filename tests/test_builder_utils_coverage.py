"""
Additional tests to increase coverage for builder utility functions.
"""

from circe.cohortdefinition.builders.utils import (
    BuilderOptions,
    BuilderUtils,
    CriteriaColumn,
)
from circe.cohortdefinition.core import DateAdjustment, DateRange, NumericRange
from circe.vocabulary.concept import Concept


class TestBuilderUtilsNumericRanges:
    """Test numeric range clause building."""
    
    def test_numeric_range_between_uses_and(self):
        """Test bt operator uses >= and <=."""
        range_val = NumericRange(op="bt", value=10, extent=20)
        # Integer range (no format)
        clause = BuilderUtils.build_numeric_range_clause("age", range_val)
        assert "age >= 10" in clause and "age <= 20" in clause
        
        # Double range (with format)
        clause_decimal = BuilderUtils.build_numeric_range_clause("age", range_val, format=".4f")
        assert "age >= 10.0000" in clause_decimal and "age <= 20.0000" in clause_decimal
    
    def test_numeric_range_greater_than(self):
        """Test > operator."""
        range_val = NumericRange(op="gt", value=18)
        clause = BuilderUtils.build_numeric_range_clause("age", range_val)
        assert ">" in clause
        assert "18" in clause
    
    def test_numeric_range_greater_equal(self):
        """Test >= operator."""
        range_val = NumericRange(op="gte", value=18)
        clause = BuilderUtils.build_numeric_range_clause("age", range_val)
        assert ">=" in clause
    
    def test_numeric_range_less_than(self):
        """Test < operator."""
        range_val = NumericRange(op="lt", value=65)
        clause = BuilderUtils.build_numeric_range_clause("age", range_val)
        assert "<" in clause

    def test_numeric_range_less_equal(self):
        """Test <= operator."""
        range_val = NumericRange(op="lte", value=65)
        clause = BuilderUtils.build_numeric_range_clause("age", range_val)
        assert "<=" in clause

    def test_numeric_range_equal(self):
        """Test = operator."""
        range_val = NumericRange(op="eq", value=50)
        clause = BuilderUtils.build_numeric_range_clause("age", range_val)
        assert "=" in clause
        assert "50" in clause

    def test_numeric_range_not_equal(self):
        """Test != operator translates to <>."""
        range_val = NumericRange(op="!eq", value=50)
        clause = BuilderUtils.build_numeric_range_clause("age", range_val)
        assert "<>" in clause
    
    def test_numeric_range_none(self):
        """Test None range returns None."""
        clause = BuilderUtils.build_numeric_range_clause("age", None)
        assert clause is None


class TestBuilderUtilsDateRanges:
    """Test date range clause building."""
    
    def test_date_range_simple(self):
        """Test simple date range."""
        range_val = DateRange(op="gt", value="2020-01-01")
        clause = BuilderUtils.build_date_range_clause("start_date", range_val)
        assert clause == "start_date > DATEFROMPARTS(2020, 1, 1)"
    
    def test_date_range_between(self):
        """Test between date range."""
        range_val = DateRange(op="bt", value="2020-01-01", extent="2020-12-31")
        clause = BuilderUtils.build_date_range_clause("start_date", range_val)
        assert clause == "(start_date >= DATEFROMPARTS(2020, 1, 1) and start_date <= DATEFROMPARTS(2020, 12, 31))"

    def test_date_range_not_between(self):
        """Test not between date range."""
        range_val = DateRange(op="!bt", value="2020-01-01", extent="2020-12-31")
        clause = BuilderUtils.build_date_range_clause("start_date", range_val)
        assert clause == "not (start_date >= DATEFROMPARTS(2020, 1, 1) and start_date <= DATEFROMPARTS(2020, 12, 31))"
    
    def test_date_range_none(self):
        """Test None date range returns None."""
        clause = BuilderUtils.build_date_range_clause("start_date", None)
        assert clause is None


class TestBuilderUtilsDateAdjustment:
    """Test date adjustment expression building."""
    
    def test_date_adjustment_basic(self):
        """Test basic date adjustment."""
        adjustment = DateAdjustment(
            start_with="start_date",
            start_offset=0,
            end_with="start_date",
            end_offset=30
        )
        expr = BuilderUtils.get_date_adjustment_expression(
            adjustment,
            "drug_exposure_start_date",
            "drug_exposure_end_date"
        )
        assert "DATEADD" in expr
        assert "30" in expr
    
    def test_date_adjustment_negative_offset(self):
        """Test date adjustment with negative offset."""
        adjustment = DateAdjustment(
            start_with="start_date",
            start_offset=-7,
            end_with="start_date",
            end_offset=0
        )
        expr = BuilderUtils.get_date_adjustment_expression(
            adjustment,
            "drug_exposure_start_date",
            "drug_exposure_end_date"
        )
        assert "DATEADD" in expr
        assert "-7" in expr


class TestBuilderUtilsCodesets:
    """Test codeset-related utility functions."""
    
    def test_get_concept_ids_from_concepts(self):
        """Test extracting concept IDs from concept list."""
        concepts = [
            Concept(concept_id=123, concept_name="Test1"),
            Concept(concept_id=456, concept_name="Test2"),
            Concept(concept_id=789, concept_name="Test3")
        ]
        ids = BuilderUtils.get_concept_ids_from_concepts(concepts)
        assert 123 in ids
        assert 456 in ids
        assert 789 in ids
        assert len(ids) == 3
    
    def test_get_concept_ids_empty_list(self):
        """Test with empty concept list."""
        ids = BuilderUtils.get_concept_ids_from_concepts([])
        assert ids == []
    
    def test_get_codeset_in_expression(self):
        """Test codeset IN expression generation."""
        expr = BuilderUtils.get_codeset_in_expression(5, "drug_concept_id")
        assert "drug_concept_id" in expr
        assert "5" in expr
    
    def test_get_codeset_in_expression_with_exclusion(self):
        """Test codeset NOT IN expression generation."""
        expr = BuilderUtils.get_codeset_in_expression(5, "drug_concept_id", is_exclusion=True)
        assert "drug_concept_id" in expr
        assert "not" in expr.lower()
    
    def test_get_codeset_join_expression_standard_only(self):
        """Test codeset join with standard codeset only."""
        expr = BuilderUtils.get_codeset_join_expression(
            standard_codeset_id=10,
            standard_concept_column="de.drug_concept_id",
            source_codeset_id=None,
            source_concept_column="de.drug_source_concept_id"
        )
        assert "JOIN" in expr
        assert "10" in expr
    
    def test_get_codeset_join_expression_with_source(self):
        """Test codeset join with both standard and source."""
        expr = BuilderUtils.get_codeset_join_expression(
            standard_codeset_id=10,
            standard_concept_column="de.drug_concept_id",
            source_codeset_id=11,
            source_concept_column="de.drug_source_concept_id"
        )
        assert "JOIN" in expr
        assert "10" in expr
        assert "11" in expr


class TestBuilderUtilsOther:
    """Test other utility functions."""
    
    def test_split_in_clause_small(self):
        """Test split IN clause with small list."""
        values = [1, 2, 3, 4, 5]
        result = BuilderUtils.split_in_clause("concept_id", values)
        assert result == "(concept_id in (1,2,3,4,5))"
    
    def test_split_in_clause_empty(self):
        """Test split IN clause with empty list."""
        result = BuilderUtils.split_in_clause("concept_id", [])
        assert result == "NULL"
    
    def test_date_string_to_sql(self):
        """Test date string to SQL conversion."""
        result = BuilderUtils.date_string_to_sql("2020-01-01")
        assert result == "DATEFROMPARTS(2020, 1, 1)"


class TestBuilderOptions:
    """Test BuilderOptions class."""
    
    def test_builder_options_init(self):
        """Test BuilderOptions initialization."""
        options = BuilderOptions()
        assert hasattr(options, 'additional_columns')
        assert isinstance(options.additional_columns, list)


class TestCriteriaColumn:
    """Test CriteriaColumn enum."""
    
    def test_criteria_column_values(self):
        """Test that CriteriaColumn enum has expected values."""
        assert hasattr(CriteriaColumn, 'START_DATE')
        assert hasattr(CriteriaColumn, 'END_DATE')
        assert hasattr(CriteriaColumn, 'DOMAIN_CONCEPT')
        assert hasattr(CriteriaColumn, 'VISIT_ID')
        assert hasattr(CriteriaColumn, 'DURATION')
        assert hasattr(CriteriaColumn, 'DAYS_SUPPLY')
        assert hasattr(CriteriaColumn, 'QUANTITY')
        assert hasattr(CriteriaColumn, 'REFILLS')

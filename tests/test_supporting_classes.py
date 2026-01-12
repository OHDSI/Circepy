"""
Tests for Supporting Classes

This module contains comprehensive tests for all the supporting classes
that were recently implemented.
"""

import unittest
import sys
import os
from typing import List, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from circe.cohortdefinition.core import (
    ResultLimit, Period, CollapseSettings, EndStrategy, DateOffsetStrategy,
    CustomEraStrategy, DateRange, NumericRange,
    ConceptSetSelection, CollapseType, DateType, TextFilter, Window, WindowBound,
    DateAdjustment
)
from circe.cohortdefinition.criteria import WindowedCriteria, ConditionOccurrence


class TestTextFilter(unittest.TestCase):
    """Test TextFilter class."""

    def test_text_filter_initialization(self):
        """Test basic initialization of TextFilter."""
        text_filter = TextFilter()
        self.assertIsNone(text_filter.text)
        self.assertIsNone(text_filter.op)

    def test_text_filter_with_fields(self):
        """Test TextFilter with fields populated."""
        text_filter = TextFilter(
            text="completed",
            op="eq"
        )
        self.assertEqual(text_filter.text, "completed")
        self.assertEqual(text_filter.op, "eq")

    def test_text_filter_empty_string(self):
        """Test TextFilter with empty string."""
        text_filter = TextFilter(
            text="",
            op="ne"
        )
        self.assertEqual(text_filter.text, "")
        self.assertEqual(text_filter.op, "ne")

    def test_text_filter_unicode_text(self):
        """Test TextFilter with unicode text."""
        text_filter = TextFilter(
            text="café",
            op="like"
        )
        self.assertEqual(text_filter.text, "café")
        self.assertEqual(text_filter.op, "like")


class TestWindowBound(unittest.TestCase):
    """Test WindowBound class."""

    def test_window_bound_initialization(self):
        """Test basic initialization of WindowBound."""
        window_bound = WindowBound(coeff=1)
        self.assertEqual(window_bound.coeff, 1)
        self.assertIsNone(window_bound.days)

    def test_window_bound_with_days(self):
        """Test WindowBound with days populated."""
        window_bound = WindowBound(
            coeff=1,
            days=30
        )
        self.assertEqual(window_bound.coeff, 1)
        self.assertEqual(window_bound.days, 30)

    def test_window_bound_negative_coeff(self):
        """Test WindowBound with negative coefficient."""
        window_bound = WindowBound(
            coeff=-1,
            days=7
        )
        self.assertEqual(window_bound.coeff, -1)
        self.assertEqual(window_bound.days, 7)

    def test_window_bound_zero_coeff(self):
        """Test WindowBound with zero coefficient."""
        window_bound = WindowBound(
            coeff=0,
            days=0
        )
        self.assertEqual(window_bound.coeff, 0)
        self.assertEqual(window_bound.days, 0)


class TestWindow(unittest.TestCase):
    """Test Window class."""

    def test_window_initialization(self):
        """Test basic initialization of Window."""
        window = Window(
            use_event_end=True
        )
        self.assertTrue(window.use_event_end)
        self.assertFalse(window.use_index_end)
        self.assertIsNone(window.start)
        self.assertIsNone(window.end)

    def test_window_with_all_fields(self):
        """Test Window with all fields populated."""
        start_bound = WindowBound(coeff=1, days=30)
        end_bound = WindowBound(coeff=-1, days=7)
        
        window = Window(
            use_event_end=True,
            use_index_end=False,
            start=start_bound,
            end=end_bound
        )
        
        self.assertTrue(window.use_event_end)
        self.assertFalse(window.use_index_end)
        self.assertEqual(window.start.coeff, 1)
        self.assertEqual(window.start.days, 30)
        self.assertEqual(window.end.coeff, -1)
        self.assertEqual(window.end.days, 7)

    def test_window_camel_case_aliases(self):
        """Test that camelCase aliases work correctly."""
        window = Window.model_validate({
            "useEventEnd": True,
            "start": {"coeff": -1, "days": 0},
            "end": {"coeff": 1, "days": 30}
        })
        
        self.assertTrue(window.use_event_end)
        self.assertEqual(window.start.coeff, -1)
        self.assertEqual(window.start.days, 0)
        self.assertEqual(window.end.coeff, 1)
        self.assertEqual(window.end.days, 30)

    def test_window_use_event_end_false(self):
        """Test Window with use_event_end=False."""
        window = Window(
            use_event_end=False,
            start=WindowBound(coeff=-1),
            end=WindowBound(coeff=1)
        )
        self.assertFalse(window.use_event_end)
        self.assertEqual(window.start.coeff, -1)
        self.assertEqual(window.end.coeff, 1)


class TestWindowedCriteria(unittest.TestCase):
    """Test WindowedCriteria class."""

    def test_windowed_criteria_initialization(self):
        """Test basic initialization of WindowedCriteria."""
        windowed_criteria = WindowedCriteria(criteria=ConditionOccurrence())
        self.assertTrue(isinstance(windowed_criteria.criteria, ConditionOccurrence))
        self.assertIsNone(windowed_criteria.start_window)
        self.assertIsNone(windowed_criteria.end_window)

    def test_windowed_criteria_with_windows(self):
        """Test WindowedCriteria with windows populated."""
        start_window = Window(
            use_event_end=True,
            start=WindowBound(coeff=-1, days=0),
            end=WindowBound(coeff=1, days=30)
        )
        end_window = Window(
            use_event_end=False,
            start=WindowBound(coeff=-1, days=7),
            end=WindowBound(coeff=1, days=14)
        )
        
        windowed_criteria = WindowedCriteria(
            criteria=ConditionOccurrence(),
            start_window=start_window,
            end_window=end_window
        )
        
        self.assertTrue(isinstance(windowed_criteria.criteria, ConditionOccurrence))
        self.assertEqual(windowed_criteria.start_window.end.coeff, 1)
        self.assertEqual(windowed_criteria.start_window.end.days, 30)
        self.assertEqual(windowed_criteria.end_window.start.coeff, -1)
        self.assertEqual(windowed_criteria.end_window.start.days, 7)

    def test_windowed_criteria_camel_case_aliases(self):
        """Test that camelCase aliases work correctly."""
        windowed_criteria = WindowedCriteria.model_validate({
            "Criteria": {"ConditionOccurrence": {}},
            "StartWindow": {
                "useEventEnd": True,
                "start": {"coeff": -1, "days": 0},
                "end": {"coeff": 1, "days": 30}
            },
            "EndWindow": {
                "useEventEnd": False,
                "start": {"coeff": -1, "days": 7},
                "end": {"coeff": 1, "days": 14}
            }
        })
        
        self.assertTrue(isinstance(windowed_criteria.criteria, ConditionOccurrence))
        self.assertIsNotNone(windowed_criteria.start_window)
        self.assertIsNotNone(windowed_criteria.end_window)
        self.assertTrue(windowed_criteria.start_window.use_event_end)
        self.assertFalse(windowed_criteria.end_window.use_event_end)
        self.assertEqual(windowed_criteria.start_window.end.coeff, 1)
        self.assertEqual(windowed_criteria.end_window.start.coeff, -1)


class TestDateOffsetStrategy(unittest.TestCase):
    """Test DateOffsetStrategy class."""

    def test_date_offset_strategy_initialization(self):
        """Test basic initialization of DateOffsetStrategy."""
        strategy = DateOffsetStrategy(
            offset=30,
            date_field="start_date"
        )
        self.assertEqual(strategy.offset, 30)
        self.assertEqual(strategy.date_field, "start_date")

    def test_date_offset_strategy_negative_offset(self):
        """Test DateOffsetStrategy with negative offset."""
        strategy = DateOffsetStrategy(
            offset=-7,
            date_field="end_date"
        )
        self.assertEqual(strategy.offset, -7)
        self.assertEqual(strategy.date_field, "end_date")

    def test_date_offset_strategy_zero_offset(self):
        """Test DateOffsetStrategy with zero offset."""
        strategy = DateOffsetStrategy(
            offset=0,
            date_field="event_date"
        )
        self.assertEqual(strategy.offset, 0)
        self.assertEqual(strategy.date_field, "event_date")

    def test_date_offset_strategy_camel_case_aliases(self):
        """Test that camelCase aliases work correctly."""
        strategy = DateOffsetStrategy.model_validate({
            "offset": 30,
            "dateField": "start_date"
        })
        
        self.assertEqual(strategy.offset, 30)
        self.assertEqual(strategy.date_field, "start_date")

    def test_date_offset_strategy_different_date_fields(self):
        """Test DateOffsetStrategy with different date fields."""
        fields = ["start_date", "end_date", "event_date", "observation_date"]
        
        for field in fields:
            strategy = DateOffsetStrategy(
                offset=15,
                date_field=field
            )
            self.assertEqual(strategy.offset, 15)
            self.assertEqual(strategy.date_field, field)


class TestCustomEraStrategy(unittest.TestCase):
    """Test CustomEraStrategy class."""

    def test_custom_era_strategy_initialization(self):
        """Test basic initialization of CustomEraStrategy."""
        strategy = CustomEraStrategy(
            gap_days=30,
            offset=0
        )
        self.assertIsNone(strategy.drug_codeset_id)
        self.assertEqual(strategy.gap_days, 30)
        self.assertEqual(strategy.offset, 0)

    def test_custom_era_strategy_with_drug_codeset(self):
        """Test CustomEraStrategy with drug codeset ID."""
        strategy = CustomEraStrategy(
            drug_codeset_id=12345,
            gap_days=30,
            offset=0
        )
        self.assertEqual(strategy.drug_codeset_id, 12345)
        self.assertEqual(strategy.gap_days, 30)
        self.assertEqual(strategy.offset, 0)

    def test_custom_era_strategy_different_gap_days(self):
        """Test CustomEraStrategy with different gap days."""
        gap_days_values = [0, 7, 14, 30, 60, 90]
        
        for gap_days in gap_days_values:
            strategy = CustomEraStrategy(
                gap_days=gap_days,
                offset=0
            )
            self.assertEqual(strategy.gap_days, gap_days)
            self.assertEqual(strategy.offset, 0)

    def test_custom_era_strategy_different_offsets(self):
        """Test CustomEraStrategy with different offsets."""
        offset_values = [-30, -7, 0, 7, 30]
        
        for offset in offset_values:
            strategy = CustomEraStrategy(
                gap_days=30,
                offset=offset
            )
            self.assertEqual(strategy.gap_days, 30)
            self.assertEqual(strategy.offset, offset)

    def test_custom_era_strategy_camel_case_aliases(self):
        """Test that camelCase aliases work correctly."""
        strategy = CustomEraStrategy.model_validate({
            "drugCodesetId": 12345,
            "gapDays": 30,
            "offset": 0
        })
        
        self.assertEqual(strategy.drug_codeset_id, 12345)
        self.assertEqual(strategy.gap_days, 30)
        self.assertEqual(strategy.offset, 0)

    def test_custom_era_strategy_edge_cases(self):
        """Test CustomEraStrategy with edge case values."""
        # Test with maximum values
        strategy = CustomEraStrategy(
            drug_codeset_id=999999,
            gap_days=365,
            offset=365
        )
        self.assertEqual(strategy.drug_codeset_id, 999999)
        self.assertEqual(strategy.gap_days, 365)
        self.assertEqual(strategy.offset, 365)
        
        # Test with minimum values
        strategy = CustomEraStrategy(
            drug_codeset_id=1,
            gap_days=0,
            offset=-365
        )
        self.assertEqual(strategy.drug_codeset_id, 1)
        self.assertEqual(strategy.gap_days, 0)
        self.assertEqual(strategy.offset, -365)


class TestSupportingClassesIntegration(unittest.TestCase):
    """Test integration between supporting classes."""

    def test_window_with_window_bound_integration(self):
        """Test Window integration with WindowBound."""
        start_bound = WindowBound(coeff=1, days=30)
        end_bound = WindowBound(coeff=-1, days=7)
        
        window = Window(
            use_event_end=True,
            start=start_bound,
            coeff=1,
            days=30,
            end=end_bound
        )
        
        # Test that the bounds are properly integrated
        self.assertEqual(window.start.coeff, 1)
        self.assertEqual(window.start.days, 30)
        self.assertEqual(window.end.coeff, -1)
        self.assertEqual(window.end.days, 7)

    def test_windowed_criteria_with_window_integration(self):
        """Test WindowedCriteria integration with Window."""
        start_window = Window(
            use_event_end=True,
            start=WindowBound(coeff=-1, days=0),
            end=WindowBound(coeff=1, days=30)
        )
        end_window = Window(
            use_event_end=False,
            start=WindowBound(coeff=-1, days=7),
            end=WindowBound(coeff=1, days=14)
        )
        
        windowed_criteria = WindowedCriteria(
            criteria=ConditionOccurrence(),
            start_window=start_window,
            end_window=end_window
        )
        
        # Test that the windows are properly integrated
        self.assertEqual(windowed_criteria.start_window.end.coeff, 1)
        self.assertEqual(windowed_criteria.start_window.end.days, 30)
        self.assertEqual(windowed_criteria.end_window.start.coeff, -1)
        self.assertEqual(windowed_criteria.end_window.start.days, 7)

    def test_text_filter_with_criteria_integration(self):
        """Test TextFilter integration with criteria classes."""
        from circe.cohortdefinition.criteria import ConditionOccurrence
        
        text_filter = TextFilter(text="completed", op="eq")
        
        condition = ConditionOccurrence(
            stop_reason=text_filter,
            first=True,
            condition_type_exclude=False
        )
        
        # Test that the text filter is properly integrated
        self.assertEqual(condition.stop_reason.text, "completed")
        self.assertEqual(condition.stop_reason.op, "eq")

    def test_all_supporting_classes_importable(self):
        """Test that all supporting classes can be imported."""
        from circe.cohortdefinition.core import (
            TextFilter, WindowBound, Window,
            DateOffsetStrategy, CustomEraStrategy
        )
        from circe.cohortdefinition.criteria import WindowedCriteria
        
        # Test that all classes are importable
        self.assertTrue(TextFilter is not None)
        self.assertTrue(WindowBound is not None)
        self.assertTrue(Window is not None)
        self.assertTrue(WindowedCriteria is not None)
        self.assertTrue(DateOffsetStrategy is not None)
        self.assertTrue(CustomEraStrategy is not None)


if __name__ == '__main__':
    unittest.main()

import unittest

from circe.cohortdefinition.builders.device_exposure import DeviceExposureSqlBuilder
from circe.cohortdefinition.builders.utils import BuilderOptions
from circe.cohortdefinition.core import DateRange, NumericRange
from circe.cohortdefinition.criteria import DeviceExposure
from circe.vocabulary.concept import Concept


class TestDeviceExposureSql(unittest.TestCase):
    def test_basic_device_exposure(self):
        criteria = DeviceExposure(
            codeset_id=1, occurrence_start_date=DateRange(value="2023-01-01", op="gt")
        )
        builder = DeviceExposureSqlBuilder()
        options = BuilderOptions()

        # We need to minimally test the resolved clauses
        where_clauses = builder.resolve_where_clauses(criteria, options)
        join_clauses = builder.resolve_join_clauses(criteria, options)
        builder.resolve_select_clauses(criteria, options)

        self.assertTrue(
            any("C.start_date" in c for c in where_clauses),
            "Should have start date condition",
        )
        self.assertEqual(
            len(join_clauses), 0, "Should have no joins for basic criteria"
        )

    def test_device_exposure_with_age(self):
        criteria = DeviceExposure(age=NumericRange(value=50, op="gt"))
        builder = DeviceExposureSqlBuilder()
        options = BuilderOptions()

        where_clauses = builder.resolve_where_clauses(criteria, options)
        join_clauses = builder.resolve_join_clauses(criteria, options)

        # Check join to PERSON
        self.assertTrue(
            any("JOIN @cdm_database_schema.PERSON P" in c for c in join_clauses),
            "Should join to PERSON when age is used",
        )

        # Check date diff logic for age
        age_logic_present = any(
            "YEAR(C.start_date) - P.year_of_birth" in c for c in where_clauses
        )
        self.assertTrue(age_logic_present, "Should use correct age calculation logic")

    def test_device_exposure_joins(self):
        criteria = DeviceExposure(
            visit_type=[Concept(concept_id=1, concept_name="Test")],
            provider_specialty=[Concept(concept_id=2, concept_name="Test")],
        )
        builder = DeviceExposureSqlBuilder()
        options = BuilderOptions()

        join_clauses = builder.resolve_join_clauses(criteria, options)

        self.assertTrue(
            any(
                "JOIN @cdm_database_schema.VISIT_OCCURRENCE V" in c
                for c in join_clauses
            ),
            "Should join to VISIT_OCCURRENCE",
        )
        self.assertTrue(
            any("JOIN @cdm_database_schema.PROVIDER PR" in c for c in join_clauses),
            "Should join to PROVIDER",
        )


if __name__ == "__main__":
    unittest.main()

from circe.cohortdefinition import DeviceExposure, DrugExposure
from circe.cohortdefinition.builders.device_exposure import DeviceExposureSqlBuilder
from circe.cohortdefinition.builders.drug_exposure import DrugExposureSqlBuilder
from circe.cohortdefinition.builders.utils import BuilderOptions


def normalize_sql(sql):
    return " ".join(sql.split()).lower()


class TestDrugExposureSqlBuilder:
    """Tests for DrugExposureSqlBuilder matching Java logic."""

    def test_basic_drug_exposure(self):
        # Setup basic criteria
        criteria = DrugExposure(codeset_id=1, drug_type_exclude=False)

        builder = DrugExposureSqlBuilder()
        options = BuilderOptions()

        sql = normalize_sql(builder.get_criteria_sql(criteria, options))

        assert "from @cdm_database_schema.drug_exposure de" in sql
        assert "join #codesets cs on (de.drug_concept_id = cs.concept_id and cs.codeset_id = 1)" in sql

    def test_full_drug_exposure(self):
        # Test with more options to verify column mapping and joins
        pass


class TestDeviceExposureSqlBuilder:
    """Tests for DeviceExposureSqlBuilder matching Java logic."""

    def test_basic_device_exposure(self):
        criteria = DeviceExposure(codeset_id=2)
        builder = DeviceExposureSqlBuilder()
        options = BuilderOptions()

        sql = normalize_sql(builder.get_criteria_sql(criteria, options))

        # Based on my fixes for 2068:
        # 1. Should be wrapped
        assert "from @cdm_database_schema.device_exposure de" in sql
        assert "from ( select" in sql  # Subquery start
        assert ") c" in sql  # Outer alias

        # 2. Codeset join
        assert "join #codesets cs on (de.device_concept_id = cs.concept_id and cs.codeset_id = 2)" in sql

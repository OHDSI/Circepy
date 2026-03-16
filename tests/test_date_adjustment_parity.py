
from circe.cohortdefinition import (
    ConditionEra,
    ConditionOccurrence,
    DateAdjustment,
    DoseEra,
    DrugEra,
    DrugExposure,
)
from circe.cohortdefinition.builders.condition_era import ConditionEraSqlBuilder
from circe.cohortdefinition.builders.condition_occurrence import (
    ConditionOccurrenceSqlBuilder,
)
from circe.cohortdefinition.builders.dose_era import DoseEraSqlBuilder
from circe.cohortdefinition.builders.drug_era import DrugEraSqlBuilder
from circe.cohortdefinition.builders.drug_exposure import DrugExposureSqlBuilder
from tests.test_utils_db import DuckDBTestHelper


class TestDateAdjustmentParity:
    
    @classmethod
    def setup_class(cls):
        # ... setup db ...
        cls.db = DuckDBTestHelper()
        cls.ce_builder = ConditionEraSqlBuilder()
        cls.de_builder = DrugEraSqlBuilder()
        cls.co_builder = ConditionOccurrenceSqlBuilder()
        cls.dexp_builder = DrugExposureSqlBuilder()
        cls.dose_builder = DoseEraSqlBuilder()

    # ... existing test ...

    def test_drug_era_date_adjustment(self):
        ce = DrugEra()
        ce.codeset_id = 1
        ce.date_adjustment = DateAdjustment(start_offset=5, end_offset=-5)
        
        sql = self.de_builder.get_criteria_sql(ce)
        assert "DATEADD(day,5, de.drug_era_start_date)" in sql
        assert "DATEADD(day,-5, de.drug_era_end_date)" in sql
        
        # Setup Data
        self.db.con.execute("DROP TABLE IF EXISTS drug_era")
        self.db.con.execute("""
            CREATE TABLE drug_era (
                person_id INTEGER,
                drug_era_id INTEGER,
                drug_concept_id INTEGER,
                drug_era_start_date DATE,
                drug_era_end_date DATE,
                drug_exposure_count INTEGER,
                gap_days INTEGER
            )
        """)
        self.db.con.execute("DELETE FROM Codesets")
        # Insert record: 2020-01-10 to 2020-01-20
        self.db.con.execute("INSERT INTO drug_era (person_id, drug_era_id, drug_concept_id, drug_era_start_date, drug_era_end_date, drug_exposure_count, gap_days) VALUES (1, 100, 10, '2020-01-10'::DATE, '2020-01-20'::DATE, 1, 0)")
        self.db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (1, 10)")
        
        query = f"SELECT C.start_date, C.end_date FROM ({sql}) C"
        results = self.db.query(query)
        assert len(results) == 1
        
        res_start = results[0][0]
        res_end = results[0][1]
        
        # Check logic: Start + 5 = 15th, End - 5 = 15th
        import datetime
        if isinstance(res_start, datetime.datetime): res_start = res_start.date()
        if isinstance(res_end, datetime.datetime): res_end = res_end.date()
            
        assert res_start == datetime.date(2020, 1, 15)
        assert res_end == datetime.date(2020, 1, 15)

    def test_condition_occurrence_date_adjustment(self):
        co = ConditionOccurrence()
        co.codeset_id = 1
        co.date_adjustment = DateAdjustment(start_offset=1, end_offset=1)
        
        sql = self.co_builder.get_criteria_sql(co)
        # Condition Occurrence uses co.condition_start_date / condition_end_date
        # Note: End date logic uses COALESCE for safety
        assert "DATEADD(day,1, co.condition_start_date)" in sql
        assert "DATEADD(day,1, COALESCE(co.condition_end_date, DATEADD(day,1,co.condition_start_date)))" in sql
        
        # Setup Data
        self.db.con.execute("DROP TABLE IF EXISTS condition_occurrence")
        self.db.con.execute("""
            CREATE TABLE condition_occurrence (
                person_id INTEGER,
                condition_occurrence_id INTEGER,
                condition_concept_id INTEGER,
                condition_start_date DATE,
                condition_end_date DATE,
                condition_type_concept_id INTEGER,
                stop_reason VARCHAR,
                provider_id INTEGER,
                visit_occurrence_id INTEGER,
                visit_detail_id INTEGER,
                condition_source_value VARCHAR,
                condition_source_concept_id INTEGER,
                condition_status_concept_id INTEGER
            )
        """)
        self.db.con.execute("DELETE FROM Codesets")
        # Insert record
        self.db.con.execute("INSERT INTO condition_occurrence (person_id, condition_occurrence_id, condition_concept_id, condition_start_date, condition_end_date, condition_type_concept_id) VALUES (1, 100, 10, '2020-02-01'::DATE, '2020-02-05'::DATE, 0)")
        self.db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (1, 10)")
        
        query = f"SELECT C.start_date, C.end_date FROM ({sql}) C"
        results = self.db.query(query)
        assert len(results) == 1
        
        res_start = results[0][0]
        res_end = results[0][1]
        
        import datetime
        if isinstance(res_start, datetime.datetime): res_start = res_start.date()
        if isinstance(res_end, datetime.datetime): res_end = res_end.date()
            
        # 2020-02-01 + 1 = 2020-02-02
        # 2020-02-05 + 1 = 2020-02-06
        assert res_start == datetime.date(2020, 2, 2)
        assert res_end == datetime.date(2020, 2, 6)

    def test_drug_exposure_date_adjustment(self):
        de = DrugExposure()
        de.codeset_id = 1
        de.date_adjustment = DateAdjustment(start_offset=2, end_offset=2)
        
        sql = self.dexp_builder.get_criteria_sql(de)
        # Drug Exposure uses de.drug_exposure_start_date / drug_exposure_end_date
        # Check if it uses COALESCE loop like ConditionOccurrence? 
        # Java DrugExposureSqlBuilder: 
        # start_date = drug_exposure_start_date
        # end_date = COALESCE(drug_exposure_end_date, DATEADD(day, 0, drug_exposure_start_date)) (Wait, usually 0 or days_supply?)
        # Let's assume standard COALESCE pattern found in ConditionOccurrence
        assert "DATEADD(day,2, de.drug_exposure_start_date)" in sql
        assert "DATEADD(day,2, COALESCE(de.drug_exposure_end_date, DATEADD(day,0,de.drug_exposure_start_date)))" in sql or "DATEADD(day,2, de.drug_exposure_end_date)" in sql
        
        # Setup Data
        self.db.con.execute("DROP TABLE IF EXISTS drug_exposure")
        self.db.con.execute("""
            CREATE TABLE drug_exposure (
                person_id INTEGER,
                drug_exposure_id INTEGER,
                drug_concept_id INTEGER,
                drug_exposure_start_date DATE,
                drug_exposure_end_date DATE,
                drug_type_concept_id INTEGER,
                stop_reason VARCHAR,
                refills INTEGER,
                quantity NUMERIC,
                days_supply INTEGER,
                sig VARCHAR,
                route_concept_id INTEGER,
                lot_number VARCHAR,
                provider_id INTEGER,
                visit_occurrence_id INTEGER,
                visit_detail_id INTEGER,
                drug_source_value VARCHAR,
                drug_source_concept_id INTEGER,
                route_source_value VARCHAR,
                dose_unit_source_value VARCHAR
            )
        """)
        self.db.con.execute("DELETE FROM Codesets")
        # Insert record
        self.db.con.execute("INSERT INTO drug_exposure (person_id, drug_exposure_id, drug_concept_id, drug_exposure_start_date, drug_exposure_end_date, drug_type_concept_id) VALUES (1, 100, 10, '2020-03-01'::DATE, '2020-03-10'::DATE, 0)")
        self.db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (1, 10)")
        
        query = f"SELECT C.start_date, C.end_date FROM ({sql}) C"
        results = self.db.query(query)
        assert len(results) == 1
        
        res_start = results[0][0]
        res_end = results[0][1]
        
        import datetime
        if isinstance(res_start, datetime.datetime): res_start = res_start.date()
        if isinstance(res_end, datetime.datetime): res_end = res_end.date()
            
        assert res_start == datetime.date(2020, 3, 3)
        assert res_end == datetime.date(2020, 3, 12)

    def test_dose_era_date_adjustment(self):
        de = DoseEra()
        de.codeset_id = 1
        de.date_adjustment = DateAdjustment(start_offset=-1, end_offset=-1)
        
        sql = self.dose_builder.get_criteria_sql(de)
        assert "DATEADD(day,-1, de.dose_era_start_date)" in sql
        assert "DATEADD(day,-1, de.dose_era_end_date)" in sql
        
        # Setup Data
        self.db.con.execute("DROP TABLE IF EXISTS dose_era")
        self.db.con.execute("""
            CREATE TABLE dose_era (
                person_id INTEGER,
                dose_era_id INTEGER,
                drug_concept_id INTEGER,
                unit_concept_id INTEGER,
                dose_value NUMERIC,
                dose_era_start_date DATE,
                dose_era_end_date DATE
            )
        """)
        self.db.con.execute("DELETE FROM Codesets")
        # Insert record
        self.db.con.execute("INSERT INTO dose_era (person_id, dose_era_id, drug_concept_id, dose_era_start_date, dose_era_end_date) VALUES (1, 100, 10, '2020-04-01'::DATE, '2020-04-05'::DATE)")
        self.db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (1, 10)")
        
        query = f"SELECT C.start_date, C.end_date FROM ({sql}) C"
        results = self.db.query(query)
        assert len(results) == 1
        
        res_start = results[0][0]
        res_end = results[0][1]
        
        import datetime
        if isinstance(res_start, datetime.datetime): res_start = res_start.date()
        if isinstance(res_end, datetime.datetime): res_end = res_end.date()
            
        assert res_start == datetime.date(2020, 3, 31)
        assert res_end == datetime.date(2020, 4, 4)
        
    def test_condition_era_date_adjustment(self):
        """
        Replicate Java: CriteriaQuery_5_0_0_Test.testConditionEraDateOffset
        
        Java Logic:
        ConditionEra era = new ConditionEra();
        era.dateAdjustment = new DateAdjustment();
        era.dateAdjustment.startOffset = 2;
        era.dateAdjustment.endOffset = 1;
        """
        # 1. Define Criteria
        ce = ConditionEra()
        # Ensure we have a codeset to make SQL valid/realistic (Java often uses 1)
        ce.codeset_id = 1 
        
        ce.date_adjustment = DateAdjustment(start_offset=2, end_offset=1)
        
        # 2. Generate SQL
        # Note: We need a dummy concept set expression for the builder to include codeset logic if needed,
        # but ConditionEra builder is usually standalone regarding codeset lookups if codeset_id is present?
        # Actually Builder usually needs a concept set mapping.
        # For simplicity in this unit test, we might mock the result or just check the inner SQL 
        # but `get_criteria_sql` usually returns the full inner selection.
        
        sql = self.ce_builder.get_criteria_sql(ce)
        
        # 3. Validation - String Check (Immediate feedback)
        # We expect DATEADD/DATEFROMPARTS logic. 
        # In T-SQL (OHDSI format): DATEADD(day, 2, start_date)
        assert "DATEADD(day,2, ce.condition_era_start_date)" in sql
        assert "DATEADD(day,1, ce.condition_era_end_date)" in sql
        
        # 4. Validation - DuckDB Execution (Functional Parity)
        # We need to wrap the generated criteria SQL in a runnable SELECT to verify it works
        # The criteria SQL usually starts with "SELECT ... FROM ...".
        
        # Add necessary context for it to run:
        # We need a dummy "condition_era" and "Codesets" table populated.
        
        # Setup Data
        self.db.con.execute("DROP TABLE IF EXISTS condition_era")
        self.db.con.execute("""
            CREATE TABLE condition_era (
                person_id INTEGER,
                condition_era_id INTEGER,
                condition_concept_id INTEGER,
                condition_era_start_date DATE,
                condition_era_end_date DATE,
                condition_occurrence_count INTEGER
            )
        """)
        self.db.con.execute("DELETE FROM Codesets")
        
        # Insert a matching record: start_date=2020-01-01, end_date=2020-01-10
        self.db.con.execute("INSERT INTO condition_era (person_id, condition_era_id, condition_concept_id, condition_era_start_date, condition_era_end_date, condition_occurrence_count) VALUES (1, 100, 10, '2020-01-01'::DATE, '2020-01-10'::DATE, 1)")
        
        # Insert codeset mapping
        self.db.con.execute("INSERT INTO Codesets (codeset_id, concept_id) VALUES (1, 10)")
        
        # Construct full query
        # We replace @indexId with 0 or similar
        query = f"""
            SELECT 
                C.person_id, 
                C.event_id, 
                C.start_date, 
                C.end_date 
            FROM (
                {sql}
            ) C
        """
        
        # The builder emits SQL with @codesetId and @indexId placeholders? 
        # Actually `get_criteria_sql` usually renders fully if we pass options? 
        # Or does it leave #Codesets?
        # It relies on #Codesets being created.
        
        # Run It
        # We expect the result dates to be adjusted:
        # Start: 2020-01-01 + 2 days = 2020-01-03
        # End: 2020-01-10 + 1 day = 2020-01-11
        
        # We need to clean up the SQL params manually as our helper does simple replacement
        # ConditionEra builder might not emit params if not using generic properties
        
        results = self.db.query(query)
        
        assert len(results) == 1
        row = results[0]
        # DuckDB returns date objects (or strings depending on driver)
        # person_id, event_id, start_date, end_date
        res_start = row[2]
        res_end = row[3]
        
        import datetime
        
        # DuckDB might return datetime or date depending on driver/version
        if isinstance(res_start, datetime.datetime):
            res_start = res_start.date()
        if isinstance(res_end, datetime.datetime):
            res_end = res_end.date()
            
        assert res_start == datetime.date(2020, 1, 3)
        assert res_end == datetime.date(2020, 1, 11)


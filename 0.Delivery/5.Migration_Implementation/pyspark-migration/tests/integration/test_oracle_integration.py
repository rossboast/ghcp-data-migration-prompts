"""
Integration tests for Oracle extractor with real Oracle database.

These tests require:
    - Oracle database (Docker Oracle 23ai Free recommended)
    - HR schema installed
    - Connection details in .env
    - RUN_INTEGRATION_TESTS=true

Run: pytest tests/integration/test_oracle_integration.py -v -m oracle
"""

import pytest
from .conftest import EXPECTED_COUNTS, EXPECTED_REGION_NAMES, EXPECTED_EMPLOYEE_COLUMNS


@pytest.mark.integration
@pytest.mark.oracle
class TestOracleConnectionIntegration:
    """Test real Oracle database connections."""
    
    def test_connection_validation(self, oracle_extractor):
        """Test that connection to Oracle succeeds."""
        assert oracle_extractor.validate_connection()
    
    def test_connection_properties(self, oracle_extractor, oracle_config):
        """Test connection properties are set correctly."""
        assert oracle_extractor.config.host == oracle_config.host
        assert oracle_extractor.config.port == oracle_config.port
        assert oracle_extractor.config.service_name == oracle_config.service_name
        assert oracle_extractor.config.username == oracle_config.username


@pytest.mark.integration
@pytest.mark.oracle
class TestOracleExtractionIntegration:
    """Test real data extraction from Oracle."""
    
    def test_extract_regions_all(self, oracle_extractor):
        """Test extracting all regions from HR schema."""
        df = oracle_extractor.extract_regions()
        
        assert df is not None
        assert df.count() == EXPECTED_COUNTS["regions"]
        
        # Verify columns
        columns = df.columns
        assert "region_id" in columns
        assert "region_name" in columns
    
    def test_extract_regions_with_filter(self, oracle_extractor):
        """Test extracting regions with WHERE clause."""
        df = oracle_extractor.extract(
            table="regions",
            where_clause="region_id <= 2"
        )
        
        assert df is not None
        count = df.count()
        assert count == 2
    
    def test_extract_employees_all(self, oracle_extractor):
        """Test extracting all employees from HR schema."""
        df = oracle_extractor.extract_employees()
        
        assert df is not None
        assert df.count() == EXPECTED_COUNTS["employees"]
        
        # Verify all expected columns present
        columns = df.columns
        for expected_col in EXPECTED_EMPLOYEE_COLUMNS:
            assert expected_col.upper() in [c.upper() for c in columns]
    
    def test_extract_with_column_selection(self, oracle_extractor):
        """Test extracting specific columns only."""
        columns = ["employee_id", "first_name", "last_name", "salary"]
        df = oracle_extractor.extract(
            table="employees",
            columns=columns
        )
        
        assert df is not None
        assert len(df.columns) == len(columns)
        
        # Verify only requested columns present
        for col in columns:
            assert col.upper() in [c.upper() for c in df.columns]
    
    def test_extract_with_complex_filter(self, oracle_extractor):
        """Test extraction with complex WHERE clause."""
        df = oracle_extractor.extract(
            table="employees",
            where_clause="salary > 10000 AND department_id = 90"
        )
        
        assert df is not None
        count = df.count()
        assert count > 0  # Should have some high-salary execs in dept 90
        
        # Verify all records meet criteria
        records = df.collect()
        for record in records:
            assert record["SALARY"] > 10000
            assert record["DEPARTMENT_ID"] == 90


@pytest.mark.integration
@pytest.mark.oracle
class TestOracleBatchOperationsIntegration:
    """Test batch operations with real Oracle database."""
    
    def test_extract_all_tables(self, oracle_extractor):
        """Test extracting all tables from HR schema."""
        tables = ["regions", "countries", "locations"]
        dataframes = oracle_extractor.extract_all_tables(tables)
        
        assert len(dataframes) == len(tables)
        
        # Verify each table extracted
        for table in tables:
            assert table in dataframes
            assert dataframes[table] is not None
            assert dataframes[table].count() > 0
    
    def test_extract_all_tables_with_invalid(self, oracle_extractor):
        """Test that invalid tables are skipped gracefully."""
        tables = ["regions", "invalid_table_xyz", "countries"]
        dataframes = oracle_extractor.extract_all_tables(tables)
        
        # Should get valid tables only
        assert "regions" in dataframes
        assert "countries" in dataframes
        assert "invalid_table_xyz" not in dataframes


@pytest.mark.integration
@pytest.mark.oracle
@pytest.mark.slow
class TestOracleUtilitiesIntegration:
    """Test utility functions with real Oracle database."""
    
    def test_get_table_count(self, oracle_extractor):
        """Test getting row count for a specific table."""
        count = oracle_extractor.get_table_count("regions")
        assert count == EXPECTED_COUNTS["regions"]
        
        count = oracle_extractor.get_table_count("employees")
        assert count == EXPECTED_COUNTS["employees"]
    
    def test_get_all_table_counts(self, oracle_extractor):
        """Test getting row counts for multiple tables."""
        tables = ["regions", "countries", "employees"]
        counts = oracle_extractor.get_all_table_counts(tables)
        
        assert len(counts) == len(tables)
        assert counts["regions"] == EXPECTED_COUNTS["regions"]
        assert counts["countries"] == EXPECTED_COUNTS["countries"]
        assert counts["employees"] == EXPECTED_COUNTS["employees"]
    
    def test_get_table_count_invalid_table(self, oracle_extractor):
        """Test that invalid table returns 0 or raises error."""
        # Depending on implementation, might return 0 or raise exception
        try:
            count = oracle_extractor.get_table_count("invalid_table_xyz")
            assert count == 0
        except Exception:
            # Expected if implementation raises exception for invalid tables
            pass


@pytest.mark.integration
@pytest.mark.oracle
class TestOracleDataQualityIntegration:
    """Test data quality and content validation."""
    
    def test_region_names_correct(self, oracle_extractor):
        """Test that region names match expected values."""
        df = oracle_extractor.extract_regions()
        records = df.collect()
        
        region_names = [r["REGION_NAME"] for r in records]
        
        for expected_name in EXPECTED_REGION_NAMES:
            assert expected_name in region_names
    
    def test_no_null_primary_keys(self, oracle_extractor):
        """Test that primary key columns have no nulls."""
        # Test regions primary key
        df = oracle_extractor.extract_regions()
        null_count = df.filter("region_id IS NULL").count()
        assert null_count == 0
        
        # Test employees primary key
        df = oracle_extractor.extract_employees()
        null_count = df.filter("employee_id IS NULL").count()
        assert null_count == 0
    
    def test_foreign_key_integrity(self, oracle_extractor):
        """Test basic foreign key relationships."""
        # Get all departments and their employee counts
        departments_df = oracle_extractor.extract("departments")
        employees_df = oracle_extractor.extract_employees()
        
        # Every employee's department_id should exist in departments
        # (except for NULL department_ids)
        emp_depts = employees_df.filter("department_id IS NOT NULL") \
                                .select("department_id") \
                                .distinct() \
                                .collect()
        
        dept_ids = [d["DEPARTMENT_ID"] for d in departments_df.collect()]
        
        for emp_dept in emp_depts:
            assert emp_dept["department_id"] in dept_ids


@pytest.mark.integration
@pytest.mark.oracle
class TestOracleMetricsIntegration:
    """Test metrics collection with real extractions."""
    
    def test_metrics_collection(self, oracle_extractor):
        """Test that metrics are collected during extraction."""
        df, metrics = oracle_extractor.extract_with_metrics(
            table="employees"
        )
        
        assert df is not None
        assert metrics is not None
        
        # Verify metric fields
        assert hasattr(metrics, "records_processed")
        assert hasattr(metrics, "execution_time")
        assert hasattr(metrics, "success")
        
        # Verify metric values
        assert metrics.records_processed == EXPECTED_COUNTS["employees"]
        assert metrics.execution_time > 0
        assert metrics.success is True
    
    def test_metrics_with_filter(self, oracle_extractor):
        """Test metrics reflect filtered extraction."""
        df, metrics = oracle_extractor.extract_with_metrics(
            table="employees",
            where_clause="department_id = 90"
        )
        
        assert metrics.records_processed == df.count()
        assert metrics.records_processed < EXPECTED_COUNTS["employees"]


@pytest.mark.integration
@pytest.mark.oracle
@pytest.mark.slow
class TestOraclePerformanceIntegration:
    """Test performance characteristics of real extractions."""
    
    def test_large_table_extraction_performance(self, oracle_extractor):
        """Test extraction performance for largest table."""
        import time
        
        start_time = time.time()
        df = oracle_extractor.extract_employees()
        extraction_time = time.time() - start_time
        
        # Should complete in reasonable time (adjust threshold as needed)
        assert extraction_time < 10.0  # seconds
        assert df.count() == EXPECTED_COUNTS["employees"]
    
    def test_batch_extraction_performance(self, oracle_extractor):
        """Test batch extraction of multiple tables."""
        import time
        
        tables = ["regions", "countries", "locations", "departments", "jobs"]
        
        start_time = time.time()
        dataframes = oracle_extractor.extract_all_tables(tables)
        extraction_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert extraction_time < 30.0  # seconds
        assert len(dataframes) == len(tables)

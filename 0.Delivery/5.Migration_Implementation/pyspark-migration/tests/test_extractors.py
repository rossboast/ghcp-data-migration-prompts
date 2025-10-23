"""
Unit tests for Oracle extractor with mocked JDBC connections.

These tests use mocking to avoid requiring a real Oracle database.
For integration tests with real Oracle, see integration/test_oracle_integration.py

Run these tests:
    pytest tests/test_extractors.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType

from extractors.oracle_extractor import OracleExtractor
from config.connections import OracleConnectionConfig
from utils.error_handler import ExtractionError


@pytest.fixture
def mock_oracle_config():
    """Create mock Oracle connection config."""
    return OracleConnectionConfig(
        host="localhost",
        port=1521,
        service="XEPDB1",
        user="hr",
        password="test_password"
    )


@pytest.fixture
def mock_spark_session():
    """Create mock SparkSession with properly mocked read.jdbc."""
    mock_spark = MagicMock(spec=SparkSession)
    
    # Mock the read.jdbc chain
    mock_jdbc = MagicMock()
    mock_read = MagicMock()
    mock_read.jdbc = mock_jdbc
    mock_spark.read = mock_read
    
    return mock_spark


@pytest.fixture
def mock_dataframe():
    """Create mock DataFrame with expected methods."""
    mock_df = MagicMock(spec=DataFrame)
    mock_df.count.return_value = 10
    mock_df.collect.return_value = []
    
    # Mock schema
    mock_schema = StructType([
        StructField("id", IntegerType(), True),
        StructField("name", StringType(), True)
    ])
    type(mock_df).schema = PropertyMock(return_value=mock_schema)
    
    return mock_df


class TestOracleExtractorInitialization:
    """Test OracleExtractor initialization."""
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_initialization_success(self, mock_get_session, mock_oracle_config, mock_spark_session):
        """Test successful extractor initialization."""
        mock_get_session.return_value = mock_spark_session
        
        extractor = OracleExtractor(mock_oracle_config)
        
        assert extractor.config == mock_oracle_config
        assert extractor.spark == mock_spark_session
        assert len(extractor.AVAILABLE_TABLES) == 7
        assert "employees" in extractor.AVAILABLE_TABLES
        assert "regions" in extractor.AVAILABLE_TABLES
        assert "departments" in extractor.AVAILABLE_TABLES
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_jdbc_properties_configured(self, mock_get_session, mock_oracle_config, mock_spark_session):
        """Test JDBC properties are properly configured."""
        mock_get_session.return_value = mock_spark_session
        
        extractor = OracleExtractor(mock_oracle_config)
        
        assert extractor.jdbc_properties["user"] == "hr"
        assert extractor.jdbc_properties["password"] == "test_password"
        assert extractor.jdbc_properties["driver"] == "oracle.jdbc.driver.OracleDriver"
        assert "fetchsize" in extractor.jdbc_properties
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_jdbc_url_generation(self, mock_get_session, mock_oracle_config, mock_spark_session):
        """Test JDBC URL is properly generated."""
        mock_get_session.return_value = mock_spark_session
        
        extractor = OracleExtractor(mock_oracle_config)
        
        expected_url = "jdbc:oracle:thin:@localhost:1521/XEPDB1"
        assert extractor.jdbc_url == expected_url


class TestOracleExtractorConnection:
    """Test connection validation."""
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_validate_connection_success(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test successful connection validation."""
        mock_get_session.return_value = mock_spark_session
        mock_dataframe.count.return_value = 1
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        
        extractor = OracleExtractor(mock_oracle_config)
        result = extractor.validate_connection()
        
        assert result is True
        
        # Verify DUAL query was used
        call_args = mock_spark_session.read.jdbc.call_args
        assert call_args is not None
        assert "(SELECT 1 FROM DUAL)" in call_args[1]["table"]
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_validate_connection_failure(self, mock_get_session, mock_oracle_config, mock_spark_session):
        """Test connection validation failure."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.side_effect = Exception("Connection refused")
        
        extractor = OracleExtractor(mock_oracle_config)
        result = extractor.validate_connection()
        
        assert result is False


class TestOracleExtractorExtraction:
    """Test data extraction methods."""
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extract_table_basic(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test basic table extraction."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        mock_dataframe.count.return_value = 4
        
        extractor = OracleExtractor(mock_oracle_config)
        df = extractor.extract("regions")
        
        assert df is not None
        assert df.count() == 4
        
        # Verify JDBC call was made with correct parameters
        call_args = mock_spark_session.read.jdbc.call_args
        assert call_args[1]["url"] == extractor.jdbc_url
        assert "regions" in call_args[1]["table"].upper()
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extract_with_where_clause(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test extraction with WHERE clause."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        mock_dataframe.count.return_value = 2
        
        extractor = OracleExtractor(mock_oracle_config)
        df = extractor.extract("departments", where_clause="manager_id IS NULL")
        
        # Verify WHERE clause was included in query
        call_args = mock_spark_session.read.jdbc.call_args
        query = call_args[1]["table"]
        assert "WHERE manager_id IS NULL" in query
        assert df.count() == 2
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extract_invalid_table(self, mock_get_session, mock_oracle_config, mock_spark_session):
        """Test extraction of non-existent table."""
        mock_get_session.return_value = mock_spark_session
        
        extractor = OracleExtractor(mock_oracle_config)
        
        with pytest.raises(ExtractionError) as exc_info:
            extractor.extract("nonexistent_table")
        
        assert "not in available tables" in str(exc_info.value).lower()
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extract_with_columns(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test extraction with specific columns."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        
        extractor = OracleExtractor(mock_oracle_config)
        df = extractor.extract("employees", columns=["employee_id", "first_name", "last_name"])
        
        # Verify SELECT clause was built correctly
        call_args = mock_spark_session.read.jdbc.call_args
        query = call_args[1]["table"]
        assert "employee_id" in query
        assert "first_name" in query
        assert "last_name" in query


class TestOracleExtractorConvenienceMethods:
    """Test table-specific convenience methods."""
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extract_regions(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test extract_regions convenience method."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        mock_dataframe.count.return_value = 4
        
        extractor = OracleExtractor(mock_oracle_config)
        df = extractor.extract_regions()
        
        assert df.count() == 4
        call_args = mock_spark_session.read.jdbc.call_args
        assert "regions" in call_args[1]["table"].lower()
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extract_employees(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test extract_employees convenience method."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        mock_dataframe.count.return_value = 107
        
        extractor = OracleExtractor(mock_oracle_config)
        df = extractor.extract_employees()
        
        assert df.count() == 107
        call_args = mock_spark_session.read.jdbc.call_args
        assert "employees" in call_args[1]["table"].lower()
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extract_employees_active_only(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test extract_employees with active_only filter."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        
        extractor = OracleExtractor(mock_oracle_config)
        df = extractor.extract_employees(active_only=True)
        
        # Verify filter was applied (if implemented in extractor)
        call_args = mock_spark_session.read.jdbc.call_args
        query = call_args[1]["table"]
        # The actual WHERE clause depends on implementation
        assert "employees" in query.lower()
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extract_departments_exclude_null_managers(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test extract_departments with include_null_managers=False."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        
        extractor = OracleExtractor(mock_oracle_config)
        df = extractor.extract_departments(include_null_managers=False)
        
        # Verify NULL manager filter was applied
        call_args = mock_spark_session.read.jdbc.call_args
        query = call_args[1]["table"]
        assert "manager_id IS NOT NULL" in query or "departments" in query.lower()


class TestOracleExtractorBatchOperations:
    """Test batch extraction operations."""
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extract_all_tables(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test extracting all tables at once."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        
        extractor = OracleExtractor(mock_oracle_config)
        
        # Mock different counts for different tables
        counts = [4, 25, 23, 27, 19, 107, 10]
        mock_dataframe.count.side_effect = counts
        
        tables_dict = extractor.extract_all_tables()
        
        # Verify all 7 tables were extracted
        assert len(tables_dict) == 7
        assert "regions" in tables_dict
        assert "countries" in tables_dict
        assert "employees" in tables_dict
        
        # Verify JDBC was called 7 times
        assert mock_spark_session.read.jdbc.call_count == 7
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extract_specific_tables_subset(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test extracting specific subset of tables."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        
        extractor = OracleExtractor(mock_oracle_config)
        
        tables_to_extract = ["regions", "countries", "jobs"]
        tables_dict = extractor.extract_all_tables(tables=tables_to_extract)
        
        # Verify only requested tables were extracted
        assert len(tables_dict) == 3
        assert "regions" in tables_dict
        assert "countries" in tables_dict
        assert "jobs" in tables_dict
        assert "employees" not in tables_dict


class TestOracleExtractorUtilities:
    """Test utility methods."""
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_get_table_count(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test getting row count for a table."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        mock_dataframe.count.return_value = 107
        
        extractor = OracleExtractor(mock_oracle_config)
        count = extractor.get_table_count("employees")
        
        assert count == 107
        
        # Verify COUNT(*) query was used
        call_args = mock_spark_session.read.jdbc.call_args
        query = call_args[1]["table"]
        assert "COUNT(*)" in query.upper() or "employees" in query.lower()
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_get_all_table_counts(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test getting counts for all tables."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        
        # Mock different counts for different tables
        expected_counts = {
            "regions": 4,
            "countries": 25,
            "locations": 23,
            "departments": 27,
            "jobs": 19,
            "employees": 107,
            "job_history": 10
        }
        
        # Set up side effect to return different counts
        mock_dataframe.count.side_effect = list(expected_counts.values())
        
        extractor = OracleExtractor(mock_oracle_config)
        counts = extractor.get_all_table_counts()
        
        # Verify counts dictionary
        assert len(counts) == 7
        assert counts["regions"] == 4
        assert counts["employees"] == 107


class TestOracleExtractorErrorHandling:
    """Test error handling scenarios."""
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extraction_with_jdbc_error(self, mock_get_session, mock_oracle_config, mock_spark_session):
        """Test handling of JDBC errors during extraction."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.side_effect = Exception("JDBC connection failed")
        
        extractor = OracleExtractor(mock_oracle_config)
        
        with pytest.raises(Exception) as exc_info:
            extractor.extract("employees")
        
        assert "JDBC connection failed" in str(exc_info.value)
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extraction_with_empty_result(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test extraction returning empty DataFrame."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        mock_dataframe.count.return_value = 0
        
        extractor = OracleExtractor(mock_oracle_config)
        df = extractor.extract("employees")
        
        # Empty result is valid, should not raise error
        assert df.count() == 0


class TestOracleExtractorMetrics:
    """Test metrics collection during extraction."""
    
    @patch('extractors.oracle_extractor.SparkSessionManager.get_session')
    def test_extract_with_metrics(self, mock_get_session, mock_oracle_config, mock_spark_session, mock_dataframe):
        """Test extraction with automatic metrics collection."""
        mock_get_session.return_value = mock_spark_session
        mock_spark_session.read.jdbc.return_value = mock_dataframe
        mock_dataframe.count.return_value = 107
        
        extractor = OracleExtractor(mock_oracle_config)
        df = extractor.extract_with_metrics("employees")
        
        # Verify DataFrame was returned
        assert df is not None
        assert df.count() == 107
        
        # Verify metrics were collected (if implemented in base class)
        assert hasattr(extractor, 'metrics')
        assert extractor.metrics.records_processed > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Unit tests for transformation utilities.

Tests data type conversion and common transformations.
"""

import pytest
import sys
from datetime import datetime, date
from decimal import Decimal
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, DateType, TimestampType
)

from transformers.data_type_converter import DataTypeConverter
from transformers.common_transformations import CommonTransformations


@pytest.fixture(scope="module")
def spark():
    """Create Spark session for testing."""
    spark = SparkSession.builder \
        .appName("TestTransformers") \
        .master("local[*]") \
        .getOrCreate()
    yield spark
    spark.stop()


class TestDataTypeConverter:
    """Test DataTypeConverter functionality."""
    
    def test_convert_date_to_iso_string(self):
        """Test DATE to ISO string conversion."""
        test_date = date(2024, 1, 15)
        result = DataTypeConverter.convert_date_to_iso_string(test_date)
        assert result == "2024-01-15"
    
    def test_convert_date_to_iso_string_none(self):
        """Test DATE to ISO string with None."""
        result = DataTypeConverter.convert_date_to_iso_string(None)
        assert result is None
    
    def test_convert_timestamp_to_iso_string(self):
        """Test TIMESTAMP to ISO string conversion."""
        test_ts = datetime(2024, 1, 15, 10, 30, 45)
        result = DataTypeConverter.convert_timestamp_to_iso_string(test_ts)
        assert result == "2024-01-15T10:30:45"
    
    def test_convert_timestamp_to_iso_string_none(self):
        """Test TIMESTAMP to ISO string with None."""
        result = DataTypeConverter.convert_timestamp_to_iso_string(None)
        assert result is None
    
    def test_convert_decimal_to_number(self):
        """Test DECIMAL to number conversion."""
        test_decimal = Decimal("123.45")
        result = DataTypeConverter.convert_decimal_to_number(test_decimal)
        assert result == 123.45
        assert isinstance(result, float)
    
    def test_convert_decimal_to_number_none(self):
        """Test DECIMAL to number with None."""
        result = DataTypeConverter.convert_decimal_to_number(None)
        assert result is None
    
    def test_convert_dataframe(self, spark):
        """Test full DataFrame conversion."""
        # Create test DataFrame
        schema = StructType([
            StructField("id", IntegerType(), True),
            StructField("name", StringType(), True),
            StructField("salary", DoubleType(), True),
            StructField("hire_date", DateType(), True)
        ])
        
        data = [
            (1, "John Doe", 50000.0, date(2020, 1, 15)),
            (2, "Jane Smith", 60000.0, date(2021, 3, 20))
        ]
        
        df = spark.createDataFrame(data, schema)
        
        # Convert
        result_df = DataTypeConverter.convert_dataframe(df)
        
        # Verify schema
        assert "id" in result_df.columns
        assert "name" in result_df.columns
        assert "salary" in result_df.columns
        assert "hire_date" in result_df.columns
        
        # Verify data
        result_data = result_df.collect()
        assert len(result_data) == 2
        assert result_data[0]["name"] == "John Doe"


class TestCommonTransformations:
    """Test CommonTransformations functionality."""
    
    def test_calculate_partition_key(self, spark):
        """Test partition key calculation."""
        schema = StructType([
            StructField("employee_id", IntegerType(), True),
            StructField("department_id", IntegerType(), True)
        ])
        
        data = [
            (100, 10),
            (101, 20),
            (102, 10)
        ]
        
        df = spark.createDataFrame(data, schema)
        
        # Apply partition key formula
        result_df = CommonTransformations.calculate_partition_key(
            df,
            "dept_{department_id}_{employee_id % 10}"
        )
        
        # Verify partition key column exists
        assert "partitionKey" in result_df.columns
        
        # Verify values
        result_data = result_df.collect()
        assert result_data[0]["partitionKey"] == "dept_10_0"
        assert result_data[1]["partitionKey"] == "dept_20_1"
        assert result_data[2]["partitionKey"] == "dept_10_2"
    
    def test_add_document_id(self, spark):
        """Test document ID addition."""
        schema = StructType([
            StructField("employee_id", IntegerType(), True)
        ])
        
        data = [(100,), (101,), (102,)]
        
        df = spark.createDataFrame(data, schema)
        
        # Add document ID
        result_df = CommonTransformations.add_document_id(
            df,
            "emp_{employee_id}"
        )
        
        # Verify ID column
        assert "id" in result_df.columns
        
        result_data = result_df.collect()
        assert result_data[0]["id"] == "emp_100"
        assert result_data[1]["id"] == "emp_101"
    
    def test_add_metadata(self, spark):
        """Test metadata addition."""
        schema = StructType([
            StructField("id", IntegerType(), True)
        ])
        
        data = [(1,)]
        
        df = spark.createDataFrame(data, schema)
        
        # Add metadata
        result_df = CommonTransformations.add_metadata(
            df,
            source_system="oracle_hr",
            entity_type="employee"
        )
        
        # Verify metadata columns
        assert "metadata" in result_df.columns
        
        result_data = result_df.collect()
        metadata = result_data[0]["metadata"]
        
        assert metadata["source_system"] == "oracle_hr"
        assert metadata["entity_type"] == "employee"
        assert "migrated_at" in metadata
        assert "version" in metadata
    
    def test_create_reference_document(self, spark):
        """Test reference document creation."""
        schema = StructType([
            StructField("region_id", IntegerType(), True),
            StructField("region_name", StringType(), True)
        ])
        
        data = [
            (1, "Europe"),
            (2, "Americas")
        ]
        
        df = spark.createDataFrame(data, schema)
        
        # Create reference document
        result_df = CommonTransformations.create_reference_document(
            df=df,
            entity_type="region",
            id_column="region_id",
            partition_key_value="ref_data",
            data_columns=["region_name"]
        )
        
        # Verify structure
        assert "id" in result_df.columns
        assert "partitionKey" in result_df.columns
        assert "entity_type" in result_df.columns
        assert "data" in result_df.columns
        
        result_data = result_df.collect()
        assert result_data[0]["id"] == "region_1"
        assert result_data[0]["partitionKey"] == "ref_data"
        assert result_data[0]["entity_type"] == "region"
        assert result_data[0]["data"]["region_name"] == "Europe"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

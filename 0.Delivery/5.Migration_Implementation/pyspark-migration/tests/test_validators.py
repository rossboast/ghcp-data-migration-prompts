"""
Unit tests for validators.

Tests field validation, record validation, and business rule validation.
"""

import pytest
from datetime import date
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    DoubleType, DateType
)

from validators.field_validator import FieldValidator
from validators.record_validator import RecordValidator
from validators.business_rule_validator import BusinessRuleValidator


@pytest.fixture(scope="module")
def spark():
    """Create Spark session for testing."""
    spark = SparkSession.builder \
        .appName("TestValidators") \
        .master("local[*]") \
        .getOrCreate()
    yield spark
    spark.stop()


class TestFieldValidator:
    """Test FieldValidator functionality."""
    
    def test_not_null_validation(self, spark):
        """Test NOT_NULL validation rule."""
        schema = StructType([
            StructField("id", IntegerType(), True),
            StructField("name", StringType(), True)
        ])
        
        data = [
            (1, "John"),
            (2, None),  # Invalid
            (3, "Jane")
        ]
        
        df = spark.createDataFrame(data, schema)
        
        validator = FieldValidator(
            validation_rules={"name": ["NOT_NULL"]}
        )
        
        result = validator.validate(df)
        
        assert not result.is_valid
        assert len(result.errors) == 1
        assert result.errors[0]["rule"] == "NOT_NULL"
        assert result.errors[0]["error_count"] == 1
    
    def test_positive_validation(self, spark):
        """Test POSITIVE validation rule."""
        schema = StructType([
            StructField("id", IntegerType(), True),
            StructField("salary", DoubleType(), True)
        ])
        
        data = [
            (1, 50000.0),
            (2, -1000.0),  # Invalid
            (3, 0.0)  # Invalid (not positive)
        ]
        
        df = spark.createDataFrame(data, schema)
        
        validator = FieldValidator(
            validation_rules={"salary": ["POSITIVE"]}
        )
        
        result = validator.validate(df)
        
        assert not result.is_valid
        assert result.errors[0]["error_count"] == 2
    
    def test_email_format_validation(self, spark):
        """Test EMAIL_FORMAT validation rule."""
        schema = StructType([
            StructField("id", IntegerType(), True),
            StructField("email", StringType(), True)
        ])
        
        data = [
            (1, "john@example.com"),
            (2, "invalid-email"),  # Invalid
            (3, "jane@test.org")
        ]
        
        df = spark.createDataFrame(data, schema)
        
        validator = FieldValidator(
            validation_rules={"email": ["EMAIL_FORMAT"]}
        )
        
        result = validator.validate(df)
        
        assert not result.is_valid
        assert result.errors[0]["error_count"] == 1
    
    def test_date_range_validation(self, spark):
        """Test DATE_RANGE validation rule."""
        schema = StructType([
            StructField("id", IntegerType(), True),
            StructField("hire_date", StringType(), True)
        ])
        
        data = [
            (1, "2020-01-15"),
            (2, "1985-06-20"),  # Invalid (before min)
            (3, "2025-03-10")
        ]
        
        df = spark.createDataFrame(data, schema)
        
        validator = FieldValidator(
            validation_rules={"hire_date": ["DATE_RANGE:1990-01-01:2030-12-31"]}
        )
        
        result = validator.validate(df)
        
        assert not result.is_valid
        assert result.errors[0]["error_count"] == 1
    
    def test_multiple_rules(self, spark):
        """Test multiple validation rules on same field."""
        schema = StructType([
            StructField("id", IntegerType(), True),
            StructField("name", StringType(), True)
        ])
        
        data = [
            (1, "John"),
            (2, None),  # Fails NOT_NULL
            (3, "J")  # Fails LENGTH_MIN
        ]
        
        df = spark.createDataFrame(data, schema)
        
        validator = FieldValidator(
            validation_rules={"name": ["NOT_NULL", "LENGTH_MIN:2"]}
        )
        
        result = validator.validate(df)
        
        assert not result.is_valid
        assert len(result.errors) == 2  # Two different rules failed


class TestRecordValidator:
    """Test RecordValidator functionality."""
    
    def test_referential_integrity(self, spark):
        """Test referential integrity validation."""
        # Employees
        emp_schema = StructType([
            StructField("employee_id", IntegerType(), True),
            StructField("name", StringType(), True),
            StructField("department_id", IntegerType(), True),
            StructField("job_id", StringType(), True)
        ])
        
        emp_data = [
            (1, "John", 10, "IT_PROG"),
            (2, "Jane", 99, "IT_PROG"),  # Invalid department_id
            (3, "Bob", 10, "INVALID_JOB")  # Invalid job_id
        ]
        
        employees_df = spark.createDataFrame(emp_data, emp_schema)
        
        # Departments
        dept_data = [(10, "IT"), (20, "Sales")]
        departments_df = spark.createDataFrame(
            dept_data,
            ["department_id", "department_name"]
        )
        
        # Jobs
        job_data = [("IT_PROG", "Programmer"), ("SA_REP", "Sales Rep")]
        jobs_df = spark.createDataFrame(job_data, ["job_id", "job_title"])
        
        validator = RecordValidator()
        
        result = validator.validate(
            employees_df,
            reference_data={
                "departments": departments_df,
                "jobs": jobs_df
            }
        )
        
        assert not result.is_valid
        # Should find both invalid department_id and invalid job_id
        error_types = [e["field"] for e in result.errors]
        assert "department_id" in error_types or "job_id" in error_types
    
    def test_cross_field_constraints(self, spark):
        """Test cross-field constraint validation."""
        schema = StructType([
            StructField("employee_id", IntegerType(), True),
            StructField("start_date", StringType(), True),
            StructField("end_date", StringType(), True)
        ])
        
        data = [
            (1, "2020-01-01", "2021-01-01"),  # Valid
            (2, "2021-01-01", "2020-01-01")   # Invalid (end before start)
        ]
        
        df = spark.createDataFrame(data, schema)
        
        validator = RecordValidator()
        result = validator.validate(df)
        
        # Should detect date range violation
        assert not result.is_valid


class TestBusinessRuleValidator:
    """Test BusinessRuleValidator functionality."""
    
    def test_salary_range_validation(self, spark):
        """Test salary within job range validation."""
        # Employees
        emp_schema = StructType([
            StructField("employee_id", IntegerType(), True),
            StructField("job_id", StringType(), True),
            StructField("salary", DoubleType(), True)
        ])
        
        emp_data = [
            (1, "IT_PROG", 5000.0),   # Valid
            (2, "IT_PROG", 20000.0),  # Invalid (above max)
            (3, "IT_PROG", 2000.0)    # Invalid (below min)
        ]
        
        employees_df = spark.createDataFrame(emp_data, emp_schema)
        
        # Jobs with salary ranges
        job_data = [
            ("IT_PROG", "Programmer", 4000, 10000)
        ]
        jobs_df = spark.createDataFrame(
            job_data,
            ["job_id", "job_title", "min_salary", "max_salary"]
        )
        
        validator = BusinessRuleValidator()
        
        result = validator.validate(
            employees_df,
            business_context={"jobs": jobs_df}
        )
        
        assert not result.is_valid
        # Should find both above max and below min
        assert len(result.errors) >= 1
    
    def test_email_uniqueness(self, spark):
        """Test email uniqueness validation."""
        schema = StructType([
            StructField("employee_id", IntegerType(), True),
            StructField("email", StringType(), True)
        ])
        
        data = [
            (1, "john@example.com"),
            (2, "jane@example.com"),
            (3, "john@example.com")  # Duplicate!
        ]
        
        df = spark.createDataFrame(data, schema)
        
        validator = BusinessRuleValidator()
        result = validator.validate(df)
        
        assert not result.is_valid
        # Should find duplicate email
        duplicate_errors = [e for e in result.errors if e["rule"] == "email_uniqueness"]
        assert len(duplicate_errors) > 0
    
    def test_self_manager(self, spark):
        """Test self-manager detection."""
        schema = StructType([
            StructField("employee_id", IntegerType(), True),
            StructField("manager_id", IntegerType(), True)
        ])
        
        data = [
            (1, 2),  # Valid
            (2, 2),  # Invalid (self-manager!)
            (3, 1)   # Valid
        ]
        
        df = spark.createDataFrame(data, schema)
        
        validator = BusinessRuleValidator()
        result = validator.validate(df)
        
        assert not result.is_valid
        # Should detect self-management
        self_manager_errors = [
            e for e in result.errors
            if "self" in e["rule"].lower()
        ]
        assert len(self_manager_errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

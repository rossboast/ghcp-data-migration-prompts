"""
Record Validator

Validates cross-field relationships and record-level constraints.
Implements record-level validation rules including:
- Referential integrity (foreign key checks)
- Cross-field validation (start_date < end_date)
- Required field combinations
- Data consistency checks

Usage:
    from validators import RecordValidator
    
    validator = RecordValidator()
    result = validator.validate_with_metrics(
        employees_df,
        reference_data={
            "departments": departments_df,
            "jobs": jobs_df
        }
    )
"""

from typing import Dict, Any, Optional, List
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, when, lit

from validators.base_validator import BaseValidator, ValidationResult
from utils.logging_config import get_logger
from utils.metrics import MetricsCollector


class RecordValidator(BaseValidator):
    """
    Validate record-level constraints and relationships.
    
    Validates:
    - Referential integrity (FKs exist in reference tables)
    - Cross-field constraints (date ranges, conditional requirements)
    - Field combinations (if A then B must exist)
    - Data consistency
    """
    
    def __init__(
        self,
        logger: Optional[Any] = None,
        metrics: Optional[MetricsCollector] = None
    ):
        """
        Initialize record validator.
        
        Args:
            logger: Optional logger instance
            metrics: Optional metrics collector
        """
        # Simple initialization without calling super().__init__
        self.logger = logger or get_logger("record_validator")
        self.metrics = metrics  # Don't instantiate MetricsCollector, just keep None or passed value
        
        self.logger.info("Record validator initialized")
    
    def get_validation_rules(self) -> List[str]:
        """
        Get list of validation rules applied by this validator.
        
        Returns:
            List of rule descriptions
        """
        return [
            "Referential Integrity: Foreign keys exist in reference tables",
            "Cross-field Constraints: Date ranges and conditional requirements",
            "Data Consistency: Field value relationships"
        ]
    
    def validate(
        self,
        df: DataFrame,
        reference_data: Optional[Dict[str, DataFrame]] = None
    ) -> ValidationResult:
        """
        Validate records with cross-field and referential integrity checks.
        
        Args:
            df: DataFrame to validate
            reference_data: Dictionary of reference DataFrames for FK checks
            
        Returns:
            ValidationResult with validation status and errors
        """
        self.logger.info("Starting record validation")
        
        errors = []
        warnings = []
        total_records = df.count()
        valid_records = total_records
        
        # Validate referential integrity
        if reference_data:
            ref_errors = self._validate_referential_integrity(df, reference_data)
            errors.extend(ref_errors)
        
        # Validate cross-field constraints
        cross_field_errors = self._validate_cross_field_constraints(df)
        errors.extend(cross_field_errors)
        
        # Validate required combinations
        combo_errors = self._validate_required_combinations(df)
        errors.extend(combo_errors)
        
        # Calculate invalid records
        if errors:
            total_errors = sum(e.get("error_count", 0) for e in errors)
            invalid_records = min(total_errors, total_records)
        else:
            invalid_records = 0
        
        is_valid = len(errors) == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            total_records=total_records,
            invalid_records=invalid_records,
            errors=errors,
            warnings=warnings
        )
        
        self.logger.info(
            "Record validation completed",
            is_valid=is_valid,
            total_records=total_records,
            valid_records=valid_records,
            error_count=len(errors)
        )
        
        return result
    
    def _validate_referential_integrity(
        self,
        df: DataFrame,
        reference_data: Dict[str, DataFrame]
    ) -> list:
        """
        Validate foreign key references exist.
        
        Args:
            df: Main DataFrame
            reference_data: Dictionary of reference DataFrames
            
        Returns:
            List of validation errors
        """
        errors = []
        
        self.logger.debug("Validating referential integrity")
        
        # Check department_id exists in departments
        if "departments" in reference_data and "department_id" in df.columns:
            dept_df = reference_data["departments"]
            dept_ids = dept_df.select("department_id").distinct()
            
            invalid_dept = df.filter(
                (col("department_id").isNotNull())
            ).join(
                dept_ids,
                on="department_id",
                how="left_anti"
            ).count()
            
            if invalid_dept > 0:
                errors.append({
                    "type": "referential_integrity",
                    "field": "department_id",
                    "error_count": invalid_dept,
                    "message": f"{invalid_dept} records have invalid department_id"
                })
                self.logger.warning(
                    "Invalid department references found",
                    count=invalid_dept
                )
        
        # Check job_id exists in jobs
        if "jobs" in reference_data and "job_id" in df.columns:
            jobs_df = reference_data["jobs"]
            job_ids = jobs_df.select("job_id").distinct()
            
            invalid_job = df.filter(
                (col("job_id").isNotNull())
            ).join(
                job_ids,
                on="job_id",
                how="left_anti"
            ).count()
            
            if invalid_job > 0:
                errors.append({
                    "type": "referential_integrity",
                    "field": "job_id",
                    "error_count": invalid_job,
                    "message": f"{invalid_job} records have invalid job_id"
                })
                self.logger.warning(
                    "Invalid job references found",
                    count=invalid_job
                )
        
        # Check manager_id exists in employees (self-referential)
        if "employees" in reference_data and "manager_id" in df.columns:
            emp_df = reference_data["employees"]
            emp_ids = emp_df.select(col("employee_id").alias("manager_id")).distinct()
            
            invalid_mgr = df.filter(
                (col("manager_id").isNotNull())
            ).join(
                emp_ids,
                on="manager_id",
                how="left_anti"
            ).count()
            
            if invalid_mgr > 0:
                errors.append({
                    "type": "referential_integrity",
                    "field": "manager_id",
                    "error_count": invalid_mgr,
                    "message": f"{invalid_mgr} records have invalid manager_id"
                })
                self.logger.warning(
                    "Invalid manager references found",
                    count=invalid_mgr
                )
        
        # Check location_id exists in locations
        if "locations" in reference_data and "location_id" in df.columns:
            loc_df = reference_data["locations"]
            loc_ids = loc_df.select("location_id").distinct()
            
            invalid_loc = df.filter(
                (col("location_id").isNotNull())
            ).join(
                loc_ids,
                on="location_id",
                how="left_anti"
            ).count()
            
            if invalid_loc > 0:
                errors.append({
                    "type": "referential_integrity",
                    "field": "location_id",
                    "error_count": invalid_loc,
                    "message": f"{invalid_loc} records have invalid location_id"
                })
                self.logger.warning(
                    "Invalid location references found",
                    count=invalid_loc
                )
        
        return errors
    
    def _validate_cross_field_constraints(self, df: DataFrame) -> list:
        """
        Validate cross-field constraints (e.g., date ranges).
        
        Args:
            df: DataFrame to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        self.logger.debug("Validating cross-field constraints")
        
        # Validate start_date < end_date (for job_history)
        if "start_date" in df.columns and "end_date" in df.columns:
            invalid_dates = df.filter(
                (col("start_date").isNotNull()) &
                (col("end_date").isNotNull()) &
                (col("start_date") >= col("end_date"))
            ).count()
            
            if invalid_dates > 0:
                errors.append({
                    "type": "cross_field",
                    "fields": ["start_date", "end_date"],
                    "error_count": invalid_dates,
                    "message": f"{invalid_dates} records have start_date >= end_date"
                })
                self.logger.warning(
                    "Invalid date ranges found",
                    count=invalid_dates
                )
        
        # Validate hire_date <= current_date
        if "hire_date" in df.columns:
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            future_hires = df.filter(
                (col("hire_date").isNotNull()) &
                (col("hire_date") > lit(current_date))
            ).count()
            
            if future_hires > 0:
                errors.append({
                    "type": "cross_field",
                    "fields": ["hire_date"],
                    "error_count": future_hires,
                    "message": f"{future_hires} records have future hire_date"
                })
                self.logger.warning(
                    "Future hire dates found",
                    count=future_hires
                )
        
        # Validate salary >= min_salary and salary <= max_salary (if job data embedded)
        if all(field in df.columns for field in ["salary", "min_salary", "max_salary"]):
            salary_below_min = df.filter(
                (col("salary").isNotNull()) &
                (col("min_salary").isNotNull()) &
                (col("salary") < col("min_salary"))
            ).count()
            
            salary_above_max = df.filter(
                (col("salary").isNotNull()) &
                (col("max_salary").isNotNull()) &
                (col("salary") > col("max_salary"))
            ).count()
            
            if salary_below_min > 0:
                errors.append({
                    "type": "cross_field",
                    "fields": ["salary", "min_salary"],
                    "error_count": salary_below_min,
                    "message": f"{salary_below_min} records have salary < min_salary"
                })
                self.logger.warning(
                    "Salaries below minimum found",
                    count=salary_below_min
                )
            
            if salary_above_max > 0:
                errors.append({
                    "type": "cross_field",
                    "fields": ["salary", "max_salary"],
                    "error_count": salary_above_max,
                    "message": f"{salary_above_max} records have salary > max_salary"
                })
                self.logger.warning(
                    "Salaries above maximum found",
                    count=salary_above_max
                )
        
        # Validate commission_pct is between 0 and 1
        if "commission_pct" in df.columns:
            invalid_commission = df.filter(
                (col("commission_pct").isNotNull()) &
                ((col("commission_pct") < 0) | (col("commission_pct") > 1))
            ).count()
            
            if invalid_commission > 0:
                errors.append({
                    "type": "cross_field",
                    "fields": ["commission_pct"],
                    "error_count": invalid_commission,
                    "message": f"{invalid_commission} records have commission_pct outside [0, 1]"
                })
                self.logger.warning(
                    "Invalid commission percentages found",
                    count=invalid_commission
                )
        
        return errors
    
    def _validate_required_combinations(self, df: DataFrame) -> list:
        """
        Validate required field combinations.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        self.logger.debug("Validating required field combinations")
        
        # If commission_pct is set, employee should be in sales department
        # (This is domain-specific logic - adjust as needed)
        if "commission_pct" in df.columns and "department_id" in df.columns:
            # Assuming department_id 80 is Sales
            non_sales_with_commission = df.filter(
                (col("commission_pct").isNotNull()) &
                (col("commission_pct") > 0) &
                (col("department_id") != 80)
            ).count()
            
            if non_sales_with_commission > 0:
                # This might be a warning rather than error
                errors.append({
                    "type": "field_combination",
                    "fields": ["commission_pct", "department_id"],
                    "error_count": non_sales_with_commission,
                    "message": f"{non_sales_with_commission} non-sales employees have commission",
                    "severity": "warning"
                })
                self.logger.info(
                    "Non-sales employees with commission found",
                    count=non_sales_with_commission
                )
        
        # If manager_id is set, employee should have department
        if "manager_id" in df.columns and "department_id" in df.columns:
            managed_without_dept = df.filter(
                (col("manager_id").isNotNull()) &
                (col("department_id").isNull())
            ).count()
            
            if managed_without_dept > 0:
                errors.append({
                    "type": "field_combination",
                    "fields": ["manager_id", "department_id"],
                    "error_count": managed_without_dept,
                    "message": f"{managed_without_dept} employees have manager but no department"
                })
                self.logger.warning(
                    "Employees with manager but no department found",
                    count=managed_without_dept
                )
        
        return errors


# Example usage
if __name__ == "__main__":
    """
    Example usage of RecordValidator.
    """
    from pyspark.sql import SparkSession
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
    
    print("=" * 80)
    print("Record Validator - Example Usage")
    print("=" * 80)
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("RecordValidatorExample") \
        .master("local[*]") \
        .getOrCreate()
    
    # Create sample employee data
    emp_schema = StructType([
        StructField("employee_id", IntegerType(), True),
        StructField("first_name", StringType(), True),
        StructField("last_name", StringType(), True),
        StructField("email", StringType(), True),
        StructField("hire_date", StringType(), True),
        StructField("job_id", StringType(), True),
        StructField("salary", DoubleType(), True),
        StructField("commission_pct", DoubleType(), True),
        StructField("manager_id", IntegerType(), True),
        StructField("department_id", IntegerType(), True)
    ])
    
    emp_data = [
        (100, "Steven", "King", "SKING", "2003-06-17", "AD_PRES", 24000.0, None, None, 90),
        (101, "Neena", "Kochhar", "NKOCHHAR", "2005-09-21", "AD_VP", 17000.0, None, 100, 90),
        (102, "Lex", "De Haan", "LDEHAAN", "2001-01-13", "AD_VP", 17000.0, None, 100, 90),
        (103, "Alexander", "Hunold", "AHUNOLD", "2006-01-03", "IT_PROG", 9000.0, None, 102, 60),
        (104, "Bruce", "Ernst", "BERNST", "2007-05-21", "INVALID_JOB", 6000.0, None, 103, 60),  # Invalid job_id
        (105, "David", "Austin", "DAUSTIN", "2005-06-25", "IT_PROG", 4800.0, None, 103, 999),  # Invalid department_id
        (106, "Valli", "Pataballa", "VPATABAL", "2006-02-05", "IT_PROG", 4800.0, None, 999, 60),  # Invalid manager_id
    ]
    
    employees_df = spark.createDataFrame(emp_data, emp_schema)
    
    # Create reference data
    dept_data = [(90, "Executive"), (60, "IT"), (80, "Sales")]
    departments_df = spark.createDataFrame(dept_data, ["department_id", "department_name"])
    
    job_data = [("AD_PRES", "President"), ("AD_VP", "Vice President"), ("IT_PROG", "Programmer")]
    jobs_df = spark.createDataFrame(job_data, ["job_id", "job_title"])
    
    print("\n1. Sample Employee Data:")
    employees_df.show(truncate=False)
    
    print("\n2. Reference Data:")
    print("Departments:")
    departments_df.show()
    print("Jobs:")
    jobs_df.show()
    
    print("\n3. Running record validation...")
    
    validator = RecordValidator()
    result = validator.validate_with_metrics(
        employees_df,
        reference_data={
            "departments": departments_df,
            "jobs": jobs_df,
            "employees": employees_df  # For manager validation
        }
    )
    
    print("\n4. Validation Results:")
    print("=" * 80)
    print(f"Is Valid: {result.is_valid}")
    print(f"Total Records: {result.total_records}")
    print(f"Valid Records: {result.valid_records}")
    print(f"Invalid Records: {result.invalid_records}")
    print(f"Errors: {len(result.errors)}")
    
    if result.errors:
        print("\nValidation Errors:")
        for error in result.errors:
            severity = error.get('severity', 'error')
            icon = "⚠️ " if severity == "warning" else "❌"
            print(f"  {icon} {error['type']}: {error['message']}")
            if 'field' in error:
                print(f"     Field: {error['field']}")
            if 'fields' in error:
                print(f"     Fields: {', '.join(error['fields'])}")
    
    print("\n5. Metrics Report:")
    print(validator.metrics.generate_report())
    
    print("\n" + "=" * 80)
    if result.is_valid:
        print("✅ All record validations passed!")
    else:
        print("❌ Record validation failed - see errors above")
    print("=" * 80)
    
    spark.stop()

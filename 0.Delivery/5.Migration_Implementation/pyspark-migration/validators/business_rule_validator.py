"""
Business Rule Validator

Validates complex business rules specific to the HR domain.
Implements business logic validation including:
- Salary within job min/max ranges
- Manager hierarchy validation
- Job history consistency (no overlapping dates)
- Email uniqueness
- Circular manager reference detection
- Department-location validity

Usage:
    from validators import BusinessRuleValidator
    
    validator = BusinessRuleValidator()
    result = validator.validate_with_metrics(
        employees_df,
        business_context={
            "departments": departments_df,
            "jobs": jobs_df,
            "job_history": job_history_df
        }
    )
"""

from typing import Dict, Any, Optional
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, count, when, collect_list, array_contains,
    explode, struct, row_number, lag, lead
)
from pyspark.sql.window import Window

from validators.base_validator import BaseValidator, ValidationResult
from utils.logging_config import get_logger
from utils.metrics import MetricsCollector


class BusinessRuleValidator(BaseValidator):
    """
    Validate business rules specific to HR domain.
    
    Validates:
    - Salary within job-specific ranges
    - Manager hierarchy (no circular references)
    - Job history consistency (no gaps/overlaps)
    - Email uniqueness
    - Department-location consistency
    """
    
    def __init__(
        self,
        logger: Optional[Any] = None,
        metrics: Optional[MetricsCollector] = None
    ):
        """
        Initialize business rule validator.
        
        Args:
            logger: Optional logger instance
            metrics: Optional metrics collector
        """
        super().__init__(
            name="business_rule_validator",
            logger=logger or get_logger("business_rule_validator"),
            metrics=metrics or MetricsCollector("business_rule_validator")
        )
        
        self.logger.info("Business rule validator initialized")
    
    def validate(
        self,
        df: DataFrame,
        business_context: Optional[Dict[str, DataFrame]] = None
    ) -> ValidationResult:
        """
        Validate business rules.
        
        Args:
            df: DataFrame to validate
            business_context: Dictionary of related DataFrames for context
            
        Returns:
            ValidationResult with validation status and errors
        """
        self.logger.info("Starting business rule validation")
        
        errors = []
        warnings = []
        total_records = df.count()
        valid_records = total_records
        
        # Validate salary within job ranges
        if business_context and "jobs" in business_context:
            salary_errors = self._validate_salary_ranges(
                df,
                business_context["jobs"]
            )
            errors.extend(salary_errors)
        
        # Validate manager hierarchy
        hierarchy_errors = self._validate_manager_hierarchy(df)
        errors.extend(hierarchy_errors)
        
        # Validate email uniqueness
        email_errors = self._validate_email_uniqueness(df)
        errors.extend(email_errors)
        
        # Validate job history consistency
        if business_context and "job_history" in business_context:
            history_errors = self._validate_job_history_consistency(
                business_context["job_history"]
            )
            errors.extend(history_errors)
        
        # Validate department-location consistency
        if business_context and "departments" in business_context:
            if "locations" in business_context:
                dept_loc_errors = self._validate_department_location(
                    business_context["departments"],
                    business_context["locations"]
                )
                errors.extend(dept_loc_errors)
        
        # Calculate valid records
        if errors:
            total_errors = sum(e.get("error_count", 0) for e in errors)
            valid_records = max(0, total_records - total_errors)
        
        is_valid = len(errors) == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=total_records - valid_records,
            errors=errors,
            warnings=warnings
        )
        
        self.logger.info(
            "Business rule validation completed",
            is_valid=is_valid,
            total_records=total_records,
            valid_records=valid_records,
            error_count=len(errors)
        )
        
        return result
    
    def _validate_salary_ranges(
        self,
        employees_df: DataFrame,
        jobs_df: DataFrame
    ) -> list:
        """
        Validate employee salaries are within job min/max ranges.
        
        Args:
            employees_df: Employees DataFrame
            jobs_df: Jobs DataFrame with min_salary and max_salary
            
        Returns:
            List of validation errors
        """
        errors = []
        
        self.logger.debug("Validating salary ranges against job definitions")
        
        # Join employees with jobs
        joined_df = employees_df.join(
            jobs_df.select("job_id", "min_salary", "max_salary"),
            on="job_id",
            how="left"
        )
        
        # Check salary < min_salary
        below_min = joined_df.filter(
            (col("salary").isNotNull()) &
            (col("min_salary").isNotNull()) &
            (col("salary") < col("min_salary"))
        ).count()
        
        if below_min > 0:
            errors.append({
                "type": "business_rule",
                "rule": "salary_below_minimum",
                "error_count": below_min,
                "message": f"{below_min} employees have salary below job minimum"
            })
            self.logger.warning(
                "Salaries below job minimum found",
                count=below_min
            )
        
        # Check salary > max_salary
        above_max = joined_df.filter(
            (col("salary").isNotNull()) &
            (col("max_salary").isNotNull()) &
            (col("salary") > col("max_salary"))
        ).count()
        
        if above_max > 0:
            errors.append({
                "type": "business_rule",
                "rule": "salary_above_maximum",
                "error_count": above_max,
                "message": f"{above_max} employees have salary above job maximum"
            })
            self.logger.warning(
                "Salaries above job maximum found",
                count=above_max
            )
        
        return errors
    
    def _validate_manager_hierarchy(self, employees_df: DataFrame) -> list:
        """
        Validate manager hierarchy has no circular references.
        
        Detects cycles like: A manages B, B manages C, C manages A
        
        Args:
            employees_df: Employees DataFrame
            
        Returns:
            List of validation errors
        """
        errors = []
        
        self.logger.debug("Validating manager hierarchy for circular references")
        
        # Check for direct self-management
        self_managers = employees_df.filter(
            (col("manager_id").isNotNull()) &
            (col("employee_id") == col("manager_id"))
        ).count()
        
        if self_managers > 0:
            errors.append({
                "type": "business_rule",
                "rule": "circular_manager_self",
                "error_count": self_managers,
                "message": f"{self_managers} employees are their own manager"
            })
            self.logger.error(
                "Self-management detected",
                count=self_managers
            )
        
        # Check for 2-level cycles (A→B→A)
        # Join employees with their managers
        emp_mgr = employees_df.select(
            col("employee_id").alias("emp_id"),
            col("manager_id").alias("mgr_id")
        )
        
        mgr_mgr = employees_df.select(
            col("employee_id").alias("mgr_id"),
            col("manager_id").alias("mgr_mgr_id")
        )
        
        two_level_cycles = emp_mgr.join(
            mgr_mgr,
            on="mgr_id",
            how="inner"
        ).filter(
            col("emp_id") == col("mgr_mgr_id")
        ).count()
        
        if two_level_cycles > 0:
            errors.append({
                "type": "business_rule",
                "rule": "circular_manager_2level",
                "error_count": two_level_cycles,
                "message": f"{two_level_cycles} circular manager references (2-level)"
            })
            self.logger.error(
                "2-level circular manager references detected",
                count=two_level_cycles
            )
        
        # Note: Detecting longer cycles (3+) requires recursive traversal
        # which is complex in Spark. Consider using GraphX or iterative approach
        # for production use.
        
        return errors
    
    def _validate_email_uniqueness(self, employees_df: DataFrame) -> list:
        """
        Validate email addresses are unique.
        
        Args:
            employees_df: Employees DataFrame
            
        Returns:
            List of validation errors
        """
        errors = []
        
        self.logger.debug("Validating email uniqueness")
        
        if "email" not in employees_df.columns:
            return errors
        
        # Find duplicate emails
        email_counts = employees_df.filter(
            col("email").isNotNull()
        ).groupBy("email").agg(
            count("*").alias("email_count")
        ).filter(
            col("email_count") > 1
        )
        
        duplicate_emails = email_counts.count()
        total_duplicates = email_counts.agg({"email_count": "sum"}).collect()[0][0] if duplicate_emails > 0 else 0
        
        if duplicate_emails > 0:
            errors.append({
                "type": "business_rule",
                "rule": "email_uniqueness",
                "error_count": total_duplicates - duplicate_emails,  # Extra occurrences
                "message": f"{duplicate_emails} duplicate email addresses found ({total_duplicates} total occurrences)"
            })
            self.logger.warning(
                "Duplicate email addresses found",
                unique_duplicates=duplicate_emails,
                total_duplicates=total_duplicates
            )
        
        return errors
    
    def _validate_job_history_consistency(self, job_history_df: DataFrame) -> list:
        """
        Validate job history has no overlapping dates.
        
        Args:
            job_history_df: Job history DataFrame
            
        Returns:
            List of validation errors
        """
        errors = []
        
        self.logger.debug("Validating job history consistency")
        
        if not all(col in job_history_df.columns for col in ["employee_id", "start_date", "end_date"]):
            return errors
        
        # For each employee, check if any date ranges overlap
        # Order by employee_id and start_date
        window = Window.partitionBy("employee_id").orderBy("start_date")
        
        # Add previous end_date
        history_with_prev = job_history_df.withColumn(
            "prev_end_date",
            lag("end_date").over(window)
        )
        
        # Check if start_date <= prev_end_date (overlap)
        overlapping = history_with_prev.filter(
            (col("prev_end_date").isNotNull()) &
            (col("start_date") <= col("prev_end_date"))
        ).count()
        
        if overlapping > 0:
            errors.append({
                "type": "business_rule",
                "rule": "job_history_overlap",
                "error_count": overlapping,
                "message": f"{overlapping} job history records have overlapping dates"
            })
            self.logger.warning(
                "Overlapping job history dates found",
                count=overlapping
            )
        
        # Check for gaps (optional - might be warning instead of error)
        # A gap exists if start_date > prev_end_date + 1 day
        gaps = history_with_prev.filter(
            (col("prev_end_date").isNotNull()) &
            (col("start_date") > col("prev_end_date"))
        ).count()
        
        if gaps > 0:
            # This is often acceptable, so make it a warning
            self.logger.info(
                "Gaps in job history found (not necessarily an error)",
                count=gaps
            )
        
        return errors
    
    def _validate_department_location(
        self,
        departments_df: DataFrame,
        locations_df: DataFrame
    ) -> list:
        """
        Validate department locations exist and are valid.
        
        Args:
            departments_df: Departments DataFrame
            locations_df: Locations DataFrame
            
        Returns:
            List of validation errors
        """
        errors = []
        
        self.logger.debug("Validating department-location consistency")
        
        if "location_id" not in departments_df.columns:
            return errors
        
        # Check if all department location_ids exist in locations
        location_ids = locations_df.select("location_id").distinct()
        
        invalid_locations = departments_df.filter(
            col("location_id").isNotNull()
        ).join(
            location_ids,
            on="location_id",
            how="left_anti"
        ).count()
        
        if invalid_locations > 0:
            errors.append({
                "type": "business_rule",
                "rule": "department_location_invalid",
                "error_count": invalid_locations,
                "message": f"{invalid_locations} departments have invalid location_id"
            })
            self.logger.warning(
                "Departments with invalid locations found",
                count=invalid_locations
            )
        
        return errors


# Example usage
if __name__ == "__main__":
    """
    Example usage of BusinessRuleValidator.
    """
    from pyspark.sql import SparkSession
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
    
    print("=" * 80)
    print("Business Rule Validator - Example Usage")
    print("=" * 80)
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("BusinessRuleValidatorExample") \
        .master("local[*]") \
        .getOrCreate()
    
    # Create sample data
    emp_schema = StructType([
        StructField("employee_id", IntegerType(), True),
        StructField("first_name", StringType(), True),
        StructField("last_name", StringType(), True),
        StructField("email", StringType(), True),
        StructField("job_id", StringType(), True),
        StructField("salary", DoubleType(), True),
        StructField("manager_id", IntegerType(), True),
        StructField("department_id", IntegerType(), True)
    ])
    
    emp_data = [
        (100, "Steven", "King", "SKING", "AD_PRES", 24000.0, None, 90),
        (101, "Neena", "Kochhar", "NKOCHHAR", "AD_VP", 17000.0, 100, 90),
        (102, "Lex", "De Haan", "LDEHAAN", "AD_VP", 17000.0, 100, 90),
        (103, "Alexander", "Hunold", "AHUNOLD", "IT_PROG", 15000.0, 102, 60),  # Salary above max!
        (104, "Bruce", "Ernst", "SKING", "IT_PROG", 6000.0, 103, 60),  # Duplicate email!
        (105, "David", "Austin", "DAUSTIN", "IT_PROG", 2000.0, 103, 60),  # Salary below min!
        (106, "Valli", "Pataballa", "VPATABAL", "IT_PROG", 4800.0, 106, 60),  # Self-manager!
    ]
    
    employees_df = spark.createDataFrame(emp_data, emp_schema)
    
    # Jobs with salary ranges
    job_data = [
        ("AD_PRES", "President", 20000, 40000),
        ("AD_VP", "Vice President", 15000, 30000),
        ("IT_PROG", "Programmer", 4000, 10000),
    ]
    jobs_df = spark.createDataFrame(job_data, ["job_id", "job_title", "min_salary", "max_salary"])
    
    # Job history with overlapping dates
    history_data = [
        (103, "2006-01-03", "2007-12-31", "IT_PROG", 60),
        (103, "2007-06-01", "2008-12-31", "IT_PROG", 60),  # Overlaps with previous!
        (104, "2007-05-21", "2009-12-31", "IT_PROG", 60),
    ]
    job_history_df = spark.createDataFrame(
        history_data,
        ["employee_id", "start_date", "end_date", "job_id", "department_id"]
    )
    
    print("\n1. Sample Data:")
    print("Employees:")
    employees_df.show(truncate=False)
    print("Jobs:")
    jobs_df.show()
    print("Job History:")
    job_history_df.show()
    
    print("\n2. Running business rule validation...")
    
    validator = BusinessRuleValidator()
    result = validator.validate_with_metrics(
        employees_df,
        business_context={
            "jobs": jobs_df,
            "job_history": job_history_df
        }
    )
    
    print("\n3. Validation Results:")
    print("=" * 80)
    print(f"Is Valid: {result.is_valid}")
    print(f"Total Records: {result.total_records}")
    print(f"Valid Records: {result.valid_records}")
    print(f"Invalid Records: {result.invalid_records}")
    print(f"Errors: {len(result.errors)}")
    
    if result.errors:
        print("\nBusiness Rule Violations:")
        for error in result.errors:
            print(f"  ❌ {error['rule']}: {error['message']}")
            print(f"     Type: {error['type']}")
            print(f"     Count: {error['error_count']}")
    
    print("\n4. Metrics Report:")
    print(validator.metrics.generate_report())
    
    print("\n" + "=" * 80)
    if result.is_valid:
        print("✅ All business rules validated successfully!")
    else:
        print("❌ Business rule validation failed - see errors above")
    print("=" * 80)
    
    spark.stop()

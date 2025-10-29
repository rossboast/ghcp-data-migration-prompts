"""
Field Validator

Validates individual field values in DataFrames.
Implements field-level validation rules including:
- NOT NULL checks
- Type validation
- Format validation (email, phone, patterns)
- Range validation (min/max values)
- Length validation

Usage:
    from validators import FieldValidator
    from config.transformation_config import VALIDATION_RULES
    
    validator = FieldValidator(VALIDATION_RULES)
    result = validator.validate_with_metrics(df)
    
    if result.is_valid:
        print("✅ All field validations passed")
    else:
        print(f"❌ {len(result.errors)} validation errors")
"""

from typing import Dict, Any, List, Optional
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, when, length, regexp_extract, lit, concat

from validators.base_validator import BaseValidator, ValidationResult
from utils.logging_config import get_logger
from utils.metrics import MetricsCollector


class FieldValidator(BaseValidator):
    """
    Validate individual field values.
    
    Supports:
    - NOT_NULL: Field must not be null
    - POSITIVE: Numeric field must be > 0
    - NON_NEGATIVE: Numeric field must be >= 0
    - EMAIL_FORMAT: Must match email pattern
    - PHONE_FORMAT: Must match phone pattern
    - DATE_RANGE: Date must be within range
    - SALARY_RANGE: Salary must be within range
    - LENGTH_MIN: String length >= min
    - LENGTH_MAX: String length <= max
    - PATTERN: Must match regex pattern
    """
    
    def __init__(
        self,
        validation_rules: Dict[str, List[str]],
        spark: Optional[SparkSession] = None,
        logger: Optional[Any] = None,
        metrics: Optional[Any] = None
    ):
        """
        Initialize field validator.
        
        Args:
            validation_rules: Dictionary mapping field names to validation rule names
            spark: Optional SparkSession (not used, for compatibility)
            logger: Optional logger instance
            metrics: Optional metrics collector
        """
        # Note: BaseValidator expects different params, but field_validator uses simpler initialization
        # We'll just set attributes directly for now to avoid breaking changes
        self.validation_rules = validation_rules
        self.logger = logger or get_logger("field_validator")
        self.metrics = metrics  # Don't instantiate MetricsCollector, just keep None or passed value
        
        self.logger.info(
            "Field validator initialized",
            rules_count=len(validation_rules)
        )
    
    def get_validation_rules(self) -> List[str]:
        """
        Get list of validation rules applied by this validator.
        
        Returns:
            List of rule descriptions
        """
        rules = []
        for field_name, field_rules in self.validation_rules.items():
            for rule in field_rules:
                rules.append(f"{field_name}: {rule}")
        return rules
    
    def validate(self, df: DataFrame) -> ValidationResult:
        """
        Validate all fields according to rules.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            ValidationResult with validation status and errors
        """
        self.logger.info("Starting field validation")
        
        errors = []
        warnings = []
        total_records = df.count()
        valid_records = total_records
        
        # Validate each field
        for field_name, rules in self.validation_rules.items():
            if field_name not in df.columns:
                self.logger.warning(
                    f"Field {field_name} not found in DataFrame",
                    field=field_name
                )
                continue
            
            for rule in rules:
                self.logger.debug(f"Validating {field_name} with rule: {rule}")
                
                # Apply validation rule
                if rule == "NOT_NULL":
                    error_count = self._validate_not_null(df, field_name)
                elif rule == "POSITIVE":
                    error_count = self._validate_positive(df, field_name)
                elif rule == "NON_NEGATIVE":
                    error_count = self._validate_non_negative(df, field_name)
                elif rule == "EMAIL_FORMAT":
                    error_count = self._validate_email_format(df, field_name)
                elif rule == "PHONE_FORMAT":
                    error_count = self._validate_phone_format(df, field_name)
                elif rule.startswith("DATE_RANGE"):
                    error_count = self._validate_date_range(df, field_name, rule)
                elif rule.startswith("SALARY_RANGE"):
                    error_count = self._validate_salary_range(df, field_name, rule)
                elif rule.startswith("LENGTH_MIN"):
                    min_length = int(rule.split(":")[1])
                    error_count = self._validate_length_min(df, field_name, min_length)
                elif rule.startswith("LENGTH_MAX"):
                    max_length = int(rule.split(":")[1])
                    error_count = self._validate_length_max(df, field_name, max_length)
                elif rule.startswith("PATTERN"):
                    pattern = rule.split(":", 1)[1]
                    error_count = self._validate_pattern(df, field_name, pattern)
                else:
                    self.logger.warning(f"Unknown validation rule: {rule}")
                    continue
                
                if error_count > 0:
                    errors.append({
                        "field": field_name,
                        "rule": rule,
                        "error_count": error_count,
                        "message": f"{field_name} failed {rule} validation ({error_count} records)"
                    })
                    self.logger.warning(
                        f"Validation failed for {field_name}",
                        field=field_name,
                        rule=rule,
                        error_count=error_count
                    )
        
        # Calculate invalid records (records with errors)
        if errors:
            # This is an approximation - in reality, some records may have multiple errors
            total_errors = sum(e["error_count"] for e in errors)
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
            "Field validation completed",
            is_valid=is_valid,
            total_records=total_records,
            valid_records=valid_records,
            error_count=len(errors)
        )
        
        return result
    
    def _validate_not_null(self, df: DataFrame, field_name: str) -> int:
        """Validate field is not null."""
        return df.filter(col(field_name).isNull()).count()
    
    def _validate_positive(self, df: DataFrame, field_name: str) -> int:
        """Validate numeric field is positive (> 0)."""
        return df.filter((col(field_name).isNotNull()) & (col(field_name) <= 0)).count()
    
    def _validate_non_negative(self, df: DataFrame, field_name: str) -> int:
        """Validate numeric field is non-negative (>= 0)."""
        return df.filter((col(field_name).isNotNull()) & (col(field_name) < 0)).count()
    
    def _validate_email_format(self, df: DataFrame, field_name: str) -> int:
        """Validate email format."""
        # Simple email pattern: xxx@xxx.xxx
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        return df.filter(
            (col(field_name).isNotNull()) &
            (~col(field_name).rlike(email_pattern))
        ).count()
    
    def _validate_phone_format(self, df: DataFrame, field_name: str) -> int:
        """Validate phone format."""
        # Pattern: allows various formats like 123-456-7890, (123) 456-7890, etc.
        phone_pattern = r'^[\d\s\-\(\)\+\.]+$'
        
        return df.filter(
            (col(field_name).isNotNull()) &
            (~col(field_name).rlike(phone_pattern))
        ).count()
    
    def _validate_date_range(self, df: DataFrame, field_name: str, rule: str) -> int:
        """
        Validate date is within range.
        
        Rule format: DATE_RANGE:1990-01-01:2030-12-31
        """
        parts = rule.split(":")
        if len(parts) != 3:
            self.logger.warning(f"Invalid DATE_RANGE rule format: {rule}")
            return 0
        
        min_date = parts[1]
        max_date = parts[2]
        
        return df.filter(
            (col(field_name).isNotNull()) &
            ((col(field_name) < lit(min_date)) | (col(field_name) > lit(max_date)))
        ).count()
    
    def _validate_salary_range(self, df: DataFrame, field_name: str, rule: str) -> int:
        """
        Validate salary is within range.
        
        Rule format: SALARY_RANGE:0:1000000
        """
        parts = rule.split(":")
        if len(parts) != 3:
            self.logger.warning(f"Invalid SALARY_RANGE rule format: {rule}")
            return 0
        
        min_salary = float(parts[1])
        max_salary = float(parts[2])
        
        return df.filter(
            (col(field_name).isNotNull()) &
            ((col(field_name) < lit(min_salary)) | (col(field_name) > lit(max_salary)))
        ).count()
    
    def _validate_length_min(self, df: DataFrame, field_name: str, min_length: int) -> int:
        """Validate string length is at least min_length."""
        return df.filter(
            (col(field_name).isNotNull()) &
            (length(col(field_name)) < lit(min_length))
        ).count()
    
    def _validate_length_max(self, df: DataFrame, field_name: str, max_length: int) -> int:
        """Validate string length is at most max_length."""
        return df.filter(
            (col(field_name).isNotNull()) &
            (length(col(field_name)) > lit(max_length))
        ).count()
    
    def _validate_pattern(self, df: DataFrame, field_name: str, pattern: str) -> int:
        """Validate field matches regex pattern."""
        return df.filter(
            (col(field_name).isNotNull()) &
            (~col(field_name).rlike(pattern))
        ).count()


# Example usage
if __name__ == "__main__":
    """
    Example usage of FieldValidator.
    """
    from pyspark.sql import SparkSession
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType
    
    print("=" * 80)
    print("Field Validator - Example Usage")
    print("=" * 80)
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("FieldValidatorExample") \
        .master("local[*]") \
        .getOrCreate()
    
    # Create sample data with some invalid records
    schema = StructType([
        StructField("employee_id", IntegerType(), True),
        StructField("first_name", StringType(), True),
        StructField("last_name", StringType(), True),
        StructField("email", StringType(), True),
        StructField("phone_number", StringType(), True),
        StructField("salary", DoubleType(), True),
        StructField("commission_pct", DoubleType(), True)
    ])
    
    data = [
        (100, "Steven", "King", "SKING@example.com", "515-123-4567", 24000.0, 0.2),
        (101, "Neena", "Kochhar", "NKOCHHAR@example.com", "515-123-4568", 17000.0, None),
        (102, None, "De Haan", "invalid-email", "515-123-4569", -5000.0, 0.1),  # Invalid: null name, invalid email, negative salary
        (103, "Alexander", "Hunold", "AHUNOLD@example.com", "590-423-4567", 9000.0, None),
        (104, "Bruce", None, "BERNST@example.com", "590-423-4568", 6000.0, None),  # Invalid: null last_name
        (105, "David", "Austin", "not-an-email", "abc", 4800.0, None),  # Invalid: bad email, bad phone
    ]
    
    df = spark.createDataFrame(data, schema)
    
    print("\n1. Sample Data:")
    df.show(truncate=False)
    
    print("\n2. Setting up validation rules...")
    
    validation_rules = {
        "employee_id": ["NOT_NULL", "POSITIVE"],
        "first_name": ["NOT_NULL", "LENGTH_MIN:2"],
        "last_name": ["NOT_NULL", "LENGTH_MIN:2"],
        "email": ["NOT_NULL", "EMAIL_FORMAT"],
        "phone_number": ["PHONE_FORMAT"],
        "salary": ["NOT_NULL", "POSITIVE", "SALARY_RANGE:1000:100000"],
        "commission_pct": ["NON_NEGATIVE"]
    }
    
    print("✅ Rules configured:")
    for field, rules in validation_rules.items():
        print(f"   - {field}: {', '.join(rules)}")
    
    print("\n3. Running field validation...")
    
    validator = FieldValidator(validation_rules)
    result = validator.validate_with_metrics(df)
    
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
            print(f"  ❌ {error['field']} - {error['rule']}: {error['error_count']} records")
            print(f"     {error['message']}")
    
    print("\n5. Metrics Report:")
    print(validator.metrics.generate_report())
    
    print("\n" + "=" * 80)
    if result.is_valid:
        print("✅ All field validations passed!")
    else:
        print("❌ Field validation failed - see errors above")
    print("=" * 80)
    
    spark.stop()

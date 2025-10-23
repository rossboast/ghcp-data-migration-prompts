"""
Base Validator

This module defines the abstract base class for all data validators.
Validators are responsible for checking data quality and integrity.

All concrete validator implementations should inherit from BaseValidator
and implement the required abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from utils import get_logger, MigrationMetrics, Timer, ErrorContext, ValidationError, ErrorCollector


@dataclass
class ValidationResult:
    """
    Result of a validation check.
    
    Attributes:
        is_valid: Whether validation passed
        validation_name: Name of the validation check
        total_records: Total number of records checked
        invalid_records: Number of invalid records
        error_messages: List of error messages
        warnings: List of warning messages
        details: Additional details about the validation
    """
    is_valid: bool
    validation_name: str
    total_records: int = 0
    invalid_records: int = 0
    error_messages: List[str] = None
    warnings: List[str] = None
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []
        if self.warnings is None:
            self.warnings = []
        if self.details is None:
            self.details = {}
    
    @property
    def valid_records(self) -> int:
        """Calculate number of valid records."""
        return self.total_records - self.invalid_records
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_records == 0:
            return 100.0
        return (self.valid_records / self.total_records) * 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "validation_name": self.validation_name,
            "total_records": self.total_records,
            "invalid_records": self.invalid_records,
            "valid_records": self.valid_records,
            "success_rate": self.success_rate,
            "error_messages": self.error_messages,
            "warnings": self.warnings,
            "details": self.details,
        }


class BaseValidator(ABC):
    """
    Abstract base class for all data validators.
    
    This class provides common functionality for validating data and
    defines the interface that all validators must implement.
    
    Attributes:
        spark: SparkSession instance
        validator_name: Name of this validator
        metrics: MigrationMetrics instance for tracking validation metrics
        logger: Logger instance for this validator
        error_collector: ErrorCollector for collecting validation errors
    """
    
    def __init__(
        self,
        spark: SparkSession,
        validator_name: str,
        metrics: Optional[MigrationMetrics] = None,
        max_errors: int = 100
    ):
        """
        Initialize the base validator.
        
        Args:
            spark: SparkSession instance
            validator_name: Name of this validator
            metrics: Optional MigrationMetrics instance for tracking
            max_errors: Maximum number of errors to collect before stopping
        """
        self.spark = spark
        self.validator_name = validator_name
        self.metrics = metrics or MigrationMetrics(feed_name=validator_name)
        self.error_collector = ErrorCollector(max_errors=max_errors)
        self.logger = get_logger(
            self.__class__.__name__,
            validator=validator_name
        )
        
        self.logger.info(
            "Validator initialized",
            validator_class=self.__class__.__name__,
            validator_name=validator_name,
            max_errors=max_errors
        )
    
    @abstractmethod
    def validate(self, df: DataFrame, **kwargs) -> ValidationResult:
        """
        Validate the input DataFrame.
        
        This is the main method that concrete validators must implement.
        It should return a ValidationResult indicating success or failure.
        
        Args:
            df: Input DataFrame to validate
            **kwargs: Additional parameters specific to the validator
            
        Returns:
            ValidationResult containing validation outcome and details
        """
        pass
    
    @abstractmethod
    def get_validation_rules(self) -> List[str]:
        """
        Get list of validation rules applied by this validator.
        
        Returns:
            List of rule descriptions
        """
        pass
    
    def validate_with_metrics(
        self,
        df: DataFrame,
        **kwargs
    ) -> ValidationResult:
        """
        Validate data and track metrics.
        
        This wrapper method calls the concrete validate() implementation
        and tracks validation metrics (duration, error count).
        
        Args:
            df: Input DataFrame
            **kwargs: Additional parameters
            
        Returns:
            ValidationResult
            
        Raises:
            ValidationError: If validation fails critically
        """
        record_count = df.count()
        
        self.logger.info(
            "Starting validation",
            validator=self.validator_name,
            record_count=record_count,
            kwargs=kwargs
        )
        
        with Timer() as timer:
            try:
                with ErrorContext("validation", validator=self.validator_name):
                    # Call the concrete implementation
                    result = self.validate(df, **kwargs)
                    
                    # Update metrics
                    self.metrics.records_validated += result.valid_records
                    self.metrics.validation_duration_seconds = timer.elapsed_seconds
                    
                    if not result.is_valid:
                        self.metrics.validation_errors += result.invalid_records
                    
                    self.logger.info(
                        "Validation completed",
                        validator=self.validator_name,
                        is_valid=result.is_valid,
                        total_records=result.total_records,
                        invalid_records=result.invalid_records,
                        success_rate=result.success_rate,
                        duration_seconds=timer.elapsed_seconds
                    )
                    
                    return result
                    
            except Exception as e:
                self.metrics.validation_errors += record_count
                self.logger.error(
                    "Validation failed with exception",
                    validator=self.validator_name,
                    error=str(e),
                    duration_seconds=timer.elapsed_seconds
                )
                raise ValidationError(
                    f"Validation failed in {self.validator_name}: {str(e)}"
                ) from e
    
    def validate_multiple(
        self,
        df: DataFrame,
        validators: List['BaseValidator']
    ) -> List[ValidationResult]:
        """
        Run multiple validators on the same DataFrame.
        
        Args:
            df: Input DataFrame
            validators: List of validators to run
            
        Returns:
            List of ValidationResults
        """
        self.logger.info(
            "Running multiple validators",
            num_validators=len(validators)
        )
        
        results = []
        
        for validator in validators:
            result = validator.validate_with_metrics(df)
            results.append(result)
            
            if not result.is_valid:
                self.logger.warning(
                    "Validator failed",
                    validator_name=validator.validator_name,
                    invalid_records=result.invalid_records
                )
        
        # Summary
        total_invalid = sum(r.invalid_records for r in results)
        failed_validators = sum(1 for r in results if not r.is_valid)
        
        self.logger.info(
            "Multiple validation completed",
            total_validators=len(validators),
            failed_validators=failed_validators,
            total_invalid_records=total_invalid
        )
        
        return results
    
    def check_not_null(
        self,
        df: DataFrame,
        column_name: str
    ) -> ValidationResult:
        """
        Check that a column contains no null values.
        
        Args:
            df: Input DataFrame
            column_name: Name of column to check
            
        Returns:
            ValidationResult
        """
        total_count = df.count()
        null_count = df.filter(col(column_name).isNull()).count()
        
        is_valid = null_count == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            validation_name=f"not_null_{column_name}",
            total_records=total_count,
            invalid_records=null_count,
            details={"column": column_name, "null_count": null_count}
        )
        
        if not is_valid:
            result.error_messages.append(
                f"Column '{column_name}' contains {null_count} null values"
            )
        
        return result
    
    def check_unique(
        self,
        df: DataFrame,
        column_names: List[str]
    ) -> ValidationResult:
        """
        Check that column(s) contain only unique values.
        
        Args:
            df: Input DataFrame
            column_names: List of columns that should be unique
            
        Returns:
            ValidationResult
        """
        total_count = df.count()
        distinct_count = df.select(*column_names).distinct().count()
        duplicate_count = total_count - distinct_count
        
        is_valid = duplicate_count == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            validation_name=f"unique_{'_'.join(column_names)}",
            total_records=total_count,
            invalid_records=duplicate_count,
            details={
                "columns": column_names,
                "duplicate_count": duplicate_count
            }
        )
        
        if not is_valid:
            result.error_messages.append(
                f"Columns {column_names} contain {duplicate_count} duplicate values"
            )
        
        return result
    
    def check_range(
        self,
        df: DataFrame,
        column_name: str,
        min_value: Any,
        max_value: Any
    ) -> ValidationResult:
        """
        Check that column values are within a specified range.
        
        Args:
            df: Input DataFrame
            column_name: Name of column to check
            min_value: Minimum acceptable value
            max_value: Maximum acceptable value
            
        Returns:
            ValidationResult
        """
        total_count = df.count()
        
        out_of_range = df.filter(
            (col(column_name) < min_value) | 
            (col(column_name) > max_value)
        )
        
        invalid_count = out_of_range.count()
        is_valid = invalid_count == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            validation_name=f"range_{column_name}",
            total_records=total_count,
            invalid_records=invalid_count,
            details={
                "column": column_name,
                "min_value": min_value,
                "max_value": max_value,
                "out_of_range_count": invalid_count
            }
        )
        
        if not is_valid:
            result.error_messages.append(
                f"Column '{column_name}' has {invalid_count} values outside range [{min_value}, {max_value}]"
            )
        
        return result
    
    def check_pattern(
        self,
        df: DataFrame,
        column_name: str,
        pattern: str
    ) -> ValidationResult:
        """
        Check that column values match a regex pattern.
        
        Args:
            df: Input DataFrame
            column_name: Name of column to check
            pattern: Regex pattern to match
            
        Returns:
            ValidationResult
        """
        from pyspark.sql.functions import regexp_extract
        
        total_count = df.count()
        
        # Count records that don't match the pattern
        invalid = df.filter(
            ~col(column_name).rlike(pattern) & 
            col(column_name).isNotNull()
        )
        
        invalid_count = invalid.count()
        is_valid = invalid_count == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            validation_name=f"pattern_{column_name}",
            total_records=total_count,
            invalid_records=invalid_count,
            details={
                "column": column_name,
                "pattern": pattern,
                "invalid_count": invalid_count
            }
        )
        
        if not is_valid:
            result.error_messages.append(
                f"Column '{column_name}' has {invalid_count} values not matching pattern '{pattern}'"
            )
        
        return result
    
    def generate_report(
        self,
        results: List[ValidationResult]
    ) -> str:
        """
        Generate a formatted validation report.
        
        Args:
            results: List of ValidationResults
            
        Returns:
            Formatted report string
        """
        lines = [
            "\n" + "=" * 60,
            f"Validation Report: {self.validator_name}",
            "=" * 60,
            f"Total Validations: {len(results)}",
            f"Passed: {sum(1 for r in results if r.is_valid)}",
            f"Failed: {sum(1 for r in results if not r.is_valid)}",
            "",
        ]
        
        for result in results:
            status = "✓ PASS" if result.is_valid else "✗ FAIL"
            lines.append(f"{status} - {result.validation_name}")
            lines.append(f"  Records: {result.valid_records}/{result.total_records} ({result.success_rate:.1f}%)")
            
            if result.error_messages:
                for msg in result.error_messages:
                    lines.append(f"  Error: {msg}")
            
            if result.warnings:
                for msg in result.warnings:
                    lines.append(f"  Warning: {msg}")
            
            lines.append("")
        
        lines.append("=" * 60 + "\n")
        
        return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    from utils import get_spark_session
    
    # Demo validator for testing
    class DemoValidator(BaseValidator):
        """Demo validator for testing."""
        
        def validate(self, df: DataFrame, **kwargs) -> ValidationResult:
            """Validate that all IDs are positive."""
            total = df.count()
            invalid = df.filter(col("id") <= 0).count()
            
            return ValidationResult(
                is_valid=invalid == 0,
                validation_name="positive_id",
                total_records=total,
                invalid_records=invalid
            )
        
        def get_validation_rules(self) -> List[str]:
            """Get validation rules."""
            return ["ID must be positive"]
    
    # Test the validator
    spark = get_spark_session(app_name="TestValidator")
    
    # Create test data
    data = [(1, "Alice"), (2, "Bob"), (-1, "Invalid")]
    df = spark.createDataFrame(data, ["id", "name"])
    
    validator = DemoValidator(spark, "Demo Validator")
    
    result = validator.validate_with_metrics(df)
    
    print("\nValidation Result:")
    print(f"Is Valid: {result.is_valid}")
    print(f"Success Rate: {result.success_rate:.1f}%")
    print(f"Invalid Records: {result.invalid_records}")
    
    print("\nMetrics:")
    print(f"Records validated: {validator.metrics.records_validated}")
    print(f"Validation errors: {validator.metrics.validation_errors}")

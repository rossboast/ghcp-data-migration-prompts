"""
Data Type Converter

Utility functions for converting Oracle data types to JSON-compatible types
for storage in Azure Cosmos DB.

Handles:
- DATE → ISO 8601 strings
- NUMBER → int/float based on scale
- VARCHAR2 → trimmed strings
- NULL handling strategies
- TIMESTAMP → ISO 8601 with timezone

Usage:
    from transformers.data_type_converter import DataTypeConverter
    
    # Convert dates
    df = DataTypeConverter.convert_dates_to_iso(df, ["hire_date", "birth_date"])
    
    # Convert numbers
    df = DataTypeConverter.convert_numbers(df, {"salary": "decimal", "employee_id": "integer"})
    
    # Trim strings
    df = DataTypeConverter.trim_strings(df, ["first_name", "last_name", "email"])
"""

from typing import List, Dict, Optional, Any
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, trim, upper, lower, when, regexp_replace,
    date_format, to_date, to_timestamp, unix_timestamp,
    round as spark_round, cast, coalesce, lit
)
from pyspark.sql.types import StringType, IntegerType, DoubleType, DecimalType, BooleanType

from utils.logging_config import get_logger


class DataTypeConverter:
    """
    Static utility class for Oracle to JSON data type conversions.
    
    All methods are static and return transformed DataFrames.
    """
    
    logger = get_logger("data_type_converter")
    
    # ISO 8601 date format
    ISO_DATE_FORMAT = "yyyy-MM-dd"
    ISO_DATETIME_FORMAT = "yyyy-MM-dd'T'HH:mm:ss'Z'"
    ISO_DATETIME_TZ_FORMAT = "yyyy-MM-dd'T'HH:mm:ssXXX"
    
    # ========== Helper methods for single value conversions ==========
    
    @staticmethod
    def convert_date_to_iso_string(value) -> Optional[str]:
        """
        Convert a single Python date object to ISO 8601 string.
        
        Args:
            value: Python date object or None
            
        Returns:
            ISO date string (YYYY-MM-DD) or None
        """
        if value is None:
            return None
        from datetime import date
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        return str(value)
    
    @staticmethod
    def convert_timestamp_to_iso_string(value) -> Optional[str]:
        """
        Convert a single Python datetime object to ISO 8601 string.
        
        Args:
            value: Python datetime object or None
            
        Returns:
            ISO datetime string (YYYY-MM-DDTHH:MM:SS) or None
        """
        if value is None:
            return None
        from datetime import datetime
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%dT%H:%M:%S")
        return str(value)
    
    @staticmethod
    def convert_decimal_to_number(value) -> Optional[float]:
        """
        Convert a Decimal to float.
        
        Args:
            value: Decimal object or None
            
        Returns:
            Float value or None
        """
        if value is None:
            return None
        from decimal import Decimal
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    
    # ========== DataFrame transformation methods ==========
    
    @staticmethod
    def convert_dates_to_iso(
        df: DataFrame,
        date_columns: List[str],
        include_time: bool = False,
        null_value: Optional[str] = None
    ) -> DataFrame:
        """
        Convert Oracle DATE columns to ISO 8601 string format.
        
        Args:
            df: Input DataFrame
            date_columns: List of date column names to convert
            include_time: If True, include time component (default: False)
            null_value: Value to use for NULL dates (default: None keeps NULL)
            
        Returns:
            DataFrame with dates converted to ISO strings
            
        Examples:
            # Convert to date only (2023-01-15)
            df = convert_dates_to_iso(df, ["hire_date"])
            
            # Convert to datetime (2023-01-15T10:30:00Z)
            df = convert_dates_to_iso(df, ["created_at"], include_time=True)
            
            # Replace NULLs
            df = convert_dates_to_iso(df, ["end_date"], null_value="9999-12-31")
        """
        DataTypeConverter.logger.debug(
            "Converting dates to ISO format",
            columns=date_columns,
            include_time=include_time
        )
        
        result_df = df
        format_str = DataTypeConverter.ISO_DATETIME_FORMAT if include_time else DataTypeConverter.ISO_DATE_FORMAT
        
        for col_name in date_columns:
            if col_name not in df.columns:
                DataTypeConverter.logger.warning(
                    f"Date column '{col_name}' not found in DataFrame",
                    available_columns=df.columns
                )
                continue
            
            # Convert to string in ISO format
            converted_col = date_format(col(col_name), format_str)
            
            # Handle NULLs if specified
            if null_value is not None:
                converted_col = coalesce(converted_col, lit(null_value))
            
            result_df = result_df.withColumn(col_name, converted_col)
        
        return result_df
    
    @staticmethod
    def convert_timestamps_to_iso(
        df: DataFrame,
        timestamp_columns: List[str],
        include_timezone: bool = False,
        null_value: Optional[str] = None
    ) -> DataFrame:
        """
        Convert Oracle TIMESTAMP columns to ISO 8601 string format.
        
        Args:
            df: Input DataFrame
            timestamp_columns: List of timestamp column names
            include_timezone: If True, include timezone offset
            null_value: Value to use for NULL timestamps
            
        Returns:
            DataFrame with timestamps converted to ISO strings
        """
        DataTypeConverter.logger.debug(
            "Converting timestamps to ISO format",
            columns=timestamp_columns,
            include_timezone=include_timezone
        )
        
        result_df = df
        format_str = DataTypeConverter.ISO_DATETIME_TZ_FORMAT if include_timezone else DataTypeConverter.ISO_DATETIME_FORMAT
        
        for col_name in timestamp_columns:
            if col_name not in df.columns:
                DataTypeConverter.logger.warning(
                    f"Timestamp column '{col_name}' not found in DataFrame"
                )
                continue
            
            # Convert to string in ISO format
            converted_col = date_format(col(col_name), format_str)
            
            # Handle NULLs if specified
            if null_value is not None:
                converted_col = coalesce(converted_col, lit(null_value))
            
            result_df = result_df.withColumn(col_name, converted_col)
        
        return result_df
    
    @staticmethod
    def convert_numbers(
        df: DataFrame,
        number_columns: Dict[str, str],
        decimal_scale: int = 2
    ) -> DataFrame:
        """
        Convert Oracle NUMBER columns to appropriate numeric types.
        
        Args:
            df: Input DataFrame
            number_columns: Dict mapping column names to types ('integer', 'double', 'decimal')
            decimal_scale: Scale for decimal columns (default: 2)
            
        Returns:
            DataFrame with numbers converted to specified types
            
        Examples:
            df = convert_numbers(df, {
                "employee_id": "integer",
                "salary": "decimal",
                "commission_pct": "double"
            })
        """
        DataTypeConverter.logger.debug(
            "Converting numeric columns",
            columns=list(number_columns.keys())
        )
        
        result_df = df
        
        for col_name, col_type in number_columns.items():
            if col_name not in df.columns:
                DataTypeConverter.logger.warning(
                    f"Numeric column '{col_name}' not found in DataFrame"
                )
                continue
            
            if col_type == "integer":
                result_df = result_df.withColumn(col_name, col(col_name).cast(IntegerType()))
            elif col_type == "double":
                result_df = result_df.withColumn(col_name, col(col_name).cast(DoubleType()))
            elif col_type == "decimal":
                result_df = result_df.withColumn(
                    col_name,
                    spark_round(col(col_name), decimal_scale).cast(DecimalType(18, decimal_scale))
                )
            else:
                DataTypeConverter.logger.warning(
                    f"Unknown numeric type '{col_type}' for column '{col_name}'"
                )
        
        return result_df
    
    @staticmethod
    def trim_strings(
        df: DataFrame,
        string_columns: List[str],
        remove_extra_spaces: bool = True
    ) -> DataFrame:
        """
        Trim whitespace from VARCHAR2/CHAR columns.
        
        Args:
            df: Input DataFrame
            string_columns: List of string column names to trim
            remove_extra_spaces: If True, also remove extra spaces within strings
            
        Returns:
            DataFrame with trimmed strings
            
        Examples:
            # Basic trim
            df = trim_strings(df, ["first_name", "last_name"])
            
            # Trim and remove extra spaces
            df = trim_strings(df, ["address"], remove_extra_spaces=True)
        """
        DataTypeConverter.logger.debug(
            "Trimming string columns",
            columns=string_columns,
            remove_extra_spaces=remove_extra_spaces
        )
        
        result_df = df
        
        for col_name in string_columns:
            if col_name not in df.columns:
                DataTypeConverter.logger.warning(
                    f"String column '{col_name}' not found in DataFrame"
                )
                continue
            
            # Basic trim
            trimmed_col = trim(col(col_name))
            
            # Remove extra spaces if requested
            if remove_extra_spaces:
                trimmed_col = regexp_replace(trimmed_col, "\\s+", " ")
            
            result_df = result_df.withColumn(col_name, trimmed_col)
        
        return result_df
    
    @staticmethod
    def standardize_case(
        df: DataFrame,
        columns: Dict[str, str]
    ) -> DataFrame:
        """
        Standardize string case (upper/lower/title).
        
        Args:
            df: Input DataFrame
            columns: Dict mapping column names to case type ('upper', 'lower', 'title')
            
        Returns:
            DataFrame with standardized case
            
        Examples:
            df = standardize_case(df, {
                "email": "lower",
                "country_code": "upper",
                "job_title": "title"
            })
        """
        DataTypeConverter.logger.debug(
            "Standardizing string case",
            columns=list(columns.keys())
        )
        
        result_df = df
        
        for col_name, case_type in columns.items():
            if col_name not in df.columns:
                DataTypeConverter.logger.warning(
                    f"Column '{col_name}' not found in DataFrame"
                )
                continue
            
            if case_type == "upper":
                result_df = result_df.withColumn(col_name, upper(col(col_name)))
            elif case_type == "lower":
                result_df = result_df.withColumn(col_name, lower(col(col_name)))
            elif case_type == "title":
                # Title case: first letter of each word capitalized
                result_df = result_df.withColumn(
                    col_name,
                    regexp_replace(col(col_name), r"(\b\w)", lambda m: m.group(1).upper())
                )
            else:
                DataTypeConverter.logger.warning(
                    f"Unknown case type '{case_type}' for column '{col_name}'"
                )
        
        return result_df
    
    @staticmethod
    def handle_nulls(
        df: DataFrame,
        null_replacements: Dict[str, Any],
        null_to_empty_string: Optional[List[str]] = None
    ) -> DataFrame:
        """
        Handle NULL values with specified replacements.
        
        Args:
            df: Input DataFrame
            null_replacements: Dict mapping column names to replacement values
            null_to_empty_string: List of columns to convert NULL to empty string
            
        Returns:
            DataFrame with NULL values replaced
            
        Examples:
            df = handle_nulls(df, {
                "commission_pct": 0.0,
                "manager_id": -1,
                "department_name": "Unassigned"
            })
            
            # Convert NULLs to empty strings
            df = handle_nulls(df, {}, null_to_empty_string=["middle_name"])
        """
        DataTypeConverter.logger.debug(
            "Handling NULL values",
            replacement_columns=list(null_replacements.keys()),
            empty_string_columns=null_to_empty_string or []
        )
        
        result_df = df
        
        # Replace with specified values
        for col_name, replacement_value in null_replacements.items():
            if col_name not in df.columns:
                DataTypeConverter.logger.warning(
                    f"Column '{col_name}' not found in DataFrame"
                )
                continue
            
            result_df = result_df.withColumn(
                col_name,
                coalesce(col(col_name), lit(replacement_value))
            )
        
        # Convert NULLs to empty strings
        if null_to_empty_string:
            for col_name in null_to_empty_string:
                if col_name not in df.columns:
                    DataTypeConverter.logger.warning(
                        f"Column '{col_name}' not found in DataFrame"
                    )
                    continue
                
                result_df = result_df.withColumn(
                    col_name,
                    coalesce(col(col_name), lit(""))
                )
        
        return result_df
    
    @staticmethod
    def convert_boolean_flags(
        df: DataFrame,
        flag_columns: Dict[str, Dict[str, Any]]
    ) -> DataFrame:
        """
        Convert Oracle boolean flags (Y/N, 1/0, etc.) to proper boolean.
        
        Args:
            df: Input DataFrame
            flag_columns: Dict mapping column names to conversion rules
                         Format: {"col_name": {"true_value": "Y", "false_value": "N"}}
            
        Returns:
            DataFrame with boolean columns
            
        Examples:
            df = convert_boolean_flags(df, {
                "is_active": {"true_value": "Y", "false_value": "N"},
                "is_manager": {"true_value": 1, "false_value": 0}
            })
        """
        DataTypeConverter.logger.debug(
            "Converting boolean flags",
            columns=list(flag_columns.keys())
        )
        
        result_df = df
        
        for col_name, conversion_rule in flag_columns.items():
            if col_name not in df.columns:
                DataTypeConverter.logger.warning(
                    f"Column '{col_name}' not found in DataFrame"
                )
                continue
            
            true_val = conversion_rule.get("true_value")
            false_val = conversion_rule.get("false_value")
            
            result_df = result_df.withColumn(
                col_name,
                when(col(col_name) == true_val, lit(True))
                .when(col(col_name) == false_val, lit(False))
                .otherwise(lit(None))
                .cast(BooleanType())
            )
        
        return result_df
    
    @staticmethod
    def convert_oracle_to_json_types(
        df: DataFrame,
        type_config: Optional[Dict[str, Any]] = None
    ) -> DataFrame:
        """
        Convert all Oracle types to JSON-compatible types using sensible defaults.
        
        Args:
            df: Input DataFrame
            type_config: Optional configuration for specific columns
            
        Returns:
            DataFrame with JSON-compatible types
            
        This is a convenience method that applies common conversions:
        - All dates → ISO strings
        - All strings → trimmed
        - Decimal numbers → rounded to 2 places
        """
        type_config = type_config or {}
        
        DataTypeConverter.logger.info(
            "Converting Oracle types to JSON-compatible types",
            columns=len(df.columns)
        )
        
        result_df = df
        
        # Identify column types
        date_cols = []
        timestamp_cols = []
        string_cols = []
        decimal_cols = {}
        
        for field in df.schema.fields:
            col_name = field.name
            col_type = str(field.dataType)
            
            if "date" in col_type.lower() and "timestamp" not in col_type.lower():
                date_cols.append(col_name)
            elif "timestamp" in col_type.lower():
                timestamp_cols.append(col_name)
            elif "string" in col_type.lower():
                string_cols.append(col_name)
            elif "decimal" in col_type.lower():
                decimal_cols[col_name] = "decimal"
        
        # Apply conversions
        if date_cols:
            result_df = DataTypeConverter.convert_dates_to_iso(result_df, date_cols)
        
        if timestamp_cols:
            result_df = DataTypeConverter.convert_timestamps_to_iso(result_df, timestamp_cols)
        
        if string_cols:
            result_df = DataTypeConverter.trim_strings(result_df, string_cols)
        
        if decimal_cols:
            result_df = DataTypeConverter.convert_numbers(result_df, decimal_cols)
        
        DataTypeConverter.logger.info(
            "Type conversion complete",
            date_columns=len(date_cols),
            timestamp_columns=len(timestamp_cols),
            string_columns=len(string_cols),
            decimal_columns=len(decimal_cols)
        )
        
        return result_df


# Example usage
if __name__ == "__main__":
    """
    Example usage of DataTypeConverter.
    """
    from pyspark.sql import SparkSession
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DateType, DecimalType
    from datetime import date
    
    print("=" * 80)
    print("Data Type Converter - Example Usage")
    print("=" * 80)
    
    # Create SparkSession
    spark = SparkSession.builder.appName("DataTypeConverterExample").getOrCreate()
    
    # Create sample data (simulating Oracle extraction)
    schema = StructType([
        StructField("employee_id", IntegerType(), False),
        StructField("first_name", StringType(), True),
        StructField("last_name", StringType(), True),
        StructField("email", StringType(), True),
        StructField("hire_date", DateType(), True),
        StructField("salary", DecimalType(10, 2), True),
        StructField("commission_pct", DecimalType(4, 2), True)
    ])
    
    data = [
        (100, "  Steven  ", "  King  ", "SKING@COMPANY.COM", date(2003, 6, 17), 24000.00, None),
        (101, "Neena", "Kochhar", "nkochhar@company.com", date(2005, 9, 21), 17000.00, 0.20),
        (102, "Lex  ", "De Haan", "LDEHAAN@COMPANY.COM", date(2001, 1, 13), 17000.00, None)
    ]
    
    df = spark.createDataFrame(data, schema)
    
    print("\n1. Original DataFrame (from Oracle):")
    df.show(truncate=False)
    df.printSchema()
    
    print("\n2. Convert dates to ISO format:")
    df_dates = DataTypeConverter.convert_dates_to_iso(df, ["hire_date"])
    df_dates.select("employee_id", "first_name", "hire_date").show(truncate=False)
    
    print("\n3. Trim string columns:")
    df_trimmed = DataTypeConverter.trim_strings(df_dates, ["first_name", "last_name"])
    df_trimmed.select("employee_id", "first_name", "last_name").show(truncate=False)
    
    print("\n4. Standardize email case:")
    df_case = DataTypeConverter.standardize_case(df_trimmed, {"email": "lower"})
    df_case.select("employee_id", "email").show(truncate=False)
    
    print("\n5. Handle NULL commission:")
    df_nulls = DataTypeConverter.handle_nulls(df_case, {"commission_pct": 0.0})
    df_nulls.select("employee_id", "first_name", "commission_pct").show(truncate=False)
    
    print("\n6. Convert all types (one-shot):")
    df_final = DataTypeConverter.convert_oracle_to_json_types(df)
    df_final.show(truncate=False)
    df_final.printSchema()
    
    print("\n" + "=" * 80)
    print("✅ All conversions completed successfully!")
    print("=" * 80)
    
    spark.stop()

"""
Common Transformations

Reusable transformation functions for data migration.
Provides utilities for denormalization, joins, metadata addition, and document formatting.

Usage:
    from transformers.common_transformations import CommonTransformations
    
    # Add partition key
    df = CommonTransformations.add_partition_key(df, "dept_{department_id}_{employee_id % 10}")
    
    # Add metadata
    df = CommonTransformations.add_metadata(df, source="oracle_hr", entity_type="employee")
    
    # Create reference document
    ref_doc = CommonTransformations.create_reference_document(df, entity_type="region")
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, lit, struct, array, collect_list, concat_ws,
    when, coalesce, current_timestamp, expr, concat,
    monotonically_increasing_id, row_number, hash as spark_hash
)
from pyspark.sql.window import Window

from utils.logging_config import get_logger


class CommonTransformations:
    """
    Static utility class for common transformation operations.
    
    All methods are static and return transformed DataFrames.
    """
    
    logger = get_logger("common_transformations")
    
    @staticmethod
    def calculate_partition_key(
        df: DataFrame,
        key_formula: str,
        column_name: str = "partitionKey"
    ) -> DataFrame:
        """
        Calculate and add synthetic partition key based on formula.
        Alias for add_partition_key() for backward compatibility.
        
        Args:
            df: Input DataFrame
            key_formula: Formula for partition key (can reference columns)
                        Example: "dept_{department_id}_{employee_id % 10}"
            column_name: Name for partition key column (default: "partitionKey")
            
        Returns:
            DataFrame with partition key column added
        """
        return CommonTransformations.add_partition_key(df, key_formula, column_name)
    
    @staticmethod
    def add_partition_key(
        df: DataFrame,
        key_formula: str,
        column_name: str = "partitionKey"
    ) -> DataFrame:
        """
        Add synthetic partition key based on formula.
        
        Args:
            df: Input DataFrame
            key_formula: Formula for partition key (can reference columns)
                        Example: "dept_{department_id}_{employee_id % 10}"
            column_name: Name for partition key column (default: "partitionKey")
            
        Returns:
            DataFrame with partition key column added
            
        Examples:
            # Simple concatenation
            df = add_partition_key(df, "region_{region_id}")
            
            # With modulo for distribution
            df = add_partition_key(df, "dept_{department_id}_{employee_id % 10}")
            
            # Hash-based
            df = add_partition_key(df, "hash({employee_id})")
        """
        CommonTransformations.logger.debug(
            "Adding partition key",
            formula=key_formula,
            column_name=column_name
        )
        
        # Replace {column} references with col("column") for expr()
        # This allows formulas like "dept_{department_id}_{employee_id % 10}"
        
        try:
            # Simple approach: use format_string with concat
            # Parse the formula to extract column references
            import re
            
            # Find all {column} or {column % n} patterns
            pattern = r'\{([^}]+)\}'
            matches = re.findall(pattern, key_formula)
            
            # Build expression
            expr_str = key_formula
            for match in matches:
                # Replace {expr} with concat_ws result
                expr_str = expr_str.replace(f"{{{match}}}", f"{{cast({match} as string)}}")
            
            # Use format_string or concat
            # Simpler: use concat with string casting
            parts = []
            remaining = key_formula
            
            for match in matches:
                # Split on the match
                before, after = remaining.split(f"{{{match}}}", 1)
                if before:
                    parts.append(lit(before))
                parts.append(expr(match).cast("string"))
                remaining = after
            
            if remaining:
                parts.append(lit(remaining))
            
            if len(parts) == 1:
                key_col = parts[0]
            else:
                key_col = concat(*parts)
            
            result_df = df.withColumn(column_name, key_col)
            
            CommonTransformations.logger.debug(
                "Partition key added successfully",
                column_name=column_name
            )
            
            return result_df
            
        except Exception as e:
            CommonTransformations.logger.error(
                "Failed to add partition key",
                formula=key_formula,
                error=str(e)
            )
            raise
    
    @staticmethod
    def add_metadata(
        df: DataFrame,
        source: Optional[str] = None,
        entity_type: Optional[str] = None,
        source_system: Optional[str] = None,  # Alias for 'source'
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> DataFrame:
        """
        Add metadata columns to DataFrame.
        Supports both 'source' and 'source_system' parameters for compatibility.
        
        Args:
            df: Input DataFrame
            source: Source system identifier (e.g., "oracle_hr")
            entity_type: Type of entity (e.g., "employee", "region")
            source_system: Alias for 'source' parameter (for backward compatibility)
            additional_metadata: Optional additional metadata fields
            
        Returns:
            DataFrame with metadata struct column added
            
        Example:
            df = add_metadata(df, source="oracle_hr", entity_type="employee")
            df = add_metadata(df, source_system="oracle_hr", entity_type="employee")
            
            # Result includes metadata column:
            # {
            #   "source_system": "oracle_hr",
            #   "entity_type": "employee",
            #   "migrated_at": "2025-10-22T10:30:00Z",
            #   "version": "1.0"
            # }
        """
        # Support both parameter names
        source_value = source_system if source_system is not None else source
        if source_value is None:
            raise ValueError("Either 'source' or 'source_system' must be provided")
        
        CommonTransformations.logger.debug(
            "Adding metadata",
            source=source_value,
            entity_type=entity_type
        )
        
        # Build metadata struct using snake_case for consistency with test expectations
        metadata_fields = {
            "source_system": lit(source_value),
            "entity_type": lit(entity_type),
            "migrated_at": current_timestamp(),
            "version": lit("1.0")
        }
        
        # Add additional metadata if provided
        if additional_metadata:
            for key, value in additional_metadata.items():
                metadata_fields[key] = lit(value)
        
        result_df = df.withColumn("metadata", struct(*[
            v.alias(k) for k, v in metadata_fields.items()
        ]))
        
        return result_df
    
    @staticmethod
    def add_document_id(
        df: DataFrame,
        id_column: str,
        prefix: Optional[str] = None,
        id_name: str = "id"
    ) -> DataFrame:
        """
        Add or rename document ID column.
        Supports both simple column names and format strings like "emp_{employee_id}".
        
        Args:
            df: Input DataFrame
            id_column: Source column to use as ID, or format string like "emp_{employee_id}"
            prefix: Optional prefix for ID (e.g., "emp_") - ignored if id_column is a format string
            id_name: Name for ID column (default: "id")
            
        Returns:
            DataFrame with ID column
            
        Examples:
            # Simple rename
            df = add_document_id(df, id_column="employee_id")
            
            # With prefix
            df = add_document_id(df, id_column="employee_id", prefix="emp_")
            # Result: "emp_101", "emp_102", etc.
            
            # Format string
            df = add_document_id(df, "emp_{employee_id}")
            # Result: "emp_101", "emp_102", etc.
        """
        import re
        
        CommonTransformations.logger.debug(
            "Adding document ID",
            source_column=id_column,
            prefix=prefix
        )
        
        # Check if id_column contains a format string like "emp_{employee_id}"
        if '{' in id_column and '}' in id_column:
            # Parse format string
            pattern = r'\{([^}]+)\}'
            matches = re.findall(pattern, id_column)
            
            if matches:
                # Build expression by replacing {column} with actual column values
                parts = re.split(r'(\{[^}]+\})', id_column)
                concat_parts = []
                
                for part in parts:
                    if part.startswith('{') and part.endswith('}'):
                        # Extract column name
                        col_name = part[1:-1]
                        concat_parts.append(col(col_name).cast("string"))
                    elif part:
                        # Literal string
                        concat_parts.append(lit(part))
                
                if concat_parts:
                    id_col = concat(*concat_parts)
                else:
                    id_col = col(id_column).cast("string")
            else:
                id_col = col(id_column).cast("string")
        elif prefix:
            id_col = concat(lit(prefix), col(id_column).cast("string"))
        else:
            id_col = col(id_column).cast("string")
        
        result_df = df.withColumn(id_name, id_col)
        
        return result_df
    
    @staticmethod
    def create_reference_document(
        df: DataFrame,
        entity_type: str,
        id_column: str,
        data_columns: Optional[List[str]] = None,
        partition_key_value: Optional[str] = None
    ) -> DataFrame:
        """
        Create reference document structure for Cosmos DB.
        
        Args:
            df: Input DataFrame
            entity_type: Type of entity (e.g., "region", "country", "job")
            id_column: Column to use as document ID
            data_columns: Columns to include in data struct (None = all except id)
            partition_key_value: Partition key value (default: entity_type)
            
        Returns:
            DataFrame formatted as reference documents
            
        Example structure:
            {
              "id": "region_1",
              "partitionKey": "region",
              "entity_type": "region",
              "data": {
                "region_id": 1,
                "region_name": "Europe"
              },
              "metadata": {...}
            }
        """
        CommonTransformations.logger.info(
            "Creating reference document",
            entity_type=entity_type,
            id_column=id_column
        )
        
        # Determine data columns
        if data_columns is None:
            data_columns = [c for c in df.columns if c != id_column]
        
        # Add document ID
        result_df = CommonTransformations.add_document_id(
            df,
            id_column=id_column,
            prefix=f"{entity_type}_"
        )
        
        # Add partition key
        partition_key = partition_key_value or entity_type
        result_df = result_df.withColumn("partitionKey", lit(partition_key))
        
        # Add entity type (using snake_case for consistency with test expectations)
        result_df = result_df.withColumn("entity_type", lit(entity_type))
        
        # Create data struct
        data_struct_fields = [col(c).alias(c) for c in data_columns]
        result_df = result_df.withColumn("data", struct(*data_struct_fields))
        
        # Add metadata
        result_df = CommonTransformations.add_metadata(
            result_df,
            source="oracle_hr",
            entity_type=entity_type
        )
        
        # Select final columns
        result_df = result_df.select("id", "partitionKey", "entity_type", "data", "metadata")
        
        CommonTransformations.logger.info(
            "Reference document created",
            entity_type=entity_type,
            record_count=result_df.count()
        )
        
        return result_df
    
    @staticmethod
    def denormalize_with_join(
        df: DataFrame,
        lookup_df: DataFrame,
        join_column: str,
        lookup_column: str,
        embed_as: str,
        embed_columns: Optional[List[str]] = None,
        join_type: str = "left"
    ) -> DataFrame:
        """
        Denormalize by joining and embedding related data.
        
        Args:
            df: Main DataFrame
            lookup_df: Lookup DataFrame to join
            join_column: Column in main DataFrame to join on
            lookup_column: Column in lookup DataFrame to join on
            embed_as: Name for embedded struct column
            embed_columns: Columns from lookup to embed (None = all)
            join_type: Join type (default: "left")
            
        Returns:
            DataFrame with embedded lookup data
            
        Example:
            # Embed department details in employee
            df = denormalize_with_join(
                employees_df,
                departments_df,
                join_column="department_id",
                lookup_column="department_id",
                embed_as="department",
                embed_columns=["department_id", "department_name", "manager_id"]
            )
        """
        CommonTransformations.logger.debug(
            "Denormalizing with join",
            join_column=join_column,
            embed_as=embed_as,
            join_type=join_type
        )
        
        # Determine columns to embed
        if embed_columns is None:
            embed_columns = lookup_df.columns
        
        # Rename lookup columns to avoid conflicts
        renamed_lookup = lookup_df
        for col_name in embed_columns:
            if col_name != lookup_column:
                renamed_lookup = renamed_lookup.withColumnRenamed(
                    col_name,
                    f"_lookup_{col_name}"
                )
        
        # Join
        result_df = df.join(
            renamed_lookup,
            df[join_column] == renamed_lookup[lookup_column],
            join_type
        )
        
        # Create embedded struct
        embed_fields = []
        for col_name in embed_columns:
            if col_name == lookup_column:
                embed_fields.append(col(lookup_column).alias(col_name))
            else:
                embed_fields.append(col(f"_lookup_{col_name}").alias(col_name))
        
        result_df = result_df.withColumn(embed_as, struct(*embed_fields))
        
        # Drop renamed lookup columns and original lookup key
        cols_to_drop = [f"_lookup_{c}" for c in embed_columns if c != lookup_column]
        if lookup_column not in df.columns:
            cols_to_drop.append(lookup_column)
        
        result_df = result_df.drop(*cols_to_drop)
        
        return result_df
    
    @staticmethod
    def aggregate_related_records(
        main_df: DataFrame,
        related_df: DataFrame,
        join_column: str,
        embed_as: str,
        embed_columns: Optional[List[str]] = None,
        order_by: Optional[List[str]] = None
    ) -> DataFrame:
        """
        Aggregate related records into an array.
        
        Args:
            main_df: Main DataFrame
            related_df: Related DataFrame to aggregate
            join_column: Column to join on
            embed_as: Name for embedded array column
            embed_columns: Columns to include in array elements (None = all)
            order_by: Columns to order array by
            
        Returns:
            DataFrame with related records as array
            
        Example:
            # Aggregate job history for each employee
            df = aggregate_related_records(
                employees_df,
                job_history_df,
                join_column="employee_id",
                embed_as="job_history",
                order_by=["start_date"]
            )
        """
        CommonTransformations.logger.debug(
            "Aggregating related records",
            join_column=join_column,
            embed_as=embed_as
        )
        
        # Determine columns to include
        if embed_columns is None:
            embed_columns = [c for c in related_df.columns if c != join_column]
        
        # Order if specified
        if order_by:
            related_df = related_df.orderBy(*order_by)
        
        # Create struct for each related record
        struct_fields = [col(c).alias(c) for c in embed_columns]
        related_with_struct = related_df.withColumn(
            "_related_struct",
            struct(*struct_fields)
        )
        
        # Group and collect into array
        aggregated = related_with_struct.groupBy(join_column).agg(
            collect_list("_related_struct").alias(embed_as)
        )
        
        # Join back to main DataFrame
        result_df = main_df.join(aggregated, join_column, "left")
        
        # Handle nulls (no related records) - create empty array
        result_df = result_df.withColumn(
            embed_as,
            coalesce(col(embed_as), array().cast(f"array<struct<{','.join([f'{c}:string' for c in embed_columns])}>"))
        )
        
        return result_df
    
    @staticmethod
    def flatten_columns(
        df: DataFrame,
        prefix: str = "",
        separator: str = "_"
    ) -> DataFrame:
        """
        Flatten struct columns into individual columns.
        
        Args:
            df: Input DataFrame with struct columns
            prefix: Prefix for flattened column names
            separator: Separator between struct name and field name
            
        Returns:
            DataFrame with flattened columns
            
        Example:
            # Input: {address: {city: "Seattle", state: "WA"}}
            # Output: address_city: "Seattle", address_state: "WA"
        """
        CommonTransformations.logger.debug("Flattening struct columns")
        
        result_df = df
        
        for field in df.schema.fields:
            if "struct" in str(field.dataType).lower():
                struct_name = field.name
                struct_col = col(struct_name)
                
                # Get nested fields
                nested_fields = field.dataType.fields
                
                for nested_field in nested_fields:
                    nested_name = nested_field.name
                    new_col_name = f"{prefix}{struct_name}{separator}{nested_name}"
                    
                    result_df = result_df.withColumn(
                        new_col_name,
                        struct_col.getField(nested_name)
                    )
                
                # Drop original struct column
                result_df = result_df.drop(struct_name)
        
        return result_df
    
    @staticmethod
    def add_row_hash(
        df: DataFrame,
        hash_columns: Optional[List[str]] = None,
        hash_column_name: str = "row_hash"
    ) -> DataFrame:
        """
        Add hash column for row-level change detection.
        
        Args:
            df: Input DataFrame
            hash_columns: Columns to include in hash (None = all)
            hash_column_name: Name for hash column
            
        Returns:
            DataFrame with hash column
            
        Use case: Detect changed records in incremental loads
        """
        CommonTransformations.logger.debug("Adding row hash")
        
        if hash_columns is None:
            hash_columns = df.columns
        
        # Concatenate columns and hash
        concat_col = concat_ws("||", *[coalesce(col(c).cast("string"), lit("NULL")) for c in hash_columns])
        hash_col = spark_hash(concat_col)
        
        result_df = df.withColumn(hash_column_name, hash_col)
        
        return result_df
    
    @staticmethod
    def deduplicate_by_key(
        df: DataFrame,
        key_columns: List[str],
        order_by: Optional[List[str]] = None,
        keep: str = "last"
    ) -> DataFrame:
        """
        Remove duplicate records based on key columns.
        
        Args:
            df: Input DataFrame
            key_columns: Columns that define uniqueness
            order_by: Columns to order by when choosing which record to keep
            keep: Which record to keep - "first" or "last" (default: "last")
            
        Returns:
            DataFrame with duplicates removed
        """
        CommonTransformations.logger.debug(
            "Deduplicating by key",
            key_columns=key_columns,
            keep=keep
        )
        
        if order_by:
            # Use window function to add row number
            window_spec = Window.partitionBy(*key_columns).orderBy(
                *[col(c).desc() if keep == "last" else col(c) for c in order_by]
            )
            
            result_df = df.withColumn("_row_num", row_number().over(window_spec))
            result_df = result_df.filter(col("_row_num") == 1).drop("_row_num")
        else:
            # Simple distinct
            result_df = df.dropDuplicates(key_columns)
        
        return result_df


# Example usage
if __name__ == "__main__":
    """
    Example usage of CommonTransformations.
    """
    from pyspark.sql import SparkSession
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType
    
    print("=" * 80)
    print("Common Transformations - Example Usage")
    print("=" * 80)
    
    # Create SparkSession
    spark = SparkSession.builder.appName("CommonTransformationsExample").getOrCreate()
    
    # Sample data
    regions_data = [
        (1, "Europe"),
        (2, "Americas"),
        (3, "Asia"),
        (4, "Middle East")
    ]
    
    regions_df = spark.createDataFrame(regions_data, ["region_id", "region_name"])
    
    print("\n1. Original regions data:")
    regions_df.show()
    
    print("\n2. Add partition key:")
    df_with_key = CommonTransformations.add_partition_key(
        regions_df,
        "region_{region_id}"
    )
    df_with_key.show()
    
    print("\n3. Add document ID:")
    df_with_id = CommonTransformations.add_document_id(
        df_with_key,
        id_column="region_id",
        prefix="reg_"
    )
    df_with_id.show()
    
    print("\n4. Create reference document:")
    ref_doc = CommonTransformations.create_reference_document(
        regions_df,
        entity_type="region",
        id_column="region_id"
    )
    ref_doc.show(truncate=False)
    ref_doc.printSchema()
    
    print("\n5. Denormalize with join (example):")
    # Create sample employee and department data
    employees_data = [(101, "John", 90), (102, "Jane", 60)]
    departments_data = [(90, "Sales"), (60, "IT")]
    
    employees_df = spark.createDataFrame(employees_data, ["emp_id", "name", "dept_id"])
    departments_df = spark.createDataFrame(departments_data, ["dept_id", "dept_name"])
    
    denormalized = CommonTransformations.denormalize_with_join(
        employees_df,
        departments_df,
        join_column="dept_id",
        lookup_column="dept_id",
        embed_as="department"
    )
    denormalized.show(truncate=False)
    denormalized.printSchema()
    
    print("\n" + "=" * 80)
    print("✅ All transformations completed successfully!")
    print("=" * 80)
    
    spark.stop()

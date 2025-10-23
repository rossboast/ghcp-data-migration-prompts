"""
Base Transformer

This module defines the abstract base class for all data transformers.
Transformers are responsible for converting data from source format to target format.

All concrete transformer implementations should inherit from BaseTransformer
and implement the required abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col

from utils import get_logger, MigrationMetrics, Timer, ErrorContext, TransformationError


class BaseTransformer(ABC):
    """
    Abstract base class for all data transformers.
    
    This class provides common functionality for transforming data and
    defines the interface that all transformers must implement.
    
    Attributes:
        spark: SparkSession instance
        transformer_name: Name of this transformer
        metrics: MigrationMetrics instance for tracking transformation metrics
        logger: Logger instance for this transformer
    """
    
    def __init__(
        self,
        spark: SparkSession,
        transformer_name: str,
        metrics: Optional[MigrationMetrics] = None
    ):
        """
        Initialize the base transformer.
        
        Args:
            spark: SparkSession instance
            transformer_name: Name of this transformer
            metrics: Optional MigrationMetrics instance for tracking
        """
        self.spark = spark
        self.transformer_name = transformer_name
        self.metrics = metrics or MigrationMetrics(feed_name=transformer_name)
        self.logger = get_logger(
            self.__class__.__name__,
            transformer=transformer_name
        )
        
        self.logger.info(
            "Transformer initialized",
            transformer_class=self.__class__.__name__,
            transformer_name=transformer_name
        )
    
    @abstractmethod
    def transform(self, df: DataFrame, **kwargs) -> DataFrame:
        """
        Transform the input DataFrame.
        
        This is the main method that concrete transformers must implement.
        It should return a transformed Spark DataFrame.
        
        Args:
            df: Input DataFrame to transform
            **kwargs: Additional parameters specific to the transformer
            
        Returns:
            Transformed DataFrame
            
        Raises:
            TransformationError: If transformation fails
        """
        pass
    
    @abstractmethod
    def get_output_schema(self) -> Dict[str, str]:
        """
        Get the expected output schema.
        
        Returns:
            Dictionary mapping field names to types
        """
        pass
    
    def transform_with_metrics(
        self,
        df: DataFrame,
        **kwargs
    ) -> DataFrame:
        """
        Transform data and track metrics.
        
        This wrapper method calls the concrete transform() implementation
        and tracks transformation metrics (duration, record count, errors).
        
        Args:
            df: Input DataFrame
            **kwargs: Additional parameters
            
        Returns:
            Transformed DataFrame
            
        Raises:
            TransformationError: If transformation fails
        """
        input_count = df.count()
        
        self.logger.info(
            "Starting transformation",
            transformer=self.transformer_name,
            input_records=input_count,
            kwargs=kwargs
        )
        
        with Timer() as timer:
            try:
                with ErrorContext("transformation", transformer=self.transformer_name):
                    # Call the concrete implementation
                    transformed_df = self.transform(df, **kwargs)
                    
                    # Cache and count
                    transformed_df.cache()
                    output_count = transformed_df.count()
                    
                    # Update metrics
                    self.metrics.records_transformed += output_count
                    self.metrics.transformation_duration_seconds = timer.elapsed_seconds
                    
                    self.logger.info(
                        "Transformation completed successfully",
                        transformer=self.transformer_name,
                        input_records=input_count,
                        output_records=output_count,
                        duration_seconds=timer.elapsed_seconds
                    )
                    
                    return transformed_df
                    
            except Exception as e:
                self.metrics.transformation_errors += 1
                self.logger.error(
                    "Transformation failed",
                    transformer=self.transformer_name,
                    error=str(e),
                    duration_seconds=timer.elapsed_seconds
                )
                raise TransformationError(
                    f"Transformation failed in {self.transformer_name}: {str(e)}"
                ) from e
    
    def chain_transform(
        self,
        df: DataFrame,
        transformers: List['BaseTransformer']
    ) -> DataFrame:
        """
        Chain multiple transformations.
        
        Args:
            df: Input DataFrame
            transformers: List of transformers to apply in order
            
        Returns:
            DataFrame after all transformations
        """
        self.logger.info(
            "Starting transformation chain",
            num_transformers=len(transformers)
        )
        
        current_df = df
        
        for i, transformer in enumerate(transformers):
            self.logger.info(
                "Applying transformer in chain",
                chain_position=i + 1,
                total_transformers=len(transformers),
                transformer_name=transformer.transformer_name
            )
            
            current_df = transformer.transform_with_metrics(current_df)
        
        self.logger.info("Transformation chain completed")
        
        return current_df
    
    def add_metadata_columns(
        self,
        df: DataFrame,
        metadata: Dict[str, Any]
    ) -> DataFrame:
        """
        Add metadata columns to the DataFrame.
        
        Args:
            df: Input DataFrame
            metadata: Dictionary of metadata to add as columns
            
        Returns:
            DataFrame with metadata columns added
        """
        from pyspark.sql.functions import lit
        
        result_df = df
        
        for key, value in metadata.items():
            result_df = result_df.withColumn(key, lit(value))
        
        return result_df
    
    def rename_columns(
        self,
        df: DataFrame,
        column_mapping: Dict[str, str]
    ) -> DataFrame:
        """
        Rename columns in the DataFrame.
        
        Args:
            df: Input DataFrame
            column_mapping: Dictionary mapping old names to new names
            
        Returns:
            DataFrame with renamed columns
        """
        result_df = df
        
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                result_df = result_df.withColumnRenamed(old_name, new_name)
            else:
                self.logger.warning(
                    "Column not found for renaming",
                    old_name=old_name,
                    new_name=new_name
                )
        
        return result_df
    
    def select_columns(
        self,
        df: DataFrame,
        columns: List[str]
    ) -> DataFrame:
        """
        Select specific columns from the DataFrame.
        
        Args:
            df: Input DataFrame
            columns: List of column names to select
            
        Returns:
            DataFrame with only selected columns
        """
        missing_columns = [c for c in columns if c not in df.columns]
        
        if missing_columns:
            self.logger.warning(
                "Some columns not found",
                missing_columns=missing_columns
            )
        
        available_columns = [c for c in columns if c in df.columns]
        
        return df.select(*available_columns)
    
    def filter_records(
        self,
        df: DataFrame,
        condition: str
    ) -> DataFrame:
        """
        Filter records based on a SQL condition.
        
        Args:
            df: Input DataFrame
            condition: SQL WHERE clause condition
            
        Returns:
            Filtered DataFrame
        """
        self.logger.info(
            "Filtering records",
            condition=condition
        )
        
        filtered_df = df.filter(condition)
        
        input_count = df.count()
        output_count = filtered_df.count()
        filtered_count = input_count - output_count
        
        self.logger.info(
            "Filtering completed",
            input_records=input_count,
            output_records=output_count,
            filtered_records=filtered_count
        )
        
        return filtered_df
    
    def deduplicate(
        self,
        df: DataFrame,
        key_columns: List[str]
    ) -> DataFrame:
        """
        Remove duplicate records based on key columns.
        
        Args:
            df: Input DataFrame
            key_columns: List of columns to use for deduplication
            
        Returns:
            Deduplicated DataFrame
        """
        self.logger.info(
            "Deduplicating records",
            key_columns=key_columns
        )
        
        input_count = df.count()
        deduped_df = df.dropDuplicates(key_columns)
        output_count = deduped_df.count()
        duplicate_count = input_count - output_count
        
        if duplicate_count > 0:
            self.logger.warning(
                "Duplicates found and removed",
                input_records=input_count,
                output_records=output_count,
                duplicates_removed=duplicate_count
            )
        else:
            self.logger.info(
                "No duplicates found",
                record_count=input_count
            )
        
        return deduped_df
    
    def validate_schema(
        self,
        df: DataFrame,
        expected_schema: Dict[str, str]
    ) -> bool:
        """
        Validate that DataFrame has expected schema.
        
        Args:
            df: DataFrame to validate
            expected_schema: Dictionary of column names to types
            
        Returns:
            True if schema matches, False otherwise
        """
        actual_columns = set(df.columns)
        expected_columns = set(expected_schema.keys())
        
        missing_columns = expected_columns - actual_columns
        extra_columns = actual_columns - expected_columns
        
        if missing_columns:
            self.logger.warning(
                "Missing expected columns",
                missing_columns=list(missing_columns)
            )
        
        if extra_columns:
            self.logger.info(
                "Extra columns present",
                extra_columns=list(extra_columns)
            )
        
        return len(missing_columns) == 0


class CompositeTransformer(BaseTransformer):
    """
    Transformer that applies multiple transformations in sequence.
    
    This is useful for creating complex transformations by combining
    simpler transformers.
    """
    
    def __init__(
        self,
        spark: SparkSession,
        transformer_name: str,
        transformers: List[BaseTransformer],
        metrics: Optional[MigrationMetrics] = None
    ):
        """
        Initialize composite transformer.
        
        Args:
            spark: SparkSession instance
            transformer_name: Name of this composite transformer
            transformers: List of transformers to apply in order
            metrics: Optional MigrationMetrics instance
        """
        super().__init__(spark, transformer_name, metrics)
        self.transformers = transformers
        
        self.logger.info(
            "Composite transformer initialized",
            num_transformers=len(transformers)
        )
    
    def transform(self, df: DataFrame, **kwargs) -> DataFrame:
        """
        Apply all transformations in sequence.
        
        Args:
            df: Input DataFrame
            **kwargs: Additional parameters passed to each transformer
            
        Returns:
            Transformed DataFrame
        """
        return self.chain_transform(df, self.transformers)
    
    def get_output_schema(self) -> Dict[str, str]:
        """
        Get output schema from the last transformer in the chain.
        
        Returns:
            Output schema dictionary
        """
        if self.transformers:
            return self.transformers[-1].get_output_schema()
        return {}


# Example usage
if __name__ == "__main__":
    from utils import get_spark_session
    
    # Demo transformer for testing
    class DemoTransformer(BaseTransformer):
        """Demo transformer for testing."""
        
        def transform(self, df: DataFrame, **kwargs) -> DataFrame:
            """Add a computed column."""
            from pyspark.sql.functions import upper
            return df.withColumn("name_upper", upper(col("name")))
        
        def get_output_schema(self) -> Dict[str, str]:
            """Get output schema."""
            return {
                "id": "integer",
                "name": "string",
                "name_upper": "string"
            }
    
    # Test the transformer
    spark = get_spark_session(app_name="TestTransformer")
    
    # Create test data
    data = [(1, "Alice"), (2, "Bob"), (3, "Charlie")]
    df = spark.createDataFrame(data, ["id", "name"])
    
    transformer = DemoTransformer(spark, "Demo Transformer")
    
    result = transformer.transform_with_metrics(df)
    result.show()
    
    print("\nMetrics:")
    print(f"Records transformed: {transformer.metrics.records_transformed}")
    print(f"Duration: {transformer.metrics.transformation_duration_seconds:.2f}s")

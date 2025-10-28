"""
Base Loader

This module defines the abstract base class for all data loaders.
Loaders are responsible for writing data to target systems.

All concrete loader implementations should inherit from BaseLoader
and implement the required abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from pyspark.sql import DataFrame, SparkSession

from utils.logging_config import get_logger
from utils.metrics import MigrationMetrics, Timer
from utils.error_handler import ErrorContext, LoadError, retry


@dataclass
class LoadResult:
    """
    Result of a load operation.
    
    Attributes:
        records_loaded: Number of records successfully loaded
        records_failed: Number of records that failed to load
        load_time_seconds: Time taken to load in seconds
        target_table: Name of the target table/container
        errors: List of error messages encountered
        metadata: Additional metadata about the load operation
    """
    records_loaded: int = 0
    records_failed: int = 0
    load_time_seconds: float = 0.0
    target_table: str = ""
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        total = self.records_loaded + self.records_failed
        if total == 0:
            return 0.0
        return (self.records_loaded / total) * 100.0
    
    @property
    def total_records(self) -> int:
        """Total number of records processed."""
        return self.records_loaded + self.records_failed
    
    def __str__(self) -> str:
        """String representation of load result."""
        return (
            f"LoadResult(loaded={self.records_loaded}, "
            f"failed={self.records_failed}, "
            f"time={self.load_time_seconds:.2f}s, "
            f"success_rate={self.success_rate:.1f}%)"
        )


class BaseLoader(ABC):
    """
    Abstract base class for all data loaders.
    
    This class provides common functionality for loading data to target systems
    and defines the interface that all loaders must implement.
    
    Attributes:
        spark: SparkSession instance
        target_name: Name of the target system (e.g., "Cosmos DB")
        metrics: MigrationMetrics instance for tracking load metrics
        logger: Logger instance for this loader
    """
    
    def __init__(
        self,
        spark: SparkSession,
        target_name: str,
        metrics: Optional[MigrationMetrics] = None
    ):
        """
        Initialize the base loader.
        
        Args:
            spark: SparkSession instance
            target_name: Name of the target system
            metrics: Optional MigrationMetrics instance for tracking
        """
        self.spark = spark
        self.target_name = target_name
        self.metrics = metrics or MigrationMetrics(feed_name=target_name)
        self.logger = get_logger(
            self.__class__.__name__,
            target=target_name
        )
        
        self.logger.info(
            "Loader initialized",
            loader_class=self.__class__.__name__,
            target=target_name
        )
    
    @abstractmethod
    def load(
        self,
        df: DataFrame,
        target_table: str,
        **kwargs
    ) -> int:
        """
        Load data to the target system.
        
        This is the main method that concrete loaders must implement.
        It should write the DataFrame to the target and return the number of records loaded.
        
        Args:
            df: DataFrame to load
            target_table: Name of target table/container/collection
            **kwargs: Additional parameters specific to the loader
            
        Returns:
            Number of records successfully loaded
            
        Raises:
            LoadError: If load fails
        """
        pass
    
    @abstractmethod
    def validate_target_connection(self) -> bool:
        """
        Validate connection to the target system.
        
        Returns:
            True if connection is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def target_exists(self, target_table: str) -> bool:
        """
        Check if target table/container exists.
        
        Args:
            target_table: Name of target table/container
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    def load_with_metrics(
        self,
        df: DataFrame,
        target_table: str,
        **kwargs
    ) -> int:
        """
        Load data and track metrics.
        
        This wrapper method calls the concrete load() implementation
        and tracks load metrics (duration, record count, errors).
        
        Args:
            df: DataFrame to load
            target_table: Name of target table
            **kwargs: Additional parameters
            
        Returns:
            Number of records loaded
            
        Raises:
            LoadError: If load fails
        """
        input_count = df.count()
        
        self.logger.info(
            "Starting load",
            target_table=target_table,
            record_count=input_count,
            kwargs=kwargs
        )
        
        with Timer() as timer:
            try:
                with ErrorContext("load", target_table=target_table):
                    # Call the concrete implementation
                    loaded_count = self.load(df, target_table, **kwargs)
                    
                    # Update metrics
                    self.metrics.records_loaded += loaded_count
                    self.metrics.load_duration_seconds = timer.elapsed_seconds
                    
                    # Calculate failed records
                    failed_count = input_count - loaded_count
                    if failed_count > 0:
                        self.metrics.records_failed += failed_count
                        self.logger.warning(
                            "Some records failed to load",
                            input_records=input_count,
                            loaded_records=loaded_count,
                            failed_records=failed_count
                        )
                    
                    self.logger.info(
                        "Load completed successfully",
                        target_table=target_table,
                        records_loaded=loaded_count,
                        duration_seconds=timer.elapsed_seconds
                    )
                    
                    return loaded_count
                    
            except Exception as e:
                self.metrics.load_errors += 1
                self.metrics.records_failed += input_count
                # Extract just the message to avoid circular reference in JSON logging
                if isinstance(e, LoadError):
                    error_msg = e.args[0] if e.args else "Unknown error"
                    # Re-raise as-is to avoid wrapping
                    raise
                else:
                    error_msg = str(e)
                    self.logger.error(
                        "Load failed",
                        target_table=target_table,
                        error=error_msg,
                        duration_seconds=timer.elapsed_seconds
                    )
                    raise LoadError(
                        f"Failed to load to {target_table}: {error_msg}"
                    ) from e
    
    def load_multiple(
        self,
        dataframes: Dict[str, DataFrame],
        **kwargs
    ) -> Dict[str, int]:
        """
        Load multiple DataFrames to different targets.
        
        Args:
            dataframes: Dictionary mapping target names to DataFrames
            **kwargs: Additional parameters passed to load()
            
        Returns:
            Dictionary mapping target names to record counts loaded
        """
        self.logger.info(
            "Starting multi-target load",
            target_count=len(dataframes)
        )
        
        results = {}
        
        for target_table, df in dataframes.items():
            try:
                count = self.load_with_metrics(df, target_table, **kwargs)
                results[target_table] = count
                
            except LoadError as e:
                self.logger.error(
                    "Failed to load target, continuing with others",
                    target_table=target_table,
                    error=str(e)
                )
                results[target_table] = 0
                # Continue with other targets
                continue
        
        self.logger.info(
            "Multi-target load completed",
            successful_targets=sum(1 for c in results.values() if c > 0),
            total_targets=len(dataframes)
        )
        
        return results
    
    def load_batches(
        self,
        df: DataFrame,
        target_table: str,
        batch_size: int = 1000,
        **kwargs
    ) -> int:
        """
        Load data in batches.
        
        This method is useful for large datasets or when the target system
        has limits on batch size.
        
        Args:
            df: DataFrame to load
            target_table: Name of target table
            batch_size: Number of records per batch
            **kwargs: Additional parameters
            
        Returns:
            Total number of records loaded
        """
        total_count = df.count()
        num_batches = (total_count + batch_size - 1) // batch_size
        
        self.logger.info(
            "Starting batch load",
            target_table=target_table,
            total_records=total_count,
            batch_size=batch_size,
            num_batches=num_batches
        )
        
        # Repartition DataFrame based on batch size
        df_partitioned = df.repartition(num_batches)
        
        # Load the partitioned DataFrame
        loaded_count = self.load_with_metrics(df_partitioned, target_table, **kwargs)
        
        self.logger.info(
            "Batch load completed",
            loaded_records=loaded_count,
            num_batches=num_batches
        )
        
        return loaded_count
    
    def upsert_records(
        self,
        df: DataFrame,
        target_table: str,
        key_columns: List[str],
        **kwargs
    ) -> int:
        """
        Upsert (insert or update) records based on key columns.
        
        Note: Concrete implementations must support upsert operations.
        
        Args:
            df: DataFrame to upsert
            target_table: Name of target table
            key_columns: Columns to use for matching existing records
            **kwargs: Additional parameters
            
        Returns:
            Number of records upserted
        """
        self.logger.info(
            "Starting upsert operation",
            target_table=target_table,
            key_columns=key_columns
        )
        
        # Default implementation delegates to load()
        # Concrete loaders should override this for true upsert functionality
        return self.load_with_metrics(df, target_table, **kwargs)
    
    def delete_records(
        self,
        target_table: str,
        condition: str,
        **kwargs
    ) -> int:
        """
        Delete records from target based on condition.
        
        Args:
            target_table: Name of target table
            condition: SQL WHERE clause condition for deletion
            **kwargs: Additional parameters
            
        Returns:
            Number of records deleted
        """
        self.logger.warning(
            "Delete operation called",
            target_table=target_table,
            condition=condition
        )
        
        # This should be implemented by concrete loaders
        raise NotImplementedError(
            f"Delete operation not implemented in {self.__class__.__name__}"
        )
    
    def truncate_target(
        self,
        target_table: str,
        **kwargs
    ) -> bool:
        """
        Truncate (delete all records) from target.
        
        Args:
            target_table: Name of target table
            **kwargs: Additional parameters
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.warning(
            "Truncate operation called",
            target_table=target_table
        )
        
        # This should be implemented by concrete loaders
        raise NotImplementedError(
            f"Truncate operation not implemented in {self.__class__.__name__}"
        )
    
    def get_load_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about loaded data.
        
        Returns:
            Dictionary containing load statistics
        """
        return {
            "target_name": self.target_name,
            "loader_class": self.__class__.__name__,
            "records_loaded": self.metrics.records_loaded,
            "records_failed": self.metrics.records_failed,
            "load_duration_seconds": self.metrics.load_duration_seconds,
            "load_errors": self.metrics.load_errors,
        }
    
    def close(self) -> None:
        """
        Clean up resources.
        
        Concrete loaders can override this to clean up connections,
        close file handles, etc.
        """
        self.logger.info("Closing loader")


class BatchLoader(BaseLoader):
    """
    Extended base class for loaders that always use batch operations.
    
    This class provides additional batch-specific functionality.
    """
    
    def __init__(
        self,
        spark: SparkSession,
        target_name: str,
        default_batch_size: int = 1000,
        metrics: Optional[MigrationMetrics] = None
    ):
        """
        Initialize batch loader.
        
        Args:
            spark: SparkSession instance
            target_name: Name of target system
            default_batch_size: Default size for batches
            metrics: Optional MigrationMetrics instance
        """
        super().__init__(spark, target_name, metrics)
        self.default_batch_size = default_batch_size
        
        self.logger.info(
            "Batch loader initialized",
            default_batch_size=default_batch_size
        )
    
    @abstractmethod
    def load_batch(
        self,
        batch_df: DataFrame,
        target_table: str,
        batch_number: int,
        **kwargs
    ) -> int:
        """
        Load a single batch.
        
        Args:
            batch_df: DataFrame containing batch data
            target_table: Name of target table
            batch_number: Number of this batch (for logging)
            **kwargs: Additional parameters
            
        Returns:
            Number of records loaded in this batch
        """
        pass
    
    def load(
        self,
        df: DataFrame,
        target_table: str,
        batch_size: Optional[int] = None,
        **kwargs
    ) -> int:
        """
        Load data by splitting into batches.
        
        Args:
            df: DataFrame to load
            target_table: Name of target table
            batch_size: Size of each batch (uses default if not provided)
            **kwargs: Additional parameters
            
        Returns:
            Total number of records loaded
        """
        batch_size = batch_size or self.default_batch_size
        total_count = df.count()
        num_batches = (total_count + batch_size - 1) // batch_size
        
        self.logger.info(
            "Loading in batches",
            total_records=total_count,
            batch_size=batch_size,
            num_batches=num_batches
        )
        
        # Repartition for batch processing
        df_partitioned = df.repartition(num_batches)
        
        total_loaded = 0
        
        # Process each partition as a batch
        for batch_num in range(num_batches):
            batch_df = df_partitioned.filter(
                (df_partitioned.monotonically_increasing_id() >= batch_num * batch_size) &
                (df_partitioned.monotonically_increasing_id() < (batch_num + 1) * batch_size)
            )
            
            loaded = self.load_batch(batch_df, target_table, batch_num + 1, **kwargs)
            total_loaded += loaded
            
            self.logger.info(
                "Batch loaded",
                batch_number=batch_num + 1,
                total_batches=num_batches,
                records_in_batch=loaded
            )
        
        return total_loaded


# Example usage
if __name__ == "__main__":
    from utils import get_spark_session
    
    # Demo loader for testing
    class DemoLoader(BaseLoader):
        """Demo loader for testing."""
        
        def load(self, df: DataFrame, target_table: str, **kwargs) -> int:
            """Simulate loading data."""
            count = df.count()
            self.logger.info(f"Loading {count} records to {target_table}")
            return count
        
        def validate_target_connection(self) -> bool:
            """Validate connection."""
            return True
        
        def target_exists(self, target_table: str) -> bool:
            """Check if target exists."""
            return True
    
    # Test the loader
    spark = get_spark_session(app_name="TestLoader")
    
    # Create test data
    data = [(1, "Alice"), (2, "Bob"), (3, "Charlie")]
    df = spark.createDataFrame(data, ["id", "name"])
    
    loader = DemoLoader(spark, "Demo Target")
    
    loaded_count = loader.load_with_metrics(df, "demo_table")
    
    print(f"\nRecords loaded: {loaded_count}")
    print("\nMetrics:")
    print(f"Records loaded: {loader.metrics.records_loaded}")
    print(f"Duration: {loader.metrics.load_duration_seconds:.2f}s")
    
    loader.close()

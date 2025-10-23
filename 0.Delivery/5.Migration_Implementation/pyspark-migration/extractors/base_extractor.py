"""
Base Extractor

This module defines the abstract base class for all data extractors.
Extractors are responsible for reading data from source systems.

All concrete extractor implementations should inherit from BaseExtractor
and implement the required abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pyspark.sql import DataFrame, SparkSession

from utils import get_logger, MigrationMetrics, Timer, ErrorContext, ExtractionError


class BaseExtractor(ABC):
    """
    Abstract base class for all data extractors.
    
    This class provides common functionality for extracting data from source systems
    and defines the interface that all extractors must implement.
    
    Attributes:
        spark: SparkSession instance
        source_name: Name of the source system (e.g., "Oracle HR")
        metrics: MigrationMetrics instance for tracking extraction metrics
        logger: Logger instance for this extractor
    """
    
    def __init__(
        self,
        spark: SparkSession,
        source_name: str,
        metrics: Optional[MigrationMetrics] = None
    ):
        """
        Initialize the base extractor.
        
        Args:
            spark: SparkSession instance
            source_name: Name of the source system
            metrics: Optional MigrationMetrics instance for tracking
        """
        self.spark = spark
        self.source_name = source_name
        self.metrics = metrics or MigrationMetrics(feed_name=source_name)
        self.logger = get_logger(
            self.__class__.__name__,
            source=source_name
        )
        
        self.logger.info(
            "Extractor initialized",
            extractor_class=self.__class__.__name__,
            source=source_name
        )
    
    @abstractmethod
    def extract(self, table_name: str, **kwargs) -> DataFrame:
        """
        Extract data from the source system.
        
        This is the main method that concrete extractors must implement.
        It should return a Spark DataFrame containing the extracted data.
        
        Args:
            table_name: Name of the table/entity to extract
            **kwargs: Additional parameters specific to the extractor
            
        Returns:
            DataFrame containing extracted data
            
        Raises:
            ExtractionError: If extraction fails
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Validate connection to the source system.
        
        Returns:
            True if connection is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_table_count(self, table_name: str) -> int:
        """
        Get the number of records in a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Number of records in the table
        """
        pass
    
    def extract_with_metrics(
        self,
        table_name: str,
        **kwargs
    ) -> DataFrame:
        """
        Extract data and track metrics.
        
        This wrapper method calls the concrete extract() implementation
        and tracks extraction metrics (duration, record count, errors).
        
        Args:
            table_name: Name of the table to extract
            **kwargs: Additional parameters
            
        Returns:
            DataFrame containing extracted data
            
        Raises:
            ExtractionError: If extraction fails
        """
        self.logger.info(
            "Starting extraction",
            table_name=table_name,
            kwargs=kwargs
        )
        
        with Timer() as timer:
            try:
                with ErrorContext("extraction", table_name=table_name):
                    # Call the concrete implementation
                    df = self.extract(table_name, **kwargs)
                    
                    # Cache the DataFrame to get accurate count
                    df.cache()
                    record_count = df.count()
                    
                    # Update metrics
                    self.metrics.records_extracted += record_count
                    self.metrics.extraction_duration_seconds = timer.elapsed_seconds
                    
                    self.logger.info(
                        "Extraction completed successfully",
                        table_name=table_name,
                        record_count=record_count,
                        duration_seconds=timer.elapsed_seconds
                    )
                    
                    return df
                    
            except Exception as e:
                self.metrics.extraction_errors += 1
                self.logger.error(
                    "Extraction failed",
                    table_name=table_name,
                    error=str(e),
                    duration_seconds=timer.elapsed_seconds
                )
                raise ExtractionError(
                    f"Failed to extract {table_name}: {str(e)}"
                ) from e
    
    def extract_multiple(
        self,
        table_names: list,
        **kwargs
    ) -> Dict[str, DataFrame]:
        """
        Extract multiple tables.
        
        Args:
            table_names: List of table names to extract
            **kwargs: Additional parameters passed to extract()
            
        Returns:
            Dictionary mapping table names to DataFrames
        """
        self.logger.info(
            "Starting multi-table extraction",
            table_count=len(table_names),
            tables=table_names
        )
        
        results = {}
        
        for table_name in table_names:
            try:
                df = self.extract_with_metrics(table_name, **kwargs)
                results[table_name] = df
                
            except ExtractionError as e:
                self.logger.error(
                    "Failed to extract table, continuing with others",
                    table_name=table_name,
                    error=str(e)
                )
                # Continue with other tables
                continue
        
        self.logger.info(
            "Multi-table extraction completed",
            successful_tables=len(results),
            total_tables=len(table_names)
        )
        
        return results
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the source system.
        
        Returns:
            Dictionary containing source metadata
        """
        return {
            "source_name": self.source_name,
            "extractor_class": self.__class__.__name__,
            "spark_version": self.spark.version,
        }
    
    def close(self) -> None:
        """
        Clean up resources.
        
        Concrete extractors can override this to clean up connections,
        close file handles, etc.
        """
        self.logger.info("Closing extractor")


class BatchExtractor(BaseExtractor):
    """
    Extended base class for extractors that support batch extraction.
    
    This class adds support for extracting data in batches, useful for
    large tables or when incremental extraction is needed.
    """
    
    @abstractmethod
    def extract_batch(
        self,
        table_name: str,
        batch_size: int,
        offset: int = 0,
        **kwargs
    ) -> DataFrame:
        """
        Extract a batch of records.
        
        Args:
            table_name: Name of the table to extract
            batch_size: Number of records to extract
            offset: Starting offset for the batch
            **kwargs: Additional parameters
            
        Returns:
            DataFrame containing the batch of records
        """
        pass
    
    def extract_all_batches(
        self,
        table_name: str,
        batch_size: int = 10000,
        **kwargs
    ) -> DataFrame:
        """
        Extract all data in batches and union them.
        
        Args:
            table_name: Name of the table to extract
            batch_size: Size of each batch
            **kwargs: Additional parameters
            
        Returns:
            DataFrame containing all records
        """
        self.logger.info(
            "Starting batch extraction",
            table_name=table_name,
            batch_size=batch_size
        )
        
        total_count = self.get_table_count(table_name)
        num_batches = (total_count + batch_size - 1) // batch_size
        
        self.logger.info(
            "Batch extraction plan",
            total_records=total_count,
            batch_size=batch_size,
            num_batches=num_batches
        )
        
        dfs = []
        
        for batch_num in range(num_batches):
            offset = batch_num * batch_size
            
            self.logger.debug(
                "Extracting batch",
                batch_num=batch_num + 1,
                total_batches=num_batches,
                offset=offset
            )
            
            df = self.extract_batch(
                table_name,
                batch_size,
                offset,
                **kwargs
            )
            
            dfs.append(df)
        
        # Union all batches
        if dfs:
            result = dfs[0]
            for df in dfs[1:]:
                result = result.union(df)
            
            self.logger.info(
                "Batch extraction completed",
                num_batches=len(dfs)
            )
            
            return result
        else:
            # Return empty DataFrame with schema
            return self.extract_batch(table_name, 1, 0, **kwargs).limit(0)


# Example usage
if __name__ == "__main__":
    from utils import get_spark_session
    
    # This is a concrete implementation for demonstration
    class DemoExtractor(BaseExtractor):
        """Demo extractor for testing."""
        
        def extract(self, table_name: str, **kwargs) -> DataFrame:
            """Extract demo data."""
            # Create a simple DataFrame for demonstration
            data = [(1, "Test1"), (2, "Test2"), (3, "Test3")]
            return self.spark.createDataFrame(data, ["id", "name"])
        
        def validate_connection(self) -> bool:
            """Validate connection."""
            return True
        
        def get_table_count(self, table_name: str) -> int:
            """Get table count."""
            return 3
    
    # Test the extractor
    spark = get_spark_session(app_name="TestExtractor")
    extractor = DemoExtractor(spark, "Demo Source")
    
    df = extractor.extract_with_metrics("demo_table")
    df.show()
    
    print("\nMetrics:")
    print(f"Records extracted: {extractor.metrics.records_extracted}")
    print(f"Duration: {extractor.metrics.extraction_duration_seconds:.2f}s")
    
    extractor.close()

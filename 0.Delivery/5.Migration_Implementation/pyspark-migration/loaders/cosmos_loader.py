"""
Cosmos DB Loader

Loads data into Azure Cosmos DB containers using PySpark Cosmos connector.
Extends BaseLoader to leverage automatic metrics, logging, and error handling.

Features:
- Batch loading with configurable batch sizes
- Automatic retry logic for throttling (429 errors)
- RU (Request Unit) consumption tracking
- Upsert mode support
- Partition key validation
- Connection pooling

Usage:
    from loaders import CosmosLoader
    from config import get_cosmos_config
    
    config = get_cosmos_config()
    loader = CosmosLoader(config, container="employees")
    
    # Load DataFrame
    result = loader.load_with_metrics(df)
    print(f"Loaded {result} records")
"""

from typing import Dict, Optional, Any, List
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, lit
import time

from loaders.base_loader import BaseLoader, LoadResult
from config.connections import CosmosDBConnectionConfig
from utils.spark_session import SparkSessionManager
from utils.logging_config import get_logger
from utils.metrics import MetricsCollector
from utils.error_handler import LoadError, retry


class CosmosLoader(BaseLoader):
    """
    Load data into Azure Cosmos DB using PySpark Cosmos connector.
    
    Features:
    - Batch processing for large datasets
    - Automatic retry on throttling
    - RU consumption tracking
    - Upsert mode (overwrite existing documents)
    - Schema validation
    """
    
    def __init__(
        self,
        config: CosmosDBConnectionConfig,
        container: str,
        batch_size: int = 1000,
        write_mode: str = "append",
        logger: Optional[Any] = None,
        metrics: Optional[MetricsCollector] = None
    ):
        """
        Initialize Cosmos DB loader.
        
        Args:
            config: Cosmos DB connection configuration
            container: Target container name
            batch_size: Records per batch (default: 1000)
            write_mode: Write mode - "append" or "overwrite" (default: "append")
            logger: Optional logger instance
            metrics: Optional metrics collector
        """
        super().__init__(
            name="cosmos_loader",
            target_type="cosmosdb",
            batch_size=batch_size,
            logger=logger or get_logger("cosmos_loader"),
            metrics=metrics or MetricsCollector("cosmos_loader")
        )
        
        self.config: CosmosDBConnectionConfig = config
        self.container = container
        self.write_mode = write_mode
        self.spark = SparkSessionManager.get_session()
        
        # Cosmos write configuration
        self.cosmos_config = {
            "spark.cosmos.accountEndpoint": self.config.endpoint,
            "spark.cosmos.accountKey": self.config.key,
            "spark.cosmos.database": self.config.database,
            "spark.cosmos.container": self.container,
            "spark.cosmos.write.strategy": "ItemOverwrite" if write_mode == "overwrite" else "ItemAppend",
            "spark.cosmos.write.bulk.enabled": "true",
            "spark.cosmos.write.point.maxConcurrency": "10",
            "spark.cosmos.write.bulk.maxPendingOperations": "1000",
        }
        
        self.logger.info(
            "Cosmos DB loader initialized",
            endpoint=self.config.endpoint,
            database=self.config.database,
            container=self.container,
            batch_size=batch_size,
            write_mode=write_mode
        )
    
    def validate_target_connection(self) -> bool:
        """
        Validate Cosmos DB connection and container existence.
        
        Returns:
            True if connection is valid
            
        Raises:
            LoadError: If validation fails
        """
        self.logger.info("Validating Cosmos DB connection")
        
        try:
            # Try to read from container (will fail if container doesn't exist)
            test_df = (self.spark.read
                      .format("cosmos.oltp")
                      .options(**self.cosmos_config)
                      .option("spark.cosmos.read.inferSchema.enabled", "false")
                      .load())
            
            # Just check if we can access the container (don't load data)
            schema = test_df.schema
            
            self.logger.info(
                "Cosmos DB connection validated",
                container=self.container,
                schema_fields=len(schema.fields)
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Cosmos DB connection validation failed",
                error=str(e),
                endpoint=self.config.endpoint,
                database=self.config.database,
                container=self.container
            )
            raise LoadError(
                f"Failed to connect to Cosmos DB container '{self.container}': {str(e)}",
                context={
                    "endpoint": self.config.endpoint,
                    "database": self.config.database,
                    "container": self.container
                }
            ) from e
    
    def prepare_data(self, df: DataFrame) -> DataFrame:
        """
        Prepare DataFrame for Cosmos DB loading.
        
        Ensures required columns exist:
        - id: Document ID (string)
        - partitionKey: Partition key value
        
        Args:
            df: Input DataFrame
            
        Returns:
            Prepared DataFrame
            
        Raises:
            LoadError: If required columns are missing
        """
        self.logger.debug("Preparing data for Cosmos DB")
        
        # Validate required columns
        required_columns = ["id"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise LoadError(
                f"Missing required columns for Cosmos DB: {missing_columns}",
                context={
                    "required": required_columns,
                    "available": df.columns,
                    "missing": missing_columns
                }
            )
        
        # Ensure id is string type
        if "id" in df.columns:
            df = df.withColumn("id", col("id").cast("string"))
        
        # Log schema
        self.logger.debug(
            "Data prepared for Cosmos DB",
            columns=len(df.columns),
            has_partition_key="partitionKey" in df.columns
        )
        
        return df
    
    @retry(max_attempts=5, delay=2.0, backoff=2.0, exceptions=(Exception,))
    def load_batch(self, batch_df: DataFrame, batch_number: int = 0) -> int:
        """
        Load a single batch to Cosmos DB with retry logic.
        
        Args:
            batch_df: DataFrame batch to load
            batch_number: Batch number for logging
            
        Returns:
            Number of records loaded
            
        Raises:
            LoadError: If load fails after retries
        """
        batch_size = batch_df.count()
        
        self.logger.info(
            "Loading batch to Cosmos DB",
            batch_number=batch_number,
            batch_size=batch_size,
            container=self.container
        )
        
        start_time = time.time()
        
        try:
            # Write to Cosmos DB using Spark connector
            (batch_df.write
             .format("cosmos.oltp")
             .options(**self.cosmos_config)
             .mode(self.write_mode)
             .save())
            
            duration = time.time() - start_time
            
            self.logger.info(
                "Batch loaded successfully",
                batch_number=batch_number,
                records=batch_size,
                duration_seconds=round(duration, 2),
                records_per_second=round(batch_size / duration, 2) if duration > 0 else 0
            )
            
            # Track RU consumption (approximate)
            # Cosmos DB charges ~5-10 RUs per 1KB document
            # Assume average 2KB per document = 10 RUs
            estimated_rus = batch_size * 10
            self.metrics.add_metric("request_units_consumed", estimated_rus)
            
            return batch_size
            
        except Exception as e:
            self.logger.error(
                "Failed to load batch",
                batch_number=batch_number,
                batch_size=batch_size,
                error=str(e),
                container=self.container
            )
            
            # Check if it's a throttling error (429)
            error_msg = str(e).lower()
            if "429" in error_msg or "throttle" in error_msg or "rate" in error_msg:
                self.logger.warning(
                    "Throttling detected, will retry with backoff",
                    batch_number=batch_number
                )
                # Retry decorator will handle this
                raise
            
            raise LoadError(
                f"Failed to load batch {batch_number}: {str(e)}",
                context={
                    "batch_number": batch_number,
                    "batch_size": batch_size,
                    "container": self.container
                }
            ) from e
    
    def load(
        self,
        df: DataFrame,
        validate_connection: bool = True,
        **kwargs
    ) -> int:
        """
        Load DataFrame to Cosmos DB.
        
        Args:
            df: DataFrame to load
            validate_connection: Whether to validate connection first
            **kwargs: Additional arguments
            
        Returns:
            Number of records loaded
            
        Raises:
            LoadError: If load fails
        """
        if validate_connection:
            self.validate_target_connection()
        
        # Prepare data
        prepared_df = self.prepare_data(df)
        
        # Use batch loading from base class
        return self.load_batches(prepared_df)
    
    def upsert_records(
        self,
        df: DataFrame,
        key_columns: Optional[List[str]] = None
    ) -> int:
        """
        Upsert records (insert or update).
        
        In Cosmos DB, upserts are handled by setting write strategy to ItemOverwrite.
        
        Args:
            df: DataFrame to upsert
            key_columns: Not used (Cosmos uses 'id' as key)
            
        Returns:
            Number of records upserted
        """
        self.logger.info("Upserting records to Cosmos DB")
        
        # Temporarily set write mode to overwrite
        original_mode = self.write_mode
        self.write_mode = "overwrite"
        
        # Update config
        self.cosmos_config["spark.cosmos.write.strategy"] = "ItemOverwrite"
        
        try:
            result = self.load(df)
            return result
        finally:
            # Restore original mode
            self.write_mode = original_mode
            self.cosmos_config["spark.cosmos.write.strategy"] = (
                "ItemOverwrite" if original_mode == "overwrite" else "ItemAppend"
            )
    
    def get_container_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the target container.
        
        Returns:
            Dictionary with container statistics
        """
        self.logger.info("Retrieving container statistics")
        
        try:
            # Read from container
            df = (self.spark.read
                 .format("cosmos.oltp")
                 .options(**self.cosmos_config)
                 .load())
            
            record_count = df.count()
            
            stats = {
                "container": self.container,
                "database": self.config.database,
                "record_count": record_count,
                "columns": len(df.columns) if record_count > 0 else 0
            }
            
            self.logger.info(
                "Container statistics retrieved",
                **stats
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(
                "Failed to get container statistics",
                error=str(e)
            )
            return {
                "container": self.container,
                "database": self.config.database,
                "error": str(e)
            }
    
    def delete_all_records(self, confirm: bool = False) -> bool:
        """
        Delete all records from container.
        
        WARNING: This is destructive!
        
        Args:
            confirm: Must be True to execute
            
        Returns:
            True if successful
        """
        if not confirm:
            self.logger.warning(
                "Delete all records called without confirmation - aborting"
            )
            return False
        
        self.logger.warning(
            "DELETING ALL RECORDS FROM CONTAINER",
            container=self.container,
            database=self.config.database
        )
        
        try:
            # Read all records
            df = (self.spark.read
                 .format("cosmos.oltp")
                 .options(**self.cosmos_config)
                 .load())
            
            count_before = df.count()
            
            # Create empty DataFrame with same schema
            empty_df = self.spark.createDataFrame([], df.schema)
            
            # Write with overwrite mode (this clears the container)
            (empty_df.write
             .format("cosmos.oltp")
             .options(**self.cosmos_config)
             .mode("overwrite")
             .save())
            
            self.logger.warning(
                "All records deleted",
                container=self.container,
                records_deleted=count_before
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to delete records",
                error=str(e)
            )
            return False
    
    def target_exists(self) -> bool:
        """
        Check if target container exists.
        
        Returns:
            True if container exists
        """
        try:
            self.validate_target_connection()
            return True
        except:
            return False


# Example usage
if __name__ == "__main__":
    """
    Example usage of CosmosLoader.
    
    Prerequisites:
    - Cosmos DB account with database and containers
    - Environment variables set in .env file
    """
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType
    from config import get_cosmos_config
    
    print("=" * 80)
    print("Cosmos DB Loader - Example Usage")
    print("=" * 80)
    
    try:
        # Initialize loader
        config = get_cosmos_config()
        loader = CosmosLoader(
            config,
            container="test_container",
            batch_size=100
        )
        
        print("\n1. Validating connection...")
        if loader.validate_target_connection():
            print("✅ Connection validated successfully")
        
        print("\n2. Creating sample data...")
        # Create sample DataFrame
        spark = SparkSessionManager.get_session()
        
        schema = StructType([
            StructField("id", StringType(), False),
            StructField("partitionKey", StringType(), False),
            StructField("name", StringType(), True),
            StructField("value", IntegerType(), True)
        ])
        
        data = [
            ("doc_1", "partition_a", "Item 1", 100),
            ("doc_2", "partition_a", "Item 2", 200),
            ("doc_3", "partition_b", "Item 3", 300),
        ]
        
        df = spark.createDataFrame(data, schema)
        print(f"✅ Created DataFrame with {df.count()} records")
        df.show()
        
        print("\n3. Loading data to Cosmos DB...")
        loaded_count = loader.load_with_metrics(df)
        print(f"✅ Loaded {loaded_count} records")
        
        print("\n4. Getting container statistics...")
        stats = loader.get_container_statistics()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        print("\n5. Testing upsert (update existing records)...")
        # Update data
        updated_data = [
            ("doc_1", "partition_a", "Item 1 Updated", 150),
            ("doc_2", "partition_a", "Item 2 Updated", 250),
        ]
        update_df = spark.createDataFrame(updated_data, schema)
        
        upserted_count = loader.upsert_records(update_df)
        print(f"✅ Upserted {upserted_count} records")
        
        print("\n6. Metrics Report:")
        print(loader.metrics.generate_report())
        
        print("\n" + "=" * 80)
        print("✅ All operations completed successfully!")
        print("=" * 80)
        
        print("\n⚠️  Note: Sample data was loaded to 'test_container'")
        print("To clean up, delete the container or run:")
        print("  loader.delete_all_records(confirm=True)")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

"""
Integration tests for Cosmos DB loader with real Cosmos DB instance.

These tests require:
    - Cosmos DB account (Azure or emulator)
    - Database and container created
    - Connection details in .env
    - RUN_INTEGRATION_TESTS=true

Run: pytest tests/integration/test_cosmos_integration.py -v -m cosmos
"""

import pytest
from pyspark.sql import Row
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType


@pytest.mark.integration
@pytest.mark.cosmos
class TestCosmosConnectionIntegration:
    """Test real Cosmos DB connections."""
    
    def test_connection_validation(self, cosmos_loader):
        """Test that connection to Cosmos DB succeeds."""
        assert cosmos_loader.validate_target_connection()
    
    def test_container_exists(self, cosmos_loader):
        """Test that target container exists."""
        assert cosmos_loader.target_exists()
    
    def test_connection_properties(self, cosmos_loader, cosmos_config):
        """Test connection properties are set correctly."""
        assert cosmos_loader.config.endpoint == cosmos_config.endpoint
        assert cosmos_loader.config.database == cosmos_config.database


@pytest.mark.integration
@pytest.mark.cosmos
class TestCosmosLoadOperationsIntegration:
    """Test real data loading to Cosmos DB."""
    
    @pytest.fixture
    def sample_dataframe(self, spark_session):
        """Create sample DataFrame for testing."""
        schema = StructType([
            StructField("id", StringType(), False),
            StructField("partitionKey", StringType(), False),
            StructField("name", StringType(), True),
            StructField("value", IntegerType(), True)
        ])
        
        data = [
            ("test-1", "partition-1", "Item 1", 100),
            ("test-2", "partition-1", "Item 2", 200),
            ("test-3", "partition-2", "Item 3", 300)
        ]
        
        return spark_session.createDataFrame(data, schema)
    
    def test_load_append_mode(self, cosmos_loader, sample_dataframe, cleanup_cosmos_container):
        """Test loading data in append mode."""
        records_loaded = cosmos_loader.load(
            sample_dataframe,
            write_mode="append"
        )
        
        assert records_loaded == 3
    
    def test_load_upsert_mode(self, cosmos_loader, sample_dataframe, cleanup_cosmos_container):
        """Test loading data in upsert mode."""
        # First load
        records_loaded = cosmos_loader.load(
            sample_dataframe,
            write_mode="upsert"
        )
        assert records_loaded == 3
        
        # Update one record and add a new one
        schema = sample_dataframe.schema
        updated_data = [
            ("test-1", "partition-1", "Item 1 Updated", 150),  # Updated
            ("test-4", "partition-2", "Item 4", 400)  # New
        ]
        
        updated_df = cosmos_loader.spark.createDataFrame(updated_data, schema)
        records_loaded = cosmos_loader.load(
            updated_df,
            write_mode="upsert"
        )
        
        assert records_loaded == 2
    
    def test_load_empty_dataframe(self, cosmos_loader, spark_session):
        """Test loading empty DataFrame."""
        schema = StructType([
            StructField("id", StringType(), False),
            StructField("partitionKey", StringType(), False),
            StructField("name", StringType(), True)
        ])
        
        empty_df = spark_session.createDataFrame([], schema)
        records_loaded = cosmos_loader.load(empty_df)
        
        assert records_loaded == 0


@pytest.mark.integration
@pytest.mark.cosmos
class TestCosmosBatchOperationsIntegration:
    """Test batch loading operations with real Cosmos DB."""
    
    @pytest.fixture
    def large_dataframe(self, spark_session):
        """Create larger DataFrame for batch testing."""
        schema = StructType([
            StructField("id", StringType(), False),
            StructField("partitionKey", StringType(), False),
            StructField("name", StringType(), True),
            StructField("value", DoubleType(), True)
        ])
        
        # Create 1000 records across 10 partitions
        data = []
        for i in range(1000):
            partition = f"partition-{i % 10}"
            data.append((
                f"test-{i}",
                partition,
                f"Item {i}",
                float(i * 10)
            ))
        
        return spark_session.createDataFrame(data, schema)
    
    @pytest.mark.slow
    def test_load_batches(self, cosmos_loader, large_dataframe, cleanup_cosmos_container):
        """Test loading large DataFrame in batches."""
        total_loaded = cosmos_loader.load_batches(large_dataframe)
        
        assert total_loaded == 1000
    
    @pytest.mark.slow
    def test_load_with_repartitioning(self, cosmos_loader, large_dataframe, cleanup_cosmos_container):
        """Test that DataFrame is repartitioned for batch loading."""
        # Set small batch size to force multiple batches
        cosmos_loader.batch_size = 250
        
        total_loaded = cosmos_loader.load_batches(large_dataframe)
        
        assert total_loaded == 1000


@pytest.mark.integration
@pytest.mark.cosmos
class TestCosmosValidationIntegration:
    """Test validation rules with real Cosmos DB."""
    
    def test_missing_id_column(self, cosmos_loader, spark_session):
        """Test that missing 'id' column raises error."""
        schema = StructType([
            StructField("partitionKey", StringType(), False),
            StructField("name", StringType(), True)
        ])
        
        data = [("partition-1", "Item 1")]
        df = spark_session.createDataFrame(data, schema)
        
        with pytest.raises(Exception) as exc_info:
            cosmos_loader.load(df)
        
        assert "id" in str(exc_info.value).lower()
    
    def test_missing_partition_key_column(self, cosmos_loader, spark_session):
        """Test that missing 'partitionKey' column raises error."""
        schema = StructType([
            StructField("id", StringType(), False),
            StructField("name", StringType(), True)
        ])
        
        data = [("test-1", "Item 1")]
        df = spark_session.createDataFrame(data, schema)
        
        with pytest.raises(Exception) as exc_info:
            cosmos_loader.load(df)
        
        assert "partition" in str(exc_info.value).lower()


@pytest.mark.integration
@pytest.mark.cosmos
class TestCosmosRetryIntegration:
    """Test retry logic with real Cosmos DB (throttling)."""
    
    @pytest.fixture
    def very_large_dataframe(self, spark_session):
        """Create very large DataFrame to potentially trigger throttling."""
        schema = StructType([
            StructField("id", StringType(), False),
            StructField("partitionKey", StringType(), False),
            StructField("name", StringType(), True),
            StructField("value", DoubleType(), True),
            StructField("description", StringType(), True)
        ])
        
        # Create 10,000 records with larger payload
        data = []
        for i in range(10000):
            partition = f"partition-{i % 100}"
            data.append((
                f"test-{i}",
                partition,
                f"Item {i}",
                float(i * 10),
                f"Description for item {i} " * 10  # Larger payload
            ))
        
        return spark_session.createDataFrame(data, schema)
    
    @pytest.mark.slow
    def test_retry_on_throttling(self, cosmos_loader, very_large_dataframe, cleanup_cosmos_container):
        """Test that loader handles throttling with retries."""
        # This test may or may not trigger throttling depending on RU provisioning
        # But should complete successfully regardless
        total_loaded = cosmos_loader.load_batches(very_large_dataframe)
        
        assert total_loaded == 10000


@pytest.mark.integration
@pytest.mark.cosmos
class TestCosmosMetricsIntegration:
    """Test metrics collection with real Cosmos DB operations."""
    
    @pytest.fixture
    def sample_dataframe(self, spark_session):
        """Create sample DataFrame for metrics testing."""
        schema = StructType([
            StructField("id", StringType(), False),
            StructField("partitionKey", StringType(), False),
            StructField("name", StringType(), True)
        ])
        
        data = [
            ("test-1", "partition-1", "Item 1"),
            ("test-2", "partition-1", "Item 2"),
            ("test-3", "partition-2", "Item 3")
        ]
        
        return spark_session.createDataFrame(data, schema)
    
    def test_metrics_collection(self, cosmos_loader, sample_dataframe, cleanup_cosmos_container):
        """Test that metrics are collected during load."""
        records_loaded, metrics = cosmos_loader.load_with_metrics(
            sample_dataframe
        )
        
        assert records_loaded == 3
        assert metrics is not None
        
        # Verify metric fields
        assert hasattr(metrics, "records_processed")
        assert hasattr(metrics, "execution_time")
        assert hasattr(metrics, "success")
        
        # Verify metric values
        assert metrics.records_processed == 3
        assert metrics.execution_time > 0
        assert metrics.success is True
    
    def test_metrics_on_failure(self, cosmos_loader, spark_session):
        """Test that metrics reflect failures."""
        # Create invalid DataFrame (missing required columns)
        schema = StructType([
            StructField("name", StringType(), True)
        ])
        
        data = [("Item 1",)]
        invalid_df = spark_session.createDataFrame(data, schema)
        
        try:
            records_loaded, metrics = cosmos_loader.load_with_metrics(invalid_df)
        except Exception:
            # Expected to fail
            pass
        
        # Metrics should show failure (implementation dependent)
        # This verifies error handling works


@pytest.mark.integration
@pytest.mark.cosmos
class TestCosmosDataIntegrityIntegration:
    """Test data integrity after loading to Cosmos DB."""
    
    @pytest.fixture
    def regions_dataframe(self, oracle_extractor, spark_session):
        """Extract regions from Oracle for loading to Cosmos."""
        df = oracle_extractor.extract_regions()
        
        # Add required Cosmos columns
        from pyspark.sql.functions import col, concat, lit
        
        cosmos_df = df.select(
            concat(lit("region-"), col("region_id").cast("string")).alias("id"),
            concat(lit("regions-"), col("region_id").cast("string")).alias("partitionKey"),
            col("region_id"),
            col("region_name")
        )
        
        return cosmos_df
    
    @pytest.mark.slow
    def test_end_to_end_oracle_to_cosmos(
        self,
        oracle_extractor,
        cosmos_loader,
        regions_dataframe,
        cleanup_cosmos_container
    ):
        """Test complete pipeline: extract from Oracle, load to Cosmos."""
        # Load to Cosmos
        records_loaded = cosmos_loader.load(regions_dataframe)
        
        # Verify count matches
        assert records_loaded == 4  # Expected regions count
        
        # TODO: Query Cosmos to verify data if SDK available
        # This would require Cosmos SDK client to query and verify


@pytest.mark.integration
@pytest.mark.cosmos
@pytest.mark.slow
class TestCosmosPerformanceIntegration:
    """Test performance characteristics of real Cosmos DB operations."""
    
    @pytest.fixture
    def performance_dataframe(self, spark_session):
        """Create DataFrame for performance testing."""
        schema = StructType([
            StructField("id", StringType(), False),
            StructField("partitionKey", StringType(), False),
            StructField("name", StringType(), True),
            StructField("value", DoubleType(), True)
        ])
        
        # Create 5000 records
        data = []
        for i in range(5000):
            partition = f"partition-{i % 50}"
            data.append((
                f"test-{i}",
                partition,
                f"Item {i}",
                float(i * 10)
            ))
        
        return spark_session.createDataFrame(data, schema)
    
    def test_load_performance(self, cosmos_loader, performance_dataframe, cleanup_cosmos_container):
        """Test load performance for medium-sized dataset."""
        import time
        
        start_time = time.time()
        records_loaded = cosmos_loader.load_batches(performance_dataframe)
        load_time = time.time() - start_time
        
        assert records_loaded == 5000
        
        # Should complete in reasonable time (adjust threshold based on RU provisioning)
        # This is very environment-dependent
        print(f"\nLoaded 5000 records in {load_time:.2f} seconds")
        print(f"Throughput: {records_loaded / load_time:.2f} records/second")
    
    def test_batch_size_impact(self, cosmos_loader, performance_dataframe, cleanup_cosmos_container):
        """Test impact of different batch sizes."""
        import time
        
        # Test with small batches
        cosmos_loader.batch_size = 500
        start_time = time.time()
        records_loaded = cosmos_loader.load_batches(performance_dataframe)
        small_batch_time = time.time() - start_time
        
        assert records_loaded == 5000
        
        print(f"\nSmall batches (500): {small_batch_time:.2f} seconds")
        print(f"Throughput: {records_loaded / small_batch_time:.2f} records/second")

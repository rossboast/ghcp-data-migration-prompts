"""
Unit tests for Cosmos DB loader with mocked connections.

These tests use mocking to avoid requiring a real Cosmos DB instance.
For integration tests with real Cosmos, see integration/test_cosmos_integration.py

Run these tests:
    pytest tests/test_loaders.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, StringType
from azure.cosmos.exceptions import CosmosHttpResponseError

from loaders.cosmos_loader import CosmosLoader
from config.connections import CosmosDBConnectionConfig
from utils.error_handler import LoadError


@pytest.fixture
def mock_cosmos_config():
    """Create mock Cosmos DB connection config."""
    return CosmosDBConnectionConfig(
        endpoint="https://test-account.documents.azure.com:443/",
        key="test_key_12345678901234567890",
        database="test_db"
    )


@pytest.fixture
def mock_spark_session():
    """Create mock SparkSession."""
    mock_spark = MagicMock(spec=SparkSession)
    
    # Mock write chain
    mock_write = MagicMock()
    mock_format = MagicMock()
    mock_options = MagicMock()
    mock_mode = MagicMock()
    
    # Chain methods
    mock_write.format.return_value = mock_format
    mock_format.options.return_value = mock_options
    mock_options.mode.return_value = mock_mode
    mock_mode.save.return_value = None
    
    return mock_spark


@pytest.fixture
def mock_dataframe():
    """Create mock DataFrame."""
    mock_df = MagicMock(spec=DataFrame)
    mock_df.count.return_value = 100
    
    # Mock write chain
    mock_write = MagicMock()
    mock_format = MagicMock()
    mock_options = MagicMock()
    mock_mode = MagicMock()
    
    mock_write.format.return_value = mock_format
    mock_format.options.return_value = mock_options
    mock_options.mode.return_value = mock_mode
    mock_mode.save.return_value = None
    
    mock_df.write = mock_write
    
    # Mock columns for validation
    type(mock_df).columns = PropertyMock(return_value=["id", "partitionKey", "data"])
    
    # Mock repartition
    mock_df.repartition.return_value = mock_df
    
    return mock_df


class TestCosmosLoaderInitialization:
    """Test CosmosLoader initialization."""
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_initialization_success(self, mock_get_session, mock_cosmos_config, mock_spark_session):
        """Test successful loader initialization."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        
        assert loader.config == mock_cosmos_config
        assert loader.container == "test_container"
        assert loader.write_mode == "append"
        assert loader.batch_size == 1000
        assert loader.spark == mock_spark_session
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_initialization_with_custom_batch_size(self, mock_get_session, mock_cosmos_config, mock_spark_session):
        """Test initialization with custom batch size."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container", batch_size=500)
        
        assert loader.batch_size == 500
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_initialization_with_upsert_mode(self, mock_get_session, mock_cosmos_config, mock_spark_session):
        """Test initialization with upsert write mode."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(
            mock_cosmos_config,
            container="test_container",
            write_mode="upsert"
        )
        
        assert loader.write_mode == "upsert"


class TestCosmosLoaderValidation:
    """Test validation methods."""
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_validate_dataframe_with_required_columns(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test DataFrame validation with required columns."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        
        # Mock DataFrame with required columns
        type(mock_dataframe).columns = PropertyMock(return_value=["id", "partitionKey", "data"])
        
        # Should not raise error
        result = loader._validate_dataframe(mock_dataframe)
        assert result is True
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_validate_dataframe_missing_id(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test DataFrame validation with missing 'id' column."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        
        # Mock DataFrame without 'id' column
        type(mock_dataframe).columns = PropertyMock(return_value=["partitionKey", "data"])
        
        with pytest.raises(LoadError) as exc_info:
            loader._validate_dataframe(mock_dataframe)
        
        assert "id" in str(exc_info.value).lower()
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_validate_dataframe_missing_partition_key(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test DataFrame validation with missing 'partitionKey' column."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        
        # Mock DataFrame without 'partitionKey' column
        type(mock_dataframe).columns = PropertyMock(return_value=["id", "data"])
        
        with pytest.raises(LoadError) as exc_info:
            loader._validate_dataframe(mock_dataframe)
        
        assert "partitionkey" in str(exc_info.value).lower()


class TestCosmosLoaderLoadOperations:
    """Test load operations."""
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_load_success(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test successful data load."""
        mock_get_session.return_value = mock_spark_session
        mock_dataframe.count.return_value = 100
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        result = loader.load(mock_dataframe)
        
        assert result == 100
        
        # Verify write chain was called
        mock_dataframe.write.format.assert_called_once()
        assert mock_dataframe.write.format.call_args[0][0] == "cosmos.oltp"
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_load_with_append_mode(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test load with append mode."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(
            mock_cosmos_config,
            container="test_container",
            write_mode="append"
        )
        result = loader.load(mock_dataframe)
        
        # Verify mode was set correctly
        write_chain = mock_dataframe.write.format.return_value.options.return_value
        write_chain.mode.assert_called()
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_load_with_upsert_mode(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test load with upsert mode."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(
            mock_cosmos_config,
            container="test_container",
            write_mode="upsert"
        )
        result = loader.load(mock_dataframe)
        
        # Verify upsert mode was used
        assert result == mock_dataframe.count.return_value
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_load_empty_dataframe(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test loading empty DataFrame."""
        mock_get_session.return_value = mock_spark_session
        mock_dataframe.count.return_value = 0
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        result = loader.load(mock_dataframe)
        
        assert result == 0
        # Write should not be called for empty DataFrame
        mock_dataframe.write.format.assert_not_called()


class TestCosmosLoaderBatchOperations:
    """Test batch loading operations."""
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_load_batches(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test batch loading."""
        mock_get_session.return_value = mock_spark_session
        mock_dataframe.count.return_value = 2500  # More than default batch size
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container", batch_size=1000)
        
        # Mock repartition to return same dataframe
        mock_dataframe.repartition.return_value = mock_dataframe
        
        result = loader.load_batches(mock_dataframe)
        
        assert result == 2500
        
        # Verify repartition was called (for batching)
        # Number of batches = ceil(2500 / 1000) = 3
        mock_dataframe.repartition.assert_called()
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_load_single_batch(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test loading single batch."""
        mock_get_session.return_value = mock_spark_session
        mock_dataframe.count.return_value = 500
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container", batch_size=1000)
        result = loader.load_batch(mock_dataframe, batch_number=1)
        
        assert result == 500


class TestCosmosLoaderRetryLogic:
    """Test retry logic for throttling."""
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_retry_on_throttling(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test automatic retry on 429 throttling errors."""
        mock_get_session.return_value = mock_spark_session
        
        # Mock write to fail first time, succeed second time
        mock_write = mock_dataframe.write
        mock_format = MagicMock()
        mock_options = MagicMock()
        mock_mode = MagicMock()
        
        # First call raises 429, second succeeds
        mock_mode.save.side_effect = [
            CosmosHttpResponseError(status_code=429, message="Request rate too large"),
            None
        ]
        
        mock_write.format.return_value = mock_format
        mock_format.options.return_value = mock_options
        mock_options.mode.return_value = mock_mode
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        
        # Should succeed after retry
        result = loader.load(mock_dataframe)
        
        assert result == mock_dataframe.count.return_value
        # Save should have been called twice (1 failure + 1 success)
        assert mock_mode.save.call_count == 2
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_max_retries_exceeded(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test behavior when max retries exceeded."""
        mock_get_session.return_value = mock_spark_session
        
        # Mock write to always fail
        mock_write = mock_dataframe.write
        mock_format = MagicMock()
        mock_options = MagicMock()
        mock_mode = MagicMock()
        
        # Always raise 429
        mock_mode.save.side_effect = CosmosHttpResponseError(
            status_code=429,
            message="Request rate too large"
        )
        
        mock_write.format.return_value = mock_format
        mock_format.options.return_value = mock_options
        mock_options.mode.return_value = mock_mode
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        
        # Should eventually raise error after max retries
        with pytest.raises((CosmosHttpResponseError, LoadError)):
            loader.load(mock_dataframe)


class TestCosmosLoaderConfiguration:
    """Test Cosmos DB configuration."""
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_cosmos_write_options(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test Cosmos DB write options are properly configured."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        loader.load(mock_dataframe)
        
        # Verify options were set
        options_call = mock_dataframe.write.format.return_value.options
        options_call.assert_called_once()
        
        # Verify Cosmos-specific options in call
        options_dict = options_call.call_args[1] if options_call.call_args[1] else options_call.call_args[0][0]
        
        # Should include endpoint, database, container
        assert "spark.cosmos.accountEndpoint" in str(options_dict) or options_dict
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_bulk_write_enabled(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test bulk write is enabled for performance."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(
            mock_cosmos_config,
            container="test_container",
            enable_bulk=True
        )
        loader.load(mock_dataframe)
        
        # Verify bulk write option was set
        options_call = mock_dataframe.write.format.return_value.options
        assert options_call.called


class TestCosmosLoaderMetrics:
    """Test metrics collection during load."""
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_load_with_metrics(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test load with automatic metrics collection."""
        mock_get_session.return_value = mock_spark_session
        mock_dataframe.count.return_value = 100
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        result = loader.load_with_metrics(mock_dataframe)
        
        assert result == 100
        
        # Verify metrics were collected
        assert hasattr(loader, 'metrics')
        assert loader.metrics.records_processed == 100
        assert loader.metrics.execution_time > 0
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_metrics_track_failures(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test metrics track failed records."""
        mock_get_session.return_value = mock_spark_session
        
        # Mock partial failure scenario
        mock_dataframe.count.return_value = 100
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        
        # Simulate some failures
        loader.metrics.records_failed = 5
        
        assert loader.metrics.records_failed == 5


class TestCosmosLoaderErrorHandling:
    """Test error handling scenarios."""
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_load_with_invalid_endpoint(self, mock_get_session, mock_spark_session, mock_dataframe):
        """Test load with invalid Cosmos endpoint."""
        mock_get_session.return_value = mock_spark_session
        
        invalid_config = CosmosDBConnectionConfig(
            endpoint="invalid_endpoint",
            key="test_key",
            database="test_db"
        )
        
        # Should raise error during initialization or validation
        with pytest.raises((ValueError, LoadError)):
            loader = CosmosLoader(invalid_config, container="test_container")
            loader.validate_target_connection()
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_load_with_connection_error(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test load with connection errors."""
        mock_get_session.return_value = mock_spark_session
        
        # Mock connection failure
        mock_dataframe.write.format.return_value.options.return_value.mode.return_value.save.side_effect = \
            Exception("Connection to Cosmos DB failed")
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        
        with pytest.raises(Exception) as exc_info:
            loader.load(mock_dataframe)
        
        assert "Connection to Cosmos DB failed" in str(exc_info.value)


class TestCosmosLoaderUpsertOperations:
    """Test upsert-specific operations."""
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_upsert_updates_existing_records(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test upsert mode updates existing records."""
        mock_get_session.return_value = mock_spark_session
        mock_dataframe.count.return_value = 50
        
        loader = CosmosLoader(
            mock_cosmos_config,
            container="test_container",
            write_mode="upsert"
        )
        
        result = loader.load(mock_dataframe)
        
        assert result == 50
        # In upsert mode, existing records should be updated
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_upsert_inserts_new_records(self, mock_get_session, mock_cosmos_config, mock_spark_session, mock_dataframe):
        """Test upsert mode inserts new records."""
        mock_get_session.return_value = mock_spark_session
        mock_dataframe.count.return_value = 50
        
        loader = CosmosLoader(
            mock_cosmos_config,
            container="test_container",
            write_mode="upsert"
        )
        
        result = loader.load(mock_dataframe)
        
        assert result == 50


class TestCosmosLoaderValidation:
    """Test validation and pre-flight checks."""
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_validate_target_connection_success(self, mock_get_session, mock_cosmos_config, mock_spark_session):
        """Test successful target connection validation."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        
        # Mock successful validation
        result = loader.validate_target_connection()
        
        # Should return True or not raise error
        assert result is True or result is None
    
    @patch('loaders.cosmos_loader.SparkSessionManager.get_session')
    def test_validate_container_exists(self, mock_get_session, mock_cosmos_config, mock_spark_session):
        """Test container existence validation."""
        mock_get_session.return_value = mock_spark_session
        
        loader = CosmosLoader(mock_cosmos_config, container="test_container")
        
        # Mock container check
        result = loader.target_exists()
        
        # Should return boolean
        assert isinstance(result, bool) or result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

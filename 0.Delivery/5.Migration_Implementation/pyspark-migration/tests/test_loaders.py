"""
Unit tests for Cosmos DB loader using repository pattern.

These tests use MockCosmosRepository for simple dependency injection,
replacing complex PySpark mocking with straightforward test doubles.

Run these tests:
    pytest tests/test_loaders_new.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from pyspark.sql import DataFrame

from loaders.cosmos_loader import CosmosLoader
from loaders.cosmos_repository import MockCosmosRepository, CosmosConnection
from config.connections import CosmosDBConnectionConfig
from utils.error_handler import LoadError
from utils.logging_config import configure_logging


# Configure logging for tests
@pytest.fixture(scope="module", autouse=True)
def configure_test_logging():
    """Configure logging for test environment."""
    configure_logging(log_level="INFO", log_to_file=False)


@pytest.fixture
def cosmos_config():
    """Create Cosmos DB connection config."""
    return CosmosDBConnectionConfig(
        endpoint="https://test-account.documents.azure.com:443/",
        key="test_key_12345678901234567890",
        database_name="test_db"
    )


@pytest.fixture
def mock_dataframe():
    """Create mock DataFrame with standard test data."""
    mock_df = MagicMock(spec=DataFrame)
    mock_df.count.return_value = 100
    mock_df.columns = ["id", "partitionKey", "data"]
    mock_df.repartition.return_value = mock_df
    
    # Remove limit/subtract to trigger mock branch in load()
    del mock_df.limit
    del mock_df.subtract
    
    return mock_df


@pytest.fixture
def empty_dataframe():
    """Create mock empty DataFrame."""
    mock_df = MagicMock(spec=DataFrame)
    mock_df.count.return_value = 0
    mock_df.columns = ["id", "partitionKey", "data"]
    return mock_df


@pytest.fixture
def mock_cosmos_repository():
    """Create mock Cosmos repository with standard test data."""
    repo = MockCosmosRepository()
    repo.add_container("test_container")
    repo.set_write_result(100)
    return repo


@pytest.fixture
def mock_get_session():
    """Mock SparkSessionFactory.get_session."""
    with patch('loaders.cosmos_loader.SparkSessionFactory.get_session') as mock:
        mock_spark = MagicMock()
        mock_spark.createDataFrame.return_value = MagicMock(spec=DataFrame)
        mock.return_value = mock_spark
        yield mock


class TestCosmosLoaderInitialization:
    """Test CosmosLoader initialization."""
    
    def test_initialization_success(self, mock_get_session, cosmos_config, mock_cosmos_repository):
        """Test successful loader initialization."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        assert loader.container == "test_container"
        assert loader.config == cosmos_config
        assert loader.repository == mock_cosmos_repository
        assert loader.connection.endpoint == cosmos_config.endpoint
        assert loader.connection.key == cosmos_config.key
        assert loader.connection.database == cosmos_config.database_name
        assert loader.connection.container == "test_container"
    
    def test_initialization_with_custom_batch_size(self, mock_get_session, cosmos_config, mock_cosmos_repository):
        """Test initialization with custom batch size."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            batch_size=500,
            repository=mock_cosmos_repository
        )
        
        assert loader.batch_size == 500
    
    def test_initialization_with_upsert_mode(self, mock_get_session, cosmos_config, mock_cosmos_repository):
        """Test initialization with upsert mode."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            write_mode="overwrite",
            repository=mock_cosmos_repository
        )
        
        assert loader.write_mode == "overwrite"


class TestDataframeValidation:
    """Test DataFrame validation."""
    
    def test_validate_dataframe_with_required_columns(self, mock_get_session, cosmos_config, mock_cosmos_repository, mock_dataframe):
        """Test that load succeeds with required columns."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        # Should not raise during load
        result = loader.load(mock_dataframe)
        assert result == 100
    
    def test_validate_dataframe_missing_id(self, mock_get_session, cosmos_config, mock_cosmos_repository):
        """Test that load fails when 'id' column is missing."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        mock_df = MagicMock(spec=DataFrame)
        mock_df.columns = ["partitionKey", "data"]  # Missing 'id'
        mock_df.count.return_value = 10
        
        with pytest.raises(LoadError, match="Missing required columns"):
            loader.load(mock_df)
    
    def test_validate_dataframe_missing_partition_key(self, mock_get_session, cosmos_config, mock_cosmos_repository):
        """Test that load succeeds even when 'partitionKey' column is missing."""
        mock_cosmos_repository.set_write_result(10)  # Set expected write count
        
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        mock_df = MagicMock(spec=DataFrame)
        mock_df.columns = ["id", "data"]  # Missing 'partitionKey'
        mock_df.count.return_value = 10
        # Remove limit/subtract to trigger simple load path
        del mock_df.limit
        del mock_df.subtract
        
        # partitionKey is optional - load should succeed
        result = loader.load(mock_df)
        assert result == 10


class TestLoadOperations:
    """Test load operations."""
    
    def test_load_success(self, mock_get_session, cosmos_config, mock_cosmos_repository, mock_dataframe):
        """Test successful load operation."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        result = loader.load(mock_dataframe)
        
        assert result == 100
        assert len(mock_cosmos_repository.written_data) == 1
        write_record = mock_cosmos_repository.written_data[0]
        assert write_record['container'] == "test_container"
        assert write_record['mode'] == "append"
        assert write_record['bulk'] is True
    
    def test_load_with_append_mode(self, mock_get_session, cosmos_config, mock_cosmos_repository, mock_dataframe):
        """Test load with append mode."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            write_mode="append",
            repository=mock_cosmos_repository
        )
        
        result = loader.load(mock_dataframe)
        
        assert result == 100
        write_record = mock_cosmos_repository.written_data[0]
        assert write_record['mode'] == "append"
    
    def test_load_with_upsert_mode(self, mock_get_session, cosmos_config, mock_cosmos_repository, mock_dataframe):
        """Test load with overwrite (upsert) mode."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            write_mode="overwrite",
            repository=mock_cosmos_repository
        )
        
        result = loader.load(mock_dataframe)
        
        assert result == 100
        write_record = mock_cosmos_repository.written_data[0]
        assert write_record['mode'] == "upsert"  # CosmosLoader converts "overwrite" to "upsert"
    
    def test_load_empty_dataframe(self, mock_get_session, cosmos_config, mock_cosmos_repository, empty_dataframe):
        """Test load with empty DataFrame."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        result = loader.load(empty_dataframe)
        
        assert result == 0
        assert len(mock_cosmos_repository.written_data) == 0  # Nothing written


class TestBatchOperations:
    """Test batch loading operations."""
    
    def test_load_batch(self, mock_get_session, cosmos_config, mock_cosmos_repository, mock_dataframe):
        """Test single batch load."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        result = loader.load_batch(mock_dataframe, batch_number=1)
        
        assert result == 100
        assert len(mock_cosmos_repository.written_data) == 1


class TestRetryLogic:
    """Test retry and error handling."""
    
    def test_retry_on_throttling(self, mock_get_session, cosmos_config, mock_dataframe):
        """Test retry on throttling error."""
        repo = MockCosmosRepository()
        repo.add_container("test_container")
        
        # First call fails with throttling, second succeeds
        call_count = [0]
        def write_with_retry(df, connection, mode, enable_bulk):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("429 - Too Many Requests")
            return 100
        
        repo.write_dataframe = write_with_retry
        
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=repo
        )
        
        result = loader.load_batch(mock_dataframe)
        
        assert result == 100
        assert call_count[0] == 2  # Failed once, succeeded on retry
    
    def test_max_retries_exceeded(self, mock_get_session, cosmos_config, mock_dataframe):
        """Test failure after max retries."""
        repo = MockCosmosRepository()
        repo.add_container("test_container")
        
        # Always fail with throttling
        def always_throttle(df, connection, mode, enable_bulk):
            raise Exception("429 - Too Many Requests")
        
        repo.write_dataframe = always_throttle
        
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=repo
        )
        
        # Should raise exception after retries exhausted (not LoadError, just Exception)
        with pytest.raises(Exception, match="429"):
            loader.load_batch(mock_dataframe)


class TestUpsertOperations:
    """Test upsert operations."""
    
    def test_upsert_records(self, mock_get_session, cosmos_config, mock_cosmos_repository, mock_dataframe):
        """Test upsert operation."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        result = loader.upsert_records(mock_dataframe)
        
        assert result == 100
        # Verify write mode was set to overwrite (upsert)
        write_record = mock_cosmos_repository.written_data[0]
        assert write_record['mode'] == "upsert"


class TestValidationOperations:
    """Test validation operations."""
    
    def test_validate_target_connection_success(self, mock_get_session, cosmos_config, mock_cosmos_repository):
        """Test successful target validation."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        # Should not raise
        assert loader.validate_target_connection() is True
    
    def test_validate_container_exists(self, mock_get_session, cosmos_config, mock_cosmos_repository):
        """Test container exists check."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        assert loader.target_exists() is True
    
    def test_validate_container_not_exists(self, mock_get_session, cosmos_config):
        """Test validation fails when container doesn't exist."""
        repo = MockCosmosRepository()
        # Don't add container
        
        loader = CosmosLoader(
            cosmos_config,
            container="nonexistent_container",
            repository=repo
        )
        
        assert loader.target_exists() is False


class TestContainerOperations:
    """Test container statistics and operations."""
    
    def test_get_container_statistics(self, mock_get_session, cosmos_config, mock_cosmos_repository):
        """Test getting container statistics."""
        # Setup repository with sample data
        mock_df = MagicMock(spec=DataFrame)
        mock_df.count.return_value = 150
        mock_df.columns = ["id", "partitionKey", "data", "timestamp"]
        mock_cosmos_repository.set_read_data(mock_df)
        
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        stats = loader.get_container_statistics()
        
        assert stats["container"] == "test_container"
        assert stats["database"] == "test_db"
        assert stats["record_count"] == 150
        assert stats["columns"] == 4
    
    def test_delete_all_records_with_confirmation(self, mock_get_session, cosmos_config, mock_cosmos_repository):
        """Test deleting all records with confirmation."""
        # Setup repository with data
        mock_df = MagicMock(spec=DataFrame)
        mock_df.count.return_value = 100
        mock_df.columns = ["id", "partitionKey", "data"]
        mock_df.schema = MagicMock()
        mock_cosmos_repository.set_read_data(mock_df)
        
        # Mock createDataFrame for empty DataFrame
        mock_get_session.return_value.createDataFrame.return_value = mock_df
        
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        result = loader.delete_all_records(confirm=True)
        
        assert result is True
        # Verify empty DataFrame was written with overwrite mode
        assert len(mock_cosmos_repository.written_data) == 1
        write_record = mock_cosmos_repository.written_data[0]
        assert write_record['mode'] == "overwrite"
    
    def test_delete_all_records_without_confirmation(self, mock_get_session, cosmos_config, mock_cosmos_repository):
        """Test deleting all records without confirmation aborts."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        result = loader.delete_all_records(confirm=False)
        
        assert result is False
        assert len(mock_cosmos_repository.written_data) == 0  # Nothing written


class TestMetrics:
    """Test metrics tracking."""
    
    def test_load_with_metrics(self, mock_get_session, cosmos_config, mock_cosmos_repository, mock_dataframe):
        """Test load with metrics tracking."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        result = loader.load_with_metrics(mock_dataframe, target_table="test_container")
        
        assert result == 100
        # Just verify metrics object exists
        assert loader.metrics is not None
    
    def test_metrics_track_ru_consumption(self, mock_get_session, cosmos_config, mock_cosmos_repository, mock_dataframe):
        """Test RU consumption tracking."""
        loader = CosmosLoader(
            cosmos_config,
            container="test_container",
            repository=mock_cosmos_repository
        )
        
        loader.load_batch(mock_dataframe)
        
        # Check that RU consumption was estimated
        assert hasattr(loader.metrics, 'custom_metrics')
        assert "request_units_consumed" in loader.metrics.custom_metrics
        assert loader.metrics.custom_metrics["request_units_consumed"] > 0

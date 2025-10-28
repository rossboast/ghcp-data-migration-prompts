"""
Cosmos DB Repository Pattern

This module provides an abstraction layer for Cosmos DB operations,
isolating PySpark-specific implementation details from business logic.

The repository pattern enables:
- Easy mocking in unit tests (no PySpark complexity)
- Testable code without real Cosmos DB connections
- Clear separation of concerns
- Dependency injection for better design

Usage:
    # Production code
    repository = SparkCosmosRepository(spark)
    loader = CosmosLoader(config, repository=repository)
    
    # Test code
    mock_repository = MockCosmosRepository()
    loader = CosmosLoader(config, repository=mock_repository)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pyspark.sql import DataFrame, SparkSession


@dataclass
class CosmosConnection:
    """
    Cosmos DB connection configuration.
    
    Attributes:
        endpoint: Cosmos DB account endpoint URL
        key: Cosmos DB account key
        database: Database name
        container: Container name
        partition_key: Partition key field name
    """
    endpoint: str
    key: str
    database: str
    container: str
    partition_key: str = "partitionKey"


class ICosmosRepository(ABC):
    """
    Abstract interface for Cosmos DB operations.
    
    This interface defines the contract for all Cosmos DB operations,
    allowing different implementations (real PySpark, mock for tests, etc.)
    """
    
    @abstractmethod
    def write_dataframe(
        self,
        df: DataFrame,
        connection: CosmosConnection,
        mode: str = "append",
        enable_bulk: bool = True
    ) -> int:
        """
        Write DataFrame to Cosmos DB container.
        
        Args:
            df: DataFrame to write
            connection: Cosmos DB connection details
            mode: Write mode ('append', 'overwrite', 'upsert')
            enable_bulk: Enable bulk operations for better performance
            
        Returns:
            Number of records written
        """
        pass
    
    @abstractmethod
    def read_container(
        self,
        connection: CosmosConnection,
        query: Optional[str] = None
    ) -> DataFrame:
        """
        Read data from Cosmos DB container.
        
        Args:
            connection: Cosmos DB connection details
            query: Optional SQL query to filter data
            
        Returns:
            DataFrame with container data
        """
        pass
    
    @abstractmethod
    def container_exists(self, connection: CosmosConnection) -> bool:
        """
        Check if container exists in database.
        
        Args:
            connection: Cosmos DB connection details
            
        Returns:
            True if container exists, False otherwise
        """
        pass


class SparkCosmosRepository(ICosmosRepository):
    """
    Real Cosmos DB implementation using PySpark.
    
    This implementation uses the Azure Cosmos DB Spark connector
    to perform actual operations against Cosmos DB.
    """
    
    def __init__(self, spark: SparkSession):
        """
        Initialize repository with Spark session.
        
        Args:
            spark: SparkSession instance
        """
        self.spark = spark
    
    def write_dataframe(
        self,
        df: DataFrame,
        connection: CosmosConnection,
        mode: str = "append",
        enable_bulk: bool = True
    ) -> int:
        """Write DataFrame to Cosmos DB using Spark connector."""
        # Build Cosmos DB options
        cosmos_options = {
            "spark.cosmos.accountEndpoint": connection.endpoint,
            "spark.cosmos.accountKey": connection.key,
            "spark.cosmos.database": connection.database,
            "spark.cosmos.container": connection.container,
            "spark.cosmos.write.strategy": "ItemOverwrite" if mode == "upsert" else "ItemAppend",
            "spark.cosmos.write.bulk.enabled": str(enable_bulk).lower()
        }
        
        # Convert PySpark mode to Cosmos mode
        spark_mode = "append" if mode in ["append", "upsert"] else mode
        
        # Write to Cosmos
        df.write \
            .format("cosmos.oltp") \
            .options(**cosmos_options) \
            .mode(spark_mode) \
            .save()
        
        return df.count()
    
    def read_container(
        self,
        connection: CosmosConnection,
        query: Optional[str] = None
    ) -> DataFrame:
        """Read from Cosmos DB container using Spark connector."""
        cosmos_options = {
            "spark.cosmos.accountEndpoint": connection.endpoint,
            "spark.cosmos.accountKey": connection.key,
            "spark.cosmos.database": connection.database,
            "spark.cosmos.container": connection.container
        }
        
        if query:
            cosmos_options["spark.cosmos.read.customQuery"] = query
        
        return self.spark.read \
            .format("cosmos.oltp") \
            .options(**cosmos_options) \
            .load()
    
    def container_exists(self, connection: CosmosConnection) -> bool:
        """
        Check if container exists by attempting to read metadata.
        
        Note: This is a simplified implementation. In production,
        you might want to use the Cosmos SDK directly.
        """
        try:
            # Try to read with limit 0 to check existence
            self.read_container(connection).limit(0).count()
            return True
        except Exception:
            return False


class MockCosmosRepository(ICosmosRepository):
    """
    Mock Cosmos DB implementation for testing.
    
    This mock allows tests to verify Cosmos DB operations without
    requiring PySpark or a real Cosmos DB account.
    
    Usage:
        mock_repo = MockCosmosRepository()
        mock_repo.set_write_result(100)  # Simulate writing 100 records
        
        loader = CosmosLoader(config, repository=mock_repo)
        count = loader.load(df, "container")
        assert count == 100
    """
    
    def __init__(self):
        """Initialize mock with default values."""
        self.write_count = 0
        self.write_mode = None
        self.write_bulk_enabled = None
        self.written_data = []
        self.containers = set()
        self.read_data = None
    
    def set_write_result(self, count: int):
        """Set the result that write_dataframe will return."""
        self.write_count = count
    
    def set_read_data(self, df: DataFrame):
        """Set the DataFrame that read_container will return."""
        self.read_data = df
    
    def add_container(self, container_name: str):
        """Mark a container as existing."""
        self.containers.add(container_name)
    
    def write_dataframe(
        self,
        df: DataFrame,
        connection: CosmosConnection,
        mode: str = "append",
        enable_bulk: bool = True
    ) -> int:
        """Mock write operation - captures parameters and returns configured count."""
        self.write_mode = mode
        self.write_bulk_enabled = enable_bulk
        self.written_data.append({
            'container': connection.container,
            'mode': mode,
            'bulk': enable_bulk,
            'row_count': df.count() if hasattr(df, 'count') else 0
        })
        self.containers.add(connection.container)
        return self.write_count if self.write_count > 0 else df.count()
    
    def read_container(
        self,
        connection: CosmosConnection,
        query: Optional[str] = None
    ) -> DataFrame:
        """Mock read operation - returns configured DataFrame."""
        if self.read_data is None:
            raise Exception(f"Container {connection.container} not found or no data configured")
        return self.read_data
    
    def container_exists(self, connection: CosmosConnection) -> bool:
        """Mock existence check - returns True if container was added."""
        return connection.container in self.containers


if __name__ == "__main__":
    """Example demonstrating easy testing with MockCosmosRepository."""
    from unittest.mock import MagicMock
    
    # Create mock DataFrame
    mock_df = MagicMock()
    mock_df.count.return_value = 50
    
    # Create mock repository
    mock_repo = MockCosmosRepository()
    mock_repo.set_write_result(50)
    
    # Create connection
    connection = CosmosConnection(
        endpoint="https://test.documents.azure.com:443/",
        key="test_key",
        database="testdb",
        container="employees"
    )
    
    # Test write operation
    count = mock_repo.write_dataframe(mock_df, connection, mode="upsert")
    print(f"✅ Wrote {count} records to {connection.container}")
    
    # Verify write details
    assert mock_repo.write_mode == "upsert"
    assert mock_repo.write_bulk_enabled == True
    assert len(mock_repo.written_data) == 1
    
    # Test container existence
    assert mock_repo.container_exists(connection) == True
    
    print("✅ All mock repository tests passed!")
    print("\nThis is how simple testing becomes with the repository pattern:")
    print("- No PySpark mocking complexity")
    print("- No Cosmos DB account needed")
    print("- Tests run in milliseconds")
    print("- Clear, readable test code")

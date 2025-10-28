"""
JDBC Repository Pattern

Abstracts PySpark JDBC operations to make testing easier.
Provides clean interface for database operations without exposing PySpark internals.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from pyspark.sql import DataFrame, SparkSession
from dataclasses import dataclass


@dataclass
class JdbcConnection:
    """JDBC connection configuration."""
    url: str
    user: str
    password: str
    driver: str
    properties: Optional[Dict[str, str]] = None


class IJdbcRepository(ABC):
    """
    Interface for JDBC operations.
    
    This abstraction allows us to:
    - Mock database operations easily in tests
    - Swap implementations (Spark, Pandas, etc.)
    - Test business logic without PySpark complexity
    """
    
    @abstractmethod
    def read_table(self, table: str, connection: JdbcConnection) -> DataFrame:
        """Read entire table."""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, connection: JdbcConnection) -> DataFrame:
        """Execute custom SQL query."""
        pass
    
    @abstractmethod
    def test_connection(self, connection: JdbcConnection) -> bool:
        """Test if connection is valid."""
        pass


class SparkJdbcRepository(IJdbcRepository):
    """
    Real PySpark implementation of JDBC repository.
    
    Encapsulates all PySpark-specific method chaining and complexity.
    """
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
    
    def read_table(self, table: str, connection: JdbcConnection) -> DataFrame:
        """Read entire table using JDBC."""
        properties = self._build_properties(connection)
        
        return self.spark.read.jdbc(
            url=connection.url,
            table=table,
            properties=properties
        )
    
    def execute_query(self, query: str, connection: JdbcConnection) -> DataFrame:
        """Execute custom query using JDBC."""
        properties = self._build_properties(connection)
        
        # Wrap query in subquery syntax for JDBC
        table_expr = f"({query}) query_result"
        
        return self.spark.read.jdbc(
            url=connection.url,
            table=table_expr,
            properties=properties
        )
    
    def test_connection(self, connection: JdbcConnection) -> bool:
        """Test connection with simple query."""
        try:
            test_query = "SELECT 1 FROM DUAL"
            df = self.execute_query(test_query, connection)
            count = df.count()
            return count == 1
        except Exception:
            return False
    
    def _build_properties(self, connection: JdbcConnection) -> Dict[str, str]:
        """Build JDBC properties dictionary."""
        props = {
            "user": connection.user,
            "password": connection.password,
            "driver": connection.driver,
            "fetchsize": "10000",
            "oracle.jdbc.timezoneAsRegion": "false"
        }
        
        if connection.properties:
            props.update(connection.properties)
        
        return props


class MockJdbcRepository(IJdbcRepository):
    """
    Mock implementation for testing.
    
    No PySpark complexity - just returns predefined DataFrames.
    """
    
    def __init__(self, mock_data: Optional[Dict[str, DataFrame]] = None):
        self.mock_data = mock_data or {}
        self.connection_valid = True
        self.queries_executed = []
    
    def read_table(self, table: str, connection: JdbcConnection) -> DataFrame:
        """Return mock DataFrame for table."""
        self.queries_executed.append(f"READ_TABLE:{table}")
        
        if table not in self.mock_data:
            raise ValueError(f"No mock data for table: {table}")
        
        return self.mock_data[table]
    
    def execute_query(self, query: str, connection: JdbcConnection) -> DataFrame:
        """Return mock DataFrame for query."""
        self.queries_executed.append(f"QUERY:{query}")
        
        # Return first available mock data
        if self.mock_data:
            return list(self.mock_data.values())[0]
        
        raise ValueError("No mock data available")
    
    def test_connection(self, connection: JdbcConnection) -> bool:
        """Return mock connection status."""
        return self.connection_valid

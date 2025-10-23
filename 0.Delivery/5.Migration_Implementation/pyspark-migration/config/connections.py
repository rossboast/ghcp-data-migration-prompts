"""
Connection Configuration

This module manages connection strings and credentials for Oracle and Azure Cosmos DB.

Security Note:
- Never hardcode credentials in this file
- Use environment variables or Azure Key Vault for sensitive data
- For production, integrate with Azure Key Vault or similar secret management
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass

from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class OracleConnectionConfig:
    """
    Oracle database connection configuration.
    
    Attributes:
        host: Database host (e.g., 'localhost' or IP address)
        port: Database port (default: 1521)
        service_name: Oracle service name (e.g., 'XEPDB1')
        username: Database username
        password: Database password
        schema: Database schema to query (default: 'HR')
    """
    host: str
    port: int
    service_name: str
    username: str
    password: str
    schema: str = "HR"
    
    @property
    def jdbc_url(self) -> str:
        """
        Generate JDBC URL for Oracle connection.
        
        Returns:
            JDBC connection string
        """
        return f"jdbc:oracle:thin:@//{self.host}:{self.port}/{self.service_name}"
    
    @property
    def connection_properties(self) -> Dict[str, str]:
        """
        Get connection properties for Spark JDBC.
        
        Returns:
            Dictionary of connection properties
        """
        return {
            "user": self.username,
            "password": self.password,
            "driver": "oracle.jdbc.driver.OracleDriver",
        }
    
    def __repr__(self) -> str:
        """String representation (masks password)."""
        return (
            f"OracleConnectionConfig(host={self.host}, port={self.port}, "
            f"service_name={self.service_name}, username={self.username}, "
            f"password=*****, schema={self.schema})"
        )


@dataclass
class CosmosDBConnectionConfig:
    """
    Azure Cosmos DB connection configuration.
    
    Attributes:
        endpoint: Cosmos DB account endpoint URL
        key: Cosmos DB account key (primary or secondary)
        database_name: Database name
        preferred_regions: Comma-separated list of preferred regions (optional)
    """
    endpoint: str
    key: str
    database_name: str
    preferred_regions: Optional[str] = None
    
    @property
    def connection_properties(self) -> Dict[str, str]:
        """
        Get connection properties for Cosmos DB Spark connector.
        
        Returns:
            Dictionary of connection properties
        """
        props = {
            "spark.cosmos.accountEndpoint": self.endpoint,
            "spark.cosmos.accountKey": self.key,
            "spark.cosmos.database": self.database_name,
        }
        
        if self.preferred_regions:
            props["spark.cosmos.preferredRegions"] = self.preferred_regions
        
        return props
    
    def __repr__(self) -> str:
        """String representation (masks key)."""
        return (
            f"CosmosDBConnectionConfig(endpoint={self.endpoint}, "
            f"key=*****, database_name={self.database_name}, "
            f"preferred_regions={self.preferred_regions})"
        )


class ConnectionManager:
    """
    Manages database connections and provides configuration objects.
    
    This class reads connection details from environment variables
    and provides validated configuration objects.
    """
    
    @staticmethod
    def get_oracle_config() -> OracleConnectionConfig:
        """
        Get Oracle connection configuration from environment variables.
        
        Required environment variables:
            ORACLE_HOST: Database host
            ORACLE_PORT: Database port
            ORACLE_SERVICE_NAME: Service name
            ORACLE_USERNAME: Username
            ORACLE_PASSWORD: Password
            ORACLE_SCHEMA: Schema name (optional, defaults to 'HR')
        
        Returns:
            OracleConnectionConfig instance
            
        Raises:
            ValueError: If required environment variables are missing
        """
        required_vars = [
            "ORACLE_HOST",
            "ORACLE_PORT",
            "ORACLE_SERVICE_NAME",
            "ORACLE_USERNAME",
            "ORACLE_PASSWORD"
        ]
        
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            raise ValueError(
                f"Missing required Oracle environment variables: {', '.join(missing_vars)}"
            )
        
        config = OracleConnectionConfig(
            host=os.environ["ORACLE_HOST"],
            port=int(os.environ["ORACLE_PORT"]),
            service_name=os.environ["ORACLE_SERVICE_NAME"],
            username=os.environ["ORACLE_USERNAME"],
            password=os.environ["ORACLE_PASSWORD"],
            schema=os.environ.get("ORACLE_SCHEMA", "HR")
        )
        
        logger.info(
            "Oracle connection configuration loaded",
            host=config.host,
            port=config.port,
            service_name=config.service_name,
            schema=config.schema
        )
        
        return config
    
    @staticmethod
    def get_cosmos_config() -> CosmosDBConnectionConfig:
        """
        Get Cosmos DB connection configuration from environment variables.
        
        Required environment variables:
            COSMOS_ENDPOINT: Cosmos DB account endpoint
            COSMOS_KEY: Cosmos DB account key
            COSMOS_DATABASE: Database name
            COSMOS_REGIONS: Preferred regions (optional)
        
        Returns:
            CosmosDBConnectionConfig instance
            
        Raises:
            ValueError: If required environment variables are missing
        """
        required_vars = [
            "COSMOS_ENDPOINT",
            "COSMOS_KEY",
            "COSMOS_DATABASE"
        ]
        
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        if missing_vars:
            raise ValueError(
                f"Missing required Cosmos DB environment variables: {', '.join(missing_vars)}"
            )
        
        config = CosmosDBConnectionConfig(
            endpoint=os.environ["COSMOS_ENDPOINT"],
            key=os.environ["COSMOS_KEY"],
            database_name=os.environ["COSMOS_DATABASE"],
            preferred_regions=os.environ.get("COSMOS_REGIONS")
        )
        
        logger.info(
            "Cosmos DB connection configuration loaded",
            endpoint=config.endpoint,
            database_name=config.database_name,
            preferred_regions=config.preferred_regions
        )
        
        return config
    
    @staticmethod
    def validate_oracle_connection(config: OracleConnectionConfig) -> bool:
        """
        Validate Oracle connection (requires cx_Oracle or JDBC driver).
        
        Args:
            config: Oracle connection configuration
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            from pyspark.sql import SparkSession
            from utils.spark_session import get_spark_session
            
            spark = get_spark_session()
            
            # Try a simple query
            query = "(SELECT 1 as test FROM DUAL) test_query"
            df = spark.read \
                .format("jdbc") \
                .option("url", config.jdbc_url) \
                .option("dbtable", query) \
                .options(**config.connection_properties) \
                .load()
            
            result = df.collect()
            
            logger.info("Oracle connection validated successfully")
            return len(result) > 0
            
        except Exception as e:
            logger.error("Oracle connection validation failed", error=str(e))
            return False
    
    @staticmethod
    def validate_cosmos_connection(config: CosmosDBConnectionConfig) -> bool:
        """
        Validate Cosmos DB connection.
        
        Args:
            config: Cosmos DB connection configuration
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            from azure.cosmos import CosmosClient
            
            client = CosmosClient(config.endpoint, config.key)
            database = client.get_database_client(config.database_name)
            
            # Try to read database properties
            _ = database.read()
            
            logger.info("Cosmos DB connection validated successfully")
            return True
            
        except Exception as e:
            logger.error("Cosmos DB connection validation failed", error=str(e))
            return False


# Container names for Cosmos DB
class CosmosContainers:
    """Constants for Cosmos DB container names."""
    EMPLOYEES = "employees"
    REFERENCE_DATA = "reference_data"
    AUDIT_LOG = "audit_log"


# Example usage and configuration templates
def get_example_env_file() -> str:
    """
    Generate example .env file content.
    
    Returns:
        Example environment variable configuration
    """
    return """# Oracle Database Configuration
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=XEPDB1
ORACLE_USERNAME=hr
ORACLE_PASSWORD=your_password_here
ORACLE_SCHEMA=HR

# Azure Cosmos DB Configuration
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your_cosmos_key_here
COSMOS_DATABASE=migration_db
COSMOS_REGIONS=East US,West US

# Optional: Spark Configuration
SPARK_MASTER=local[*]
"""


if __name__ == "__main__":
    # Example: Print template .env file
    print("Example .env file configuration:")
    print(get_example_env_file())
    
    # Example: Load and display configurations (if env vars are set)
    try:
        oracle_config = ConnectionManager.get_oracle_config()
        print(f"\nOracle Config: {oracle_config}")
        print(f"JDBC URL: {oracle_config.jdbc_url}")
    except ValueError as e:
        print(f"\nCannot load Oracle config: {e}")
    
    try:
        cosmos_config = ConnectionManager.get_cosmos_config()
        print(f"\nCosmos DB Config: {cosmos_config}")
    except ValueError as e:
        print(f"\nCannot load Cosmos DB config: {e}")

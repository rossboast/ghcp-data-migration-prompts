"""
Spark Session Management

This module provides a singleton factory for creating and managing PySpark sessions
configured for Oracle JDBC and Azure Cosmos DB connectivity.

Features:
- Singleton pattern to ensure one Spark session per application
- Oracle JDBC driver configuration
- Azure Cosmos DB Spark connector configuration
- Performance tuning for migration workloads
- Graceful shutdown handling
"""

import os
import atexit
from typing import Optional, Dict, Any
from pyspark.sql import SparkSession
from pyspark import SparkConf

from utils.logging_config import get_logger

logger = get_logger(__name__)


class SparkSessionFactory:
    """
    Singleton factory for creating and managing Spark sessions.
    
    This factory ensures that only one Spark session exists per application
    and provides proper configuration for Oracle and CosmosDB connectivity.
    """
    
    _instance: Optional[SparkSession] = None
    _initialized: bool = False
    
    @classmethod
    def get_session(
        cls,
        app_name: str = "OracleToCosmosDBMigration",
        master: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None
    ) -> SparkSession:
        """
        Get or create a Spark session with migration-specific configuration.
        
        Args:
            app_name: Name of the Spark application
            master: Spark master URL (e.g., 'local[*]', 'yarn', 'spark://...')
                   If None, uses environment variable SPARK_MASTER or defaults to 'local[*]'
            config_overrides: Dictionary of additional Spark configurations to override defaults
            
        Returns:
            Configured SparkSession instance
            
        Example:
            >>> spark = SparkSessionFactory.get_session(
            ...     app_name="MyMigration",
            ...     config_overrides={"spark.executor.memory": "8g"}
            ... )
        """
        if cls._instance is None:
            logger.info("Creating new Spark session", app_name=app_name)
            cls._instance = cls._create_session(app_name, master, config_overrides)
            cls._initialized = True
            
            # Register shutdown hook
            atexit.register(cls.stop_session)
            
            logger.info(
                "Spark session created successfully",
                spark_version=cls._instance.version,
                app_id=cls._instance.sparkContext.applicationId
            )
        else:
            logger.debug("Returning existing Spark session")
            
        return cls._instance
    
    @classmethod
    def _create_session(
        cls,
        app_name: str,
        master: Optional[str],
        config_overrides: Optional[Dict[str, Any]]
    ) -> SparkSession:
        """
        Internal method to create and configure a new Spark session.
        
        Args:
            app_name: Name of the Spark application
            master: Spark master URL
            config_overrides: Additional configurations
            
        Returns:
            Configured SparkSession
        """
        # Determine master URL
        if master is None:
            master = os.environ.get("SPARK_MASTER", "local[*]")
        
        # Base configuration optimized for migration workloads
        config = SparkConf()
        config.setAppName(app_name)
        config.setMaster(master)
        
        # Default configurations
        default_config = cls._get_default_config()
        for key, value in default_config.items():
            config.set(key, value)
        
        # Apply overrides
        if config_overrides:
            for key, value in config_overrides.items():
                config.set(key, str(value))
                logger.debug("Config override applied", key=key, value=value)
        
        # Create session
        builder = SparkSession.builder.config(conf=config)
        
        # Enable Hive support if available (useful for some operations)
        try:
            spark = builder.enableHiveSupport().getOrCreate()
        except Exception as e:
            logger.warning("Hive support not available, continuing without it", error=str(e))
            spark = builder.getOrCreate()
        
        # Set log level to reduce noise
        spark.sparkContext.setLogLevel("WARN")
        
        return spark
    
    @classmethod
    def _get_default_config(cls) -> Dict[str, str]:
        """
        Get default Spark configuration optimized for migration workloads.
        
        Returns:
            Dictionary of Spark configuration key-value pairs
        """
        return {
            # Memory settings
            "spark.driver.memory": "2g",
            "spark.executor.memory": "4g",
            "spark.memory.fraction": "0.8",
            "spark.memory.storageFraction": "0.3",
            
            # Shuffle settings
            "spark.sql.shuffle.partitions": "200",
            "spark.default.parallelism": "100",
            
            # Oracle JDBC settings
            "spark.jars.packages": "com.oracle.database.jdbc:ojdbc8:21.7.0.0,"
                                  "com.azure.cosmos.spark:azure-cosmos-spark_3-2_2-12:4.22.0",
            
            # Serialization
            "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
            "spark.kryoserializer.buffer.max": "512m",
            
            # SQL settings
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true",
            
            # Network timeout settings
            "spark.network.timeout": "300s",
            "spark.executor.heartbeatInterval": "60s",
            
            # Dynamic allocation (if supported by cluster)
            "spark.dynamicAllocation.enabled": "false",
            
            # Cosmos DB specific settings
            "spark.cosmos.accountEndpoint": os.environ.get("COSMOS_ENDPOINT", ""),
            "spark.cosmos.accountKey": os.environ.get("COSMOS_KEY", ""),
            "spark.cosmos.database": os.environ.get("COSMOS_DATABASE", ""),
            "spark.cosmos.preferredRegions": os.environ.get("COSMOS_REGIONS", ""),
        }
    
    @classmethod
    def stop_session(cls) -> None:
        """
        Stop the Spark session and clean up resources.
        
        This is automatically called on application exit via atexit,
        but can also be called manually if needed.
        """
        if cls._instance is not None:
            logger.info("Stopping Spark session")
            try:
                cls._instance.stop()
                logger.info("Spark session stopped successfully")
            except Exception as e:
                logger.error("Error stopping Spark session", error=str(e))
            finally:
                cls._instance = None
                cls._initialized = False
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        Check if a Spark session has been initialized.
        
        Returns:
            True if session exists, False otherwise
        """
        return cls._initialized


def get_spark_session(
    app_name: str = "OracleToCosmosDBMigration",
    **kwargs
) -> SparkSession:
    """
    Convenience function to get a Spark session.
    
    This is a wrapper around SparkSessionFactory.get_session() for easier imports.
    
    Args:
        app_name: Name of the Spark application
        **kwargs: Additional arguments passed to SparkSessionFactory.get_session()
        
    Returns:
        Configured SparkSession instance
        
    Example:
        >>> from utils.spark_session import get_spark_session
        >>> spark = get_spark_session()
    """
    return SparkSessionFactory.get_session(app_name=app_name, **kwargs)


def configure_oracle_jdbc(
    spark: SparkSession,
    jdbc_url: str,
    driver: str = "oracle.jdbc.driver.OracleDriver"
) -> Dict[str, str]:
    """
    Get JDBC configuration for Oracle database connections.
    
    Args:
        spark: SparkSession instance
        jdbc_url: JDBC URL for Oracle database
        driver: JDBC driver class name
        
    Returns:
        Dictionary of JDBC configuration options
        
    Example:
        >>> spark = get_spark_session()
        >>> jdbc_config = configure_oracle_jdbc(
        ...     spark,
        ...     "jdbc:oracle:thin:@//localhost:1521/XEPDB1"
        ... )
        >>> df = spark.read.format("jdbc").options(**jdbc_config).load()
    """
    return {
        "url": jdbc_url,
        "driver": driver,
        "fetchsize": "10000",  # Number of rows to fetch per round trip
        "numPartitions": "4",  # Number of parallel connections
        "sessionInitStatement": "ALTER SESSION SET NLS_DATE_FORMAT='YYYY-MM-DD HH24:MI:SS'",
    }


def configure_cosmos_write(
    container: str,
    write_strategy: str = "ItemOverwrite"
) -> Dict[str, str]:
    """
    Get write configuration for Cosmos DB.
    
    Args:
        container: Cosmos DB container name
        write_strategy: Write strategy (ItemOverwrite, ItemAppend, ItemDelete, ItemDeleteIfNotModified)
        
    Returns:
        Dictionary of Cosmos DB write configuration options
        
    Example:
        >>> cosmos_config = configure_cosmos_write("employees")
        >>> df.write.format("cosmos.oltp").options(**cosmos_config).mode("append").save()
    """
    return {
        "spark.cosmos.container": container,
        "spark.cosmos.write.strategy": write_strategy,
        "spark.cosmos.write.bulk.enabled": "true",
        "spark.cosmos.write.maxRetryCount": "3",
        "spark.cosmos.write.point.maxConcurrency": "100",
    }


def configure_cosmos_read(
    container: str,
    read_strategy: str = "FullFidelity"
) -> Dict[str, str]:
    """
    Get read configuration for Cosmos DB.
    
    Args:
        container: Cosmos DB container name
        read_strategy: Read strategy (FullFidelity or Incremental)
        
    Returns:
        Dictionary of Cosmos DB read configuration options
        
    Example:
        >>> cosmos_config = configure_cosmos_read("employees")
        >>> df = spark.read.format("cosmos.oltp").options(**cosmos_config).load()
    """
    return {
        "spark.cosmos.container": container,
        "spark.cosmos.read.inferSchema.enabled": "true",
        "spark.cosmos.read.partitioning.strategy": read_strategy,
    }


# Example usage and testing
if __name__ == "__main__":
    # This block can be used for testing the module
    print("Testing Spark Session Factory...")
    
    # Get a session
    spark = get_spark_session(app_name="TestApp")
    print(f"Spark version: {spark.version}")
    print(f"Application ID: {spark.sparkContext.applicationId}")
    
    # Test Oracle JDBC configuration
    oracle_config = configure_oracle_jdbc(
        spark,
        "jdbc:oracle:thin:@//localhost:1521/XEPDB1"
    )
    print(f"Oracle JDBC config: {oracle_config}")
    
    # Test Cosmos DB write configuration
    cosmos_write_config = configure_cosmos_write("test_container")
    print(f"Cosmos write config: {cosmos_write_config}")
    
    # Clean up
    SparkSessionFactory.stop_session()
    print("Session stopped successfully")

"""
Utils Module

This module provides common utilities for the migration framework:
- Logging configuration
- Error handling
- Spark session management
- Metrics collection
"""

from utils.logging_config import (
    configure_logging,
    get_logger,
    MigrationLogger,
)

from utils.error_handler import (
    MigrationError,
    ExtractionError,
    TransformationError,
    ValidationError,
    LoadError,
    ConnectionError as MigrationConnectionError,
    ConfigurationError,
    retry,
    ErrorContext,
    ErrorCollector,
)

from utils.spark_session import (
    SparkSessionFactory,
    get_spark_session,
    configure_oracle_jdbc,
    configure_cosmos_write,
    configure_cosmos_read,
)

from utils.metrics import (
    MetricType,
    MetricValue,
    MigrationMetrics,
    MetricsCollector,
    Timer,
)

__all__ = [
    # Logging
    "configure_logging",
    "get_logger",
    "MigrationLogger",
    
    # Error handling
    "MigrationError",
    "ExtractionError",
    "TransformationError",
    "ValidationError",
    "LoadError",
    "MigrationConnectionError",
    "ConfigurationError",
    "retry",
    "ErrorContext",
    "ErrorCollector",
    
    # Spark session
    "SparkSessionFactory",
    "get_spark_session",
    "configure_oracle_jdbc",
    "configure_cosmos_write",
    "configure_cosmos_read",
    
    # Metrics
    "MetricType",
    "MetricValue",
    "MigrationMetrics",
    "MetricsCollector",
    "Timer",
]

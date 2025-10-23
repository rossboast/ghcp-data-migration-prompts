"""
Logging configuration for Oracle HR to CosmosDB migration.
Provides structured logging with context information.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import structlog

# Create logs directory if it doesn't exist
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Log file path with timestamp
LOG_FILE = LOG_DIR / f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


def configure_logging(log_level: str = "INFO", log_to_file: bool = True) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file in addition to console
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer() if not log_to_file else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    
    # Configure standard logging
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_to_file:
        file_handler = logging.FileHandler(LOG_FILE, mode='a')
        file_handler.setLevel(numeric_level)
        handlers.append(file_handler)
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def get_logger(name: str, **context) -> structlog.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Name of the logger (typically __name__ or class name)
        **context: Additional context to bind to all log messages
        
    Returns:
        Configured structlog logger instance
    """
    logger = structlog.get_logger(name)
    
    # Bind context if provided
    if context:
        logger = logger.bind(**context)
    
    return logger


class MigrationLogger:
    """
    Enhanced logger specifically for migration operations.
    Provides convenience methods for common migration logging patterns.
    """
    
    def __init__(self, component_name: str, feed_name: Optional[str] = None):
        """
        Initialize migration logger.
        
        Args:
            component_name: Name of the component (e.g., 'OracleExtractor', 'CosmosLoader')
            feed_name: Optional name of the data feed being processed
        """
        self.component_name = component_name
        self.feed_name = feed_name
        
        context = {"component": component_name}
        if feed_name:
            context["feed"] = feed_name
            
        self.logger = get_logger(component_name, **context)
    
    def log_start(self, operation: str, **details):
        """Log the start of an operation."""
        self.logger.info(f"Starting {operation}", operation=operation, status="started", **details)
    
    def log_progress(self, operation: str, processed: int, total: int, **details):
        """Log progress of an operation."""
        percentage = (processed / total * 100) if total > 0 else 0
        self.logger.info(
            f"{operation}: {processed}/{total} ({percentage:.1f}%)",
            operation=operation,
            status="in_progress",
            processed=processed,
            total=total,
            percentage=percentage,
            **details
        )
    
    def log_success(self, operation: str, **details):
        """Log successful completion of an operation."""
        self.logger.info(f"Completed {operation}", operation=operation, status="success", **details)
    
    def log_failure(self, operation: str, error: Exception, **details):
        """Log failure of an operation."""
        self.logger.error(
            f"Failed {operation}: {str(error)}",
            operation=operation,
            status="failed",
            error=str(error),
            error_type=type(error).__name__,
            **details,
            exc_info=True
        )
    
    def log_validation(self, check_name: str, passed: bool, **details):
        """Log validation check result."""
        if passed:
            self.logger.info(f"Validation passed: {check_name}", validation=check_name, passed=True, **details)
        else:
            self.logger.warning(f"Validation failed: {check_name}", validation=check_name, passed=False, **details)
    
    def log_metric(self, metric_name: str, value: float, **details):
        """Log a metric value."""
        self.logger.info(f"Metric: {metric_name} = {value}", metric=metric_name, value=value, **details)


# Initialize logging on module import
configure_logging()

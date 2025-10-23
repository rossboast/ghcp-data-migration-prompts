"""
Error handling utilities for the migration framework.
Provides custom exceptions, retry logic, and error tracking.
"""

import time
import functools
from typing import Callable, Type, Tuple, Optional, Any
from utils.logging_config import get_logger

logger = get_logger(__name__)


# Custom Exceptions

class MigrationError(Exception):
    """Base exception for all migration-related errors."""
    pass


class ExtractionError(MigrationError):
    """Error during data extraction phase."""
    pass


class TransformationError(MigrationError):
    """Error during data transformation phase."""
    pass


class ValidationError(MigrationError):
    """Error during data validation phase."""
    pass


class LoadError(MigrationError):
    """Error during data loading phase."""
    pass


class ConnectionError(MigrationError):
    """Error establishing connection to source or target."""
    pass


class ConfigurationError(MigrationError):
    """Error in configuration or setup."""
    pass


# Retry Decorator

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator to retry a function on failure.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
        
    Example:
        @retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(ConnectionError,))
        def load_to_cosmos(data):
            # ... loading logic
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            function=func.__name__,
                            attempts=max_attempts,
                            error=str(e)
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}, retrying in {current_delay}s",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=current_delay,
                        error=str(e)
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # Should never reach here
            raise last_exception
        
        return wrapper
    return decorator


# Error Context Manager

class ErrorContext:
    """
    Context manager for tracking errors and providing detailed error information.
    
    Example:
        with ErrorContext("employee_transformation", record_id=emp_id):
            # ... transformation logic
            pass
    """
    
    def __init__(self, operation: str, **context):
        """
        Initialize error context.
        
        Args:
            operation: Description of the operation
            **context: Additional context information
        """
        self.operation = operation
        self.context = context
        self.logger = get_logger(__name__)
    
    def __enter__(self):
        """Enter the context."""
        self.logger.debug(f"Starting {self.operation}", **self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context, logging any errors."""
        if exc_type is not None:
            self.logger.error(
                f"Error in {self.operation}: {exc_val}",
                operation=self.operation,
                error_type=exc_type.__name__,
                error=str(exc_val),
                **self.context,
                exc_info=True
            )
        else:
            self.logger.debug(f"Completed {self.operation}", **self.context)
        
        # Don't suppress the exception
        return False


# Error Collection

class ErrorCollector:
    """
    Collects errors during batch processing without failing immediately.
    Useful for validation and data quality checks.
    """
    
    def __init__(self, max_errors: Optional[int] = None):
        """
        Initialize error collector.
        
        Args:
            max_errors: Maximum number of errors to collect before raising exception
        """
        self.errors = []
        self.max_errors = max_errors
        self.logger = get_logger(__name__)
    
    def add_error(self, error_type: str, message: str, **context):
        """
        Add an error to the collection.
        
        Args:
            error_type: Type/category of error
            message: Error message
            **context: Additional context about the error
        """
        error_info = {
            "error_type": error_type,
            "message": message,
            "timestamp": time.time(),
            **context
        }
        self.errors.append(error_info)
        
        self.logger.warning(
            f"Error collected: {error_type} - {message}",
            **error_info
        )
        
        if self.max_errors and len(self.errors) >= self.max_errors:
            raise ValidationError(f"Maximum error threshold reached: {self.max_errors} errors collected")
    
    def has_errors(self) -> bool:
        """Check if any errors have been collected."""
        return len(self.errors) > 0
    
    def error_count(self) -> int:
        """Get the number of errors collected."""
        return len(self.errors)
    
    def get_errors(self) -> list:
        """Get all collected errors."""
        return self.errors.copy()
    
    def get_error_summary(self) -> dict:
        """Get a summary of errors by type."""
        summary = {}
        for error in self.errors:
            error_type = error["error_type"]
            summary[error_type] = summary.get(error_type, 0) + 1
        return summary
    
    def raise_if_errors(self):
        """Raise an exception if any errors have been collected."""
        if self.has_errors():
            summary = self.get_error_summary()
            raise ValidationError(
                f"Validation failed with {self.error_count()} errors: {summary}"
            )


# Safe Division

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: The numerator
        denominator: The denominator
        default: Default value to return if denominator is zero
        
    Returns:
        Result of division or default value
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ValueError):
        return default


# Safe Get with Logging

def safe_get(dictionary: dict, key: str, default: Any = None, log_missing: bool = False) -> Any:
    """
    Safely get a value from a dictionary with optional logging.
    
    Args:
        dictionary: The dictionary to get value from
        key: The key to retrieve
        default: Default value if key not found
        log_missing: Whether to log missing keys
        
    Returns:
        Value from dictionary or default
    """
    if key not in dictionary:
        if log_missing:
            logger.debug(f"Key '{key}' not found in dictionary, using default: {default}")
        return default
    return dictionary[key]

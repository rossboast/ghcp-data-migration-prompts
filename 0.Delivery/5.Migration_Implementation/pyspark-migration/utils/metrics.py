"""
Migration Metrics Collection and Reporting

This module provides functionality for collecting, tracking, and reporting
metrics during the migration process.

Features:
- Track records processed, failed, skipped
- Monitor execution time
- Track Azure Cosmos DB RU consumption
- Generate summary reports
- Export metrics for monitoring systems
"""

import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum

from utils.logging_config import get_logger

logger = get_logger(__name__)


class MetricType(Enum):
    """Types of metrics that can be tracked."""
    COUNTER = "counter"  # Incrementing count (e.g., records processed)
    GAUGE = "gauge"      # Point-in-time value (e.g., current memory usage)
    TIMER = "timer"      # Duration measurement
    DISTRIBUTION = "distribution"  # Statistical distribution


@dataclass
class MetricValue:
    """
    Represents a single metric value with metadata.
    """
    name: str
    value: float
    metric_type: MetricType
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags
        }


@dataclass
class MigrationMetrics:
    """
    Container for all migration metrics.
    
    This class tracks various metrics throughout the migration process
    including record counts, timing, and resource utilization.
    """
    feed_name: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # Record counts
    records_extracted: int = 0
    records_transformed: int = 0
    records_validated: int = 0
    records_loaded: int = 0
    records_failed: int = 0
    records_skipped: int = 0
    
    # Cosmos DB metrics
    ru_consumed: float = 0.0
    documents_created: int = 0
    documents_updated: int = 0
    
    # Error tracking
    extraction_errors: int = 0
    transformation_errors: int = 0
    validation_errors: int = 0
    load_errors: int = 0
    
    # Performance metrics
    extraction_duration_seconds: float = 0.0
    transformation_duration_seconds: float = 0.0
    validation_duration_seconds: float = 0.0
    load_duration_seconds: float = 0.0
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def mark_complete(self) -> None:
        """Mark the migration as complete and record end time."""
        self.end_time = datetime.now()
        logger.info(
            "Migration metrics finalized",
            feed_name=self.feed_name,
            duration_seconds=self.total_duration_seconds
        )
    
    @property
    def total_duration_seconds(self) -> float:
        """Calculate total migration duration in seconds."""
        if self.end_time is None:
            return (datetime.now() - self.start_time).total_seconds()
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total = self.records_loaded + self.records_failed
        if total == 0:
            return 0.0
        return (self.records_loaded / total) * 100.0
    
    @property
    def records_per_second(self) -> float:
        """Calculate processing throughput."""
        duration = self.total_duration_seconds
        if duration == 0:
            return 0.0
        return self.records_loaded / duration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary representation."""
        return {
            "feed_name": self.feed_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.total_duration_seconds,
            "records": {
                "extracted": self.records_extracted,
                "transformed": self.records_transformed,
                "validated": self.records_validated,
                "loaded": self.records_loaded,
                "failed": self.records_failed,
                "skipped": self.records_skipped,
            },
            "cosmos_db": {
                "ru_consumed": self.ru_consumed,
                "documents_created": self.documents_created,
                "documents_updated": self.documents_updated,
            },
            "errors": {
                "extraction": self.extraction_errors,
                "transformation": self.transformation_errors,
                "validation": self.validation_errors,
                "load": self.load_errors,
                "total": self.total_errors,
            },
            "performance": {
                "extraction_duration_seconds": self.extraction_duration_seconds,
                "transformation_duration_seconds": self.transformation_duration_seconds,
                "validation_duration_seconds": self.validation_duration_seconds,
                "load_duration_seconds": self.load_duration_seconds,
                "total_duration_seconds": self.total_duration_seconds,
                "records_per_second": self.records_per_second,
                "success_rate_percent": self.success_rate,
            },
            "metadata": self.metadata,
        }
    
    @property
    def total_errors(self) -> int:
        """Calculate total error count across all phases."""
        return (
            self.extraction_errors +
            self.transformation_errors +
            self.validation_errors +
            self.load_errors
        )
    
    def generate_summary(self) -> str:
        """
        Generate a human-readable summary of the migration metrics.
        
        Returns:
            Formatted summary string
        """
        lines = [
            f"\n{'='*60}",
            f"Migration Summary: {self.feed_name}",
            f"{'='*60}",
            f"Duration: {timedelta(seconds=int(self.total_duration_seconds))}",
            f"",
            f"Record Counts:",
            f"  Extracted:    {self.records_extracted:>10,}",
            f"  Transformed:  {self.records_transformed:>10,}",
            f"  Validated:    {self.records_validated:>10,}",
            f"  Loaded:       {self.records_loaded:>10,}",
            f"  Failed:       {self.records_failed:>10,}",
            f"  Skipped:      {self.records_skipped:>10,}",
            f"",
            f"Performance:",
            f"  Success Rate: {self.success_rate:>9.2f}%",
            f"  Throughput:   {self.records_per_second:>9.2f} records/sec",
            f"",
            f"Phase Durations:",
            f"  Extraction:     {self.extraction_duration_seconds:>8.2f}s",
            f"  Transformation: {self.transformation_duration_seconds:>8.2f}s",
            f"  Validation:     {self.validation_duration_seconds:>8.2f}s",
            f"  Load:           {self.load_duration_seconds:>8.2f}s",
            f"",
        ]
        
        if self.ru_consumed > 0:
            lines.extend([
                f"Cosmos DB:",
                f"  RU Consumed:      {self.ru_consumed:>10,.2f}",
                f"  Docs Created:     {self.documents_created:>10,}",
                f"  Docs Updated:     {self.documents_updated:>10,}",
                f"",
            ])
        
        if self.total_errors > 0:
            lines.extend([
                f"Errors:",
                f"  Extraction:       {self.extraction_errors:>10,}",
                f"  Transformation:   {self.transformation_errors:>10,}",
                f"  Validation:       {self.validation_errors:>10,}",
                f"  Load:             {self.load_errors:>10,}",
                f"  Total:            {self.total_errors:>10,}",
                f"",
            ])
        
        lines.append(f"{'='*60}\n")
        
        return "\n".join(lines)


class MetricsCollector:
    """
    Collects and aggregates metrics from multiple migration feeds.
    
    This class can be used to track metrics across multiple migration runs
    and generate aggregate reports.
    """
    
    def __init__(self):
        self.metrics: Dict[str, MigrationMetrics] = {}
        self.custom_metrics: List[MetricValue] = []
        
    def register_feed(self, feed_name: str) -> MigrationMetrics:
        """
        Register a new feed and create metrics tracker for it.
        
        Args:
            feed_name: Name of the data feed
            
        Returns:
            MigrationMetrics instance for the feed
        """
        if feed_name in self.metrics:
            logger.warning("Feed already registered, returning existing metrics", feed_name=feed_name)
            return self.metrics[feed_name]
        
        metrics = MigrationMetrics(feed_name=feed_name)
        self.metrics[feed_name] = metrics
        logger.info("Feed registered for metrics tracking", feed_name=feed_name)
        return metrics
    
    def get_feed_metrics(self, feed_name: str) -> Optional[MigrationMetrics]:
        """Get metrics for a specific feed."""
        return self.metrics.get(feed_name)
    
    def record_custom_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a custom metric.
        
        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            unit: Unit of measurement
            tags: Additional metadata tags
        """
        metric = MetricValue(
            name=name,
            value=value,
            metric_type=metric_type,
            unit=unit,
            tags=tags or {}
        )
        self.custom_metrics.append(metric)
        logger.debug("Custom metric recorded", name=name, value=value, unit=unit)
    
    def get_aggregate_metrics(self) -> Dict[str, Any]:
        """
        Calculate aggregate metrics across all feeds.
        
        Returns:
            Dictionary containing aggregate statistics
        """
        total_records_loaded = sum(m.records_loaded for m in self.metrics.values())
        total_records_failed = sum(m.records_failed for m in self.metrics.values())
        total_ru_consumed = sum(m.ru_consumed for m in self.metrics.values())
        total_duration = sum(m.total_duration_seconds for m in self.metrics.values())
        
        return {
            "total_feeds": len(self.metrics),
            "total_records_loaded": total_records_loaded,
            "total_records_failed": total_records_failed,
            "total_ru_consumed": total_ru_consumed,
            "total_duration_seconds": total_duration,
            "overall_success_rate": (
                (total_records_loaded / (total_records_loaded + total_records_failed) * 100)
                if (total_records_loaded + total_records_failed) > 0 else 0.0
            ),
            "feeds": {
                name: metrics.to_dict()
                for name, metrics in self.metrics.items()
            }
        }
    
    def generate_aggregate_summary(self) -> str:
        """
        Generate aggregate summary across all feeds.
        
        Returns:
            Formatted summary string
        """
        aggregate = self.get_aggregate_metrics()
        
        lines = [
            f"\n{'='*60}",
            f"Aggregate Migration Summary",
            f"{'='*60}",
            f"Total Feeds:      {aggregate['total_feeds']:>10}",
            f"Records Loaded:   {aggregate['total_records_loaded']:>10,}",
            f"Records Failed:   {aggregate['total_records_failed']:>10,}",
            f"Success Rate:     {aggregate['overall_success_rate']:>9.2f}%",
            f"RU Consumed:      {aggregate['total_ru_consumed']:>10,.2f}",
            f"Total Duration:   {timedelta(seconds=int(aggregate['total_duration_seconds']))}",
            f"",
            f"Per-Feed Summary:",
            f"{'-'*60}",
        ]
        
        for feed_name, feed_metrics in self.metrics.items():
            lines.extend([
                f"  {feed_name}:",
                f"    Loaded: {feed_metrics.records_loaded:,}, "
                f"Failed: {feed_metrics.records_failed:,}, "
                f"Success: {feed_metrics.success_rate:.1f}%",
            ])
        
        lines.extend([
            f"",
            f"{'='*60}\n",
        ])
        
        return "\n".join(lines)


class Timer:
    """
    Context manager for timing operations.
    
    Example:
        >>> with Timer() as timer:
        ...     # Do some work
        ...     pass
        >>> print(f"Operation took {timer.elapsed_seconds:.2f} seconds")
    """
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
    
    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time


# Example usage
if __name__ == "__main__":
    # Create a metrics collector
    collector = MetricsCollector()
    
    # Register feeds
    employee_metrics = collector.register_feed("employees")
    ref_data_metrics = collector.register_feed("reference_data")
    
    # Simulate some metrics
    employee_metrics.records_extracted = 107
    employee_metrics.records_loaded = 105
    employee_metrics.records_failed = 2
    employee_metrics.ru_consumed = 1500.5
    employee_metrics.mark_complete()
    
    ref_data_metrics.records_extracted = 98
    ref_data_metrics.records_loaded = 98
    ref_data_metrics.records_failed = 0
    ref_data_metrics.ru_consumed = 500.0
    ref_data_metrics.mark_complete()
    
    # Print summaries
    print(employee_metrics.generate_summary())
    print(ref_data_metrics.generate_summary())
    print(collector.generate_aggregate_summary())

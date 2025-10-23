"""
Extractors Module

This module provides data extraction functionality from source systems.
Includes base classes and concrete implementations for various data sources.
"""

from extractors.base_extractor import BaseExtractor, BatchExtractor
from extractors.oracle_extractor import OracleExtractor

__all__ = [
    "BaseExtractor",
    "BatchExtractor",
    "OracleExtractor",
]

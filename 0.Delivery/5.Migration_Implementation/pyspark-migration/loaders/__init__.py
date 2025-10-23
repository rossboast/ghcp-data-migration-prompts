"""
Loaders Module

This module provides data loading functionality to target systems.
Includes base classes and concrete implementations for various target systems.
"""

from loaders.base_loader import BaseLoader, BatchLoader
from loaders.cosmos_loader import CosmosLoader

__all__ = [
    "BaseLoader",
    "BatchLoader",
    "CosmosLoader",
]

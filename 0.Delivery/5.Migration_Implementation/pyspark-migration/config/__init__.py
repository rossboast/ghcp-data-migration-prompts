"""
Configuration Module

This module provides centralized access to all configuration components:
- Connection configurations (Oracle, Cosmos DB)
- Schema definitions (source and target)
- Transformation rules and mappings

Usage:
    from config import get_oracle_config, get_cosmos_config
    from config import OracleSchemas, CosmosSchemas
    from config import PartitionKeyConfig, TransformationRules
"""

# Connection management
from config.connections import (
    OracleConnectionConfig,
    CosmosDBConnectionConfig,
    ConnectionManager,
    CosmosContainers,
)

# Schema definitions
from config.schema_definitions import (
    OracleSchemas,
    CosmosSchemas,
    TableNames,
    SchemaRegistry,
)

# Transformation configuration
from config.transformation_config import (
    PartitionKeyConfig,
    DocumentIdConfig,
    FieldMappings,
    TransformationRules,
    ReferenceDataTypes,
    BatchConfig,
    MigrationPhases,
)

# Convenience functions
get_oracle_config = ConnectionManager.get_oracle_config
get_cosmos_config = ConnectionManager.get_cosmos_config

__all__ = [
    # Connection configs
    "OracleConnectionConfig",
    "CosmosDBConnectionConfig",
    "ConnectionManager",
    "CosmosContainers",
    "get_oracle_config",
    "get_cosmos_config",
    
    # Schemas
    "OracleSchemas",
    "CosmosSchemas",
    "TableNames",
    "SchemaRegistry",
    
    # Transformation config
    "PartitionKeyConfig",
    "DocumentIdConfig",
    "FieldMappings",
    "TransformationRules",
    "ReferenceDataTypes",
    "BatchConfig",
    "MigrationPhases",
]

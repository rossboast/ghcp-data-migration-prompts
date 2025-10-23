"""
Transformation Configuration

This module defines configuration for data transformations including:
- Field mappings between source and target
- Transformation rules
- Business logic configurations
- Partition key generation rules
"""

from typing import Dict, List, Any, Callable
from datetime import datetime

from utils.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# PARTITION KEY CONFIGURATION
# ============================================================================

class PartitionKeyConfig:
    """
    Configuration for partition key generation.
    
    Based on Phase 4 migration strategy, we use synthetic partition keys
    to ensure even distribution across partitions.
    """
    
    # Employees container: dept_{department_id}_{employee_id % 10}
    EMPLOYEES_MODULO = 10
    
    @staticmethod
    def generate_employee_partition_key(department_id: int, employee_id: int) -> str:
        """
        Generate synthetic partition key for employee documents.
        
        Formula: dept_{department_id}_{employee_id % 10}
        
        Args:
            department_id: Department ID (can be None for employees without dept)
            employee_id: Employee ID
            
        Returns:
            Partition key string
            
        Example:
            >>> generate_employee_partition_key(90, 101)
            'dept_90_1'
            >>> generate_employee_partition_key(None, 101)
            'dept_null_1'
        """
        dept_part = str(department_id) if department_id is not None else "null"
        modulo_part = employee_id % PartitionKeyConfig.EMPLOYEES_MODULO
        return f"dept_{dept_part}_{modulo_part}"
    
    @staticmethod
    def generate_reference_data_partition_key(entity_type: str) -> str:
        """
        Generate partition key for reference data documents.
        
        All documents of the same type share a partition key.
        
        Args:
            entity_type: Type of entity (region, country, location, department, job)
            
        Returns:
            Partition key string (same as entity type)
            
        Example:
            >>> generate_reference_data_partition_key("region")
            'region'
        """
        return entity_type.lower()
    
    @staticmethod
    def generate_audit_log_partition_key(timestamp: datetime) -> str:
        """
        Generate partition key for audit log documents.
        
        Uses year-month format for time-based partitioning.
        
        Args:
            timestamp: Timestamp of the audit event
            
        Returns:
            Partition key in format "YYYY-MM"
            
        Example:
            >>> from datetime import datetime
            >>> generate_audit_log_partition_key(datetime(2025, 10, 22))
            '2025-10'
        """
        return timestamp.strftime("%Y-%m")


# ============================================================================
# DOCUMENT ID GENERATION
# ============================================================================

class DocumentIdConfig:
    """Configuration for generating Cosmos DB document IDs."""
    
    @staticmethod
    def generate_employee_id(employee_id: int) -> str:
        """
        Generate document ID for employee.
        
        Args:
            employee_id: Employee ID from Oracle
            
        Returns:
            Document ID string
        """
        return f"emp_{employee_id}"
    
    @staticmethod
    def generate_reference_data_id(entity_type: str, entity_id: Any) -> str:
        """
        Generate document ID for reference data.
        
        Args:
            entity_type: Type of entity (region, country, etc.)
            entity_id: ID of the entity
            
        Returns:
            Document ID string
            
        Example:
            >>> generate_reference_data_id("region", 1)
            'region_1'
            >>> generate_reference_data_id("country", "US")
            'country_US'
        """
        return f"{entity_type.lower()}_{entity_id}"
    
    @staticmethod
    def generate_audit_log_id(timestamp: datetime, entity_type: str, entity_id: Any) -> str:
        """
        Generate document ID for audit log entry.
        
        Args:
            timestamp: Timestamp of the audit event
            entity_type: Type of entity being audited
            entity_id: ID of the entity
            
        Returns:
            Document ID string
        """
        timestamp_str = timestamp.strftime("%Y%m%d%H%M%S%f")
        return f"audit_{entity_type}_{entity_id}_{timestamp_str}"


# ============================================================================
# FIELD MAPPINGS
# ============================================================================

class FieldMappings:
    """
    Field mappings between Oracle columns and Cosmos DB document fields.
    """
    
    # Region mappings
    REGION = {
        "REGION_ID": "region_id",
        "REGION_NAME": "region_name",
    }
    
    # Country mappings
    COUNTRY = {
        "COUNTRY_ID": "country_id",
        "COUNTRY_NAME": "country_name",
        "REGION_ID": "region_id",
    }
    
    # Location mappings
    LOCATION = {
        "LOCATION_ID": "location_id",
        "STREET_ADDRESS": "street_address",
        "POSTAL_CODE": "postal_code",
        "CITY": "city",
        "STATE_PROVINCE": "state_province",
        "COUNTRY_ID": "country_id",
    }
    
    # Department mappings
    DEPARTMENT = {
        "DEPARTMENT_ID": "department_id",
        "DEPARTMENT_NAME": "department_name",
        "MANAGER_ID": "manager_id",
        "LOCATION_ID": "location_id",
    }
    
    # Job mappings
    JOB = {
        "JOB_ID": "job_id",
        "JOB_TITLE": "job_title",
        "MIN_SALARY": "min_salary",
        "MAX_SALARY": "max_salary",
    }
    
    # Employee mappings
    EMPLOYEE = {
        "EMPLOYEE_ID": "employee_id",
        "FIRST_NAME": "first_name",
        "LAST_NAME": "last_name",
        "EMAIL": "email",
        "PHONE_NUMBER": "phone_number",
        "HIRE_DATE": "hire_date",
        "JOB_ID": "job_id",
        "SALARY": "salary",
        "COMMISSION_PCT": "commission_pct",
        "MANAGER_ID": "manager_id",
        "DEPARTMENT_ID": "department_id",
    }
    
    # Job history mappings
    JOB_HISTORY = {
        "EMPLOYEE_ID": "employee_id",
        "START_DATE": "start_date",
        "END_DATE": "end_date",
        "JOB_ID": "job_id",
        "DEPARTMENT_ID": "department_id",
    }


# ============================================================================
# TRANSFORMATION RULES
# ============================================================================

class TransformationRules:
    """
    Business rules and transformation logic configuration.
    """
    
    # Default values
    DEFAULTS = {
        "source_system": "Oracle HR Schema",
        "version": 1,
        "entity_type_employee": "employee",
    }
    
    # Date format for Cosmos DB (ISO 8601)
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
    
    # String trimming rules
    TRIM_FIELDS = [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "department_name",
        "job_title",
        "city",
        "country_name",
        "region_name",
    ]
    
    # Fields to convert to uppercase
    UPPERCASE_FIELDS = [
        "email",
        "country_id",
    ]
    
    # Fields to convert to lowercase
    LOWERCASE_FIELDS: List[str] = []
    
    # Null handling: Fields that should never be null (replace with defaults)
    NULL_REPLACEMENTS = {
        "commission_pct": 0.0,
        "phone_number": "N/A",
    }
    
    # Validation rules
    VALIDATION_RULES = {
        "email": {
            "required": True,
            "pattern": r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$",
            "max_length": 100,
        },
        "salary": {
            "min_value": 0,
            "max_value": 1000000,
        },
        "commission_pct": {
            "min_value": 0.0,
            "max_value": 0.99,
        },
        "phone_number": {
            "pattern": r"^\+?[\d\s\-\(\)\.]+$",
            "max_length": 20,
        },
    }


# ============================================================================
# REFERENCE DATA ENTITY TYPES
# ============================================================================

class ReferenceDataTypes:
    """Constants for reference data entity types."""
    REGION = "region"
    COUNTRY = "country"
    LOCATION = "location"
    DEPARTMENT = "department"
    JOB = "job"
    
    @classmethod
    def get_all_types(cls) -> List[str]:
        """Get list of all reference data types."""
        return [
            cls.REGION,
            cls.COUNTRY,
            cls.LOCATION,
            cls.DEPARTMENT,
            cls.JOB,
        ]


# ============================================================================
# BATCH CONFIGURATION
# ============================================================================

class BatchConfig:
    """Configuration for batch processing."""
    
    # Cosmos DB batch sizes
    COSMOS_WRITE_BATCH_SIZE = 1000  # Documents per batch
    COSMOS_MAX_RETRIES = 3
    COSMOS_RETRY_DELAY_SECONDS = 2
    
    # Spark DataFrame repartition sizes
    SMALL_TABLE_PARTITIONS = 1  # For tables < 1000 rows
    MEDIUM_TABLE_PARTITIONS = 10  # For tables < 100K rows
    LARGE_TABLE_PARTITIONS = 100  # For tables > 100K rows
    
    # Processing batch sizes
    VALIDATION_BATCH_SIZE = 100  # Records to validate before collecting errors
    TRANSFORMATION_BATCH_SIZE = 500  # Records to transform in memory at once


# ============================================================================
# MIGRATION PHASES
# ============================================================================

class MigrationPhases:
    """
    Migration phase configuration based on Phase 4 strategy.
    
    Phase 1: Reference data (regions, countries, locations, jobs)
    Phase 2a: Departments with NULL manager_id
    Phase 2b: Employees with NULL manager_id
    Phase 3a: Update departments with actual manager_id
    Phase 3b: Update employees with actual manager_id
    Phase 4: Embed and denormalize employee documents
    """
    
    PHASE_1_TABLES = ["REGIONS", "COUNTRIES", "LOCATIONS", "JOBS"]
    PHASE_2A_TABLES = ["DEPARTMENTS"]
    PHASE_2B_TABLES = ["EMPLOYEES"]
    PHASE_3A_TABLES = ["DEPARTMENTS"]  # Update operation
    PHASE_3B_TABLES = ["EMPLOYEES"]  # Update operation
    PHASE_4_TABLES = ["EMPLOYEES"]  # Denormalization
    
    @classmethod
    def get_phase_description(cls, phase: int) -> str:
        """Get description of a migration phase."""
        descriptions = {
            1: "Load reference data (regions, countries, locations, jobs)",
            2: "Load departments and employees with NULL circular references",
            3: "Resolve circular references (update manager_id)",
            4: "Denormalize and embed related data in employee documents",
        }
        return descriptions.get(phase, "Unknown phase")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_table_batch_size(table_name: str, row_count: int) -> int:
    """
    Determine appropriate batch size for a table.
    
    Args:
        table_name: Name of the table
        row_count: Estimated row count
        
    Returns:
        Recommended batch size
    """
    if row_count < 1000:
        return BatchConfig.SMALL_TABLE_PARTITIONS
    elif row_count < 100000:
        return BatchConfig.MEDIUM_TABLE_PARTITIONS
    else:
        return BatchConfig.LARGE_TABLE_PARTITIONS


def should_trim_field(field_name: str) -> bool:
    """Check if a field should be trimmed."""
    return field_name.lower() in [f.lower() for f in TransformationRules.TRIM_FIELDS]


def should_uppercase_field(field_name: str) -> bool:
    """Check if a field should be converted to uppercase."""
    return field_name.lower() in [f.lower() for f in TransformationRules.UPPERCASE_FIELDS]


def get_null_replacement(field_name: str) -> Any:
    """Get default replacement value for null fields."""
    return TransformationRules.NULL_REPLACEMENTS.get(field_name.lower())


if __name__ == "__main__":
    # Example usage
    print("Transformation Configuration Examples")
    print("=" * 60)
    
    # Partition key examples
    print("\nPartition Key Examples:")
    print(f"Employee (dept 90, emp 101): {PartitionKeyConfig.generate_employee_partition_key(90, 101)}")
    print(f"Employee (no dept, emp 178): {PartitionKeyConfig.generate_employee_partition_key(None, 178)}")
    print(f"Reference data (region): {PartitionKeyConfig.generate_reference_data_partition_key('region')}")
    
    # Document ID examples
    print("\nDocument ID Examples:")
    print(f"Employee 101: {DocumentIdConfig.generate_employee_id(101)}")
    print(f"Region 1: {DocumentIdConfig.generate_reference_data_id('region', 1)}")
    print(f"Country US: {DocumentIdConfig.generate_reference_data_id('country', 'US')}")
    
    # Migration phases
    print("\nMigration Phases:")
    for phase in range(1, 5):
        print(f"Phase {phase}: {MigrationPhases.get_phase_description(phase)}")

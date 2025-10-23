"""
Schema Definitions

This module defines PySpark schemas for all Oracle HR tables and
target Cosmos DB document structures.

These schemas are used for:
- Reading data from Oracle with proper type inference
- Validating data during transformation
- Writing data to Cosmos DB
"""

from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    DecimalType,
    DateType,
    TimestampType,
    ArrayType,
)

from utils.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# ORACLE SOURCE SCHEMAS
# ============================================================================

class OracleSchemas:
    """
    PySpark schema definitions for Oracle HR tables.
    
    These schemas match the Oracle table structures and are used
    when reading data via JDBC.
    """
    
    REGIONS = StructType([
        StructField("REGION_ID", IntegerType(), nullable=False),
        StructField("REGION_NAME", StringType(), nullable=True),
    ])
    
    COUNTRIES = StructType([
        StructField("COUNTRY_ID", StringType(), nullable=False),  # CHAR(2)
        StructField("COUNTRY_NAME", StringType(), nullable=True),  # VARCHAR2(60)
        StructField("REGION_ID", IntegerType(), nullable=True),
    ])
    
    LOCATIONS = StructType([
        StructField("LOCATION_ID", IntegerType(), nullable=False),  # NUMBER(4)
        StructField("STREET_ADDRESS", StringType(), nullable=True),  # VARCHAR2(40)
        StructField("POSTAL_CODE", StringType(), nullable=True),  # VARCHAR2(12)
        StructField("CITY", StringType(), nullable=False),  # VARCHAR2(30)
        StructField("STATE_PROVINCE", StringType(), nullable=True),  # VARCHAR2(25)
        StructField("COUNTRY_ID", StringType(), nullable=True),  # CHAR(2)
    ])
    
    DEPARTMENTS = StructType([
        StructField("DEPARTMENT_ID", IntegerType(), nullable=False),  # NUMBER(4)
        StructField("DEPARTMENT_NAME", StringType(), nullable=False),  # VARCHAR2(30)
        StructField("MANAGER_ID", IntegerType(), nullable=True),  # NUMBER(6)
        StructField("LOCATION_ID", IntegerType(), nullable=True),  # NUMBER(4)
    ])
    
    JOBS = StructType([
        StructField("JOB_ID", StringType(), nullable=False),  # VARCHAR2(10)
        StructField("JOB_TITLE", StringType(), nullable=False),  # VARCHAR2(35)
        StructField("MIN_SALARY", IntegerType(), nullable=True),  # NUMBER(6)
        StructField("MAX_SALARY", IntegerType(), nullable=True),  # NUMBER(6)
    ])
    
    EMPLOYEES = StructType([
        StructField("EMPLOYEE_ID", IntegerType(), nullable=False),  # NUMBER(6)
        StructField("FIRST_NAME", StringType(), nullable=True),  # VARCHAR2(20)
        StructField("LAST_NAME", StringType(), nullable=False),  # VARCHAR2(25)
        StructField("EMAIL", StringType(), nullable=False),  # VARCHAR2(25)
        StructField("PHONE_NUMBER", StringType(), nullable=True),  # VARCHAR2(20)
        StructField("HIRE_DATE", DateType(), nullable=False),  # DATE
        StructField("JOB_ID", StringType(), nullable=False),  # VARCHAR2(10)
        StructField("SALARY", DecimalType(8, 2), nullable=True),  # NUMBER(8,2)
        StructField("COMMISSION_PCT", DecimalType(2, 2), nullable=True),  # NUMBER(2,2)
        StructField("MANAGER_ID", IntegerType(), nullable=True),  # NUMBER(6)
        StructField("DEPARTMENT_ID", IntegerType(), nullable=True),  # NUMBER(4)
    ])
    
    JOB_HISTORY = StructType([
        StructField("EMPLOYEE_ID", IntegerType(), nullable=False),  # NUMBER(6)
        StructField("START_DATE", DateType(), nullable=False),  # DATE
        StructField("END_DATE", DateType(), nullable=False),  # DATE
        StructField("JOB_ID", StringType(), nullable=False),  # VARCHAR2(10)
        StructField("DEPARTMENT_ID", IntegerType(), nullable=True),  # NUMBER(4)
    ])


# ============================================================================
# COSMOS DB TARGET SCHEMAS
# ============================================================================

class CosmosSchemas:
    """
    PySpark schema definitions for Cosmos DB documents.
    
    These schemas define the structure of denormalized documents
    that will be written to Cosmos DB.
    """
    
    # Metadata schema (common to all documents)
    METADATA = StructType([
        StructField("created_at", TimestampType(), nullable=False),
        StructField("updated_at", TimestampType(), nullable=False),
        StructField("source_system", StringType(), nullable=False),
        StructField("migration_batch", StringType(), nullable=True),
        StructField("version", IntegerType(), nullable=False),
    ])
    
    # Reference data document schema (regions, countries, locations, departments, jobs)
    REFERENCE_DATA = StructType([
        StructField("id", StringType(), nullable=False),
        StructField("partitionKey", StringType(), nullable=False),
        StructField("entityType", StringType(), nullable=False),
        StructField("data", StringType(), nullable=False),  # JSON string of actual data
        StructField("metadata", METADATA, nullable=False),
    ])
    
    # Job details (embedded in employee document)
    JOB_DETAILS = StructType([
        StructField("job_id", StringType(), nullable=False),
        StructField("job_title", StringType(), nullable=False),
        StructField("min_salary", IntegerType(), nullable=True),
        StructField("max_salary", IntegerType(), nullable=True),
    ])
    
    # Location details (embedded in employee document)
    LOCATION_DETAILS = StructType([
        StructField("location_id", IntegerType(), nullable=False),
        StructField("street_address", StringType(), nullable=True),
        StructField("postal_code", StringType(), nullable=True),
        StructField("city", StringType(), nullable=False),
        StructField("state_province", StringType(), nullable=True),
        StructField("country", StructType([
            StructField("country_id", StringType(), nullable=False),
            StructField("country_name", StringType(), nullable=True),
            StructField("region", StructType([
                StructField("region_id", IntegerType(), nullable=False),
                StructField("region_name", StringType(), nullable=True),
            ]), nullable=True),
        ]), nullable=True),
    ])
    
    # Department details (embedded in employee document)
    DEPARTMENT_DETAILS = StructType([
        StructField("department_id", IntegerType(), nullable=False),
        StructField("department_name", StringType(), nullable=False),
        StructField("manager", StructType([
            StructField("employee_id", IntegerType(), nullable=True),
            StructField("first_name", StringType(), nullable=True),
            StructField("last_name", StringType(), nullable=True),
            StructField("email", StringType(), nullable=True),
        ]), nullable=True),
        StructField("location", LOCATION_DETAILS, nullable=True),
    ])
    
    # Manager details (embedded in employee document)
    MANAGER_DETAILS = StructType([
        StructField("employee_id", IntegerType(), nullable=True),
        StructField("first_name", StringType(), nullable=True),
        StructField("last_name", StringType(), nullable=True),
        StructField("email", StringType(), nullable=True),
        StructField("job_title", StringType(), nullable=True),
    ])
    
    # Job history entry
    JOB_HISTORY_ENTRY = StructType([
        StructField("start_date", StringType(), nullable=False),  # ISO 8601 string
        StructField("end_date", StringType(), nullable=False),  # ISO 8601 string
        StructField("job_id", StringType(), nullable=False),
        StructField("job_title", StringType(), nullable=True),
        StructField("department_id", IntegerType(), nullable=True),
        StructField("department_name", StringType(), nullable=True),
        StructField("duration_days", IntegerType(), nullable=True),
    ])
    
    # Complete employee document schema
    EMPLOYEE_DOCUMENT = StructType([
        StructField("id", StringType(), nullable=False),
        StructField("partitionKey", StringType(), nullable=False),
        StructField("entityType", StringType(), nullable=False),
        
        # Employee basic info
        StructField("employee", StructType([
            StructField("employee_id", IntegerType(), nullable=False),
            StructField("first_name", StringType(), nullable=True),
            StructField("last_name", StringType(), nullable=False),
            StructField("email", StringType(), nullable=False),
            StructField("phone_number", StringType(), nullable=True),
            StructField("hire_date", StringType(), nullable=False),  # ISO 8601
            StructField("salary", DecimalType(8, 2), nullable=True),
            StructField("commission_pct", DecimalType(2, 2), nullable=True),
        ]), nullable=False),
        
        # Embedded related data
        StructField("job", JOB_DETAILS, nullable=False),
        StructField("department", DEPARTMENT_DETAILS, nullable=True),
        StructField("manager", MANAGER_DETAILS, nullable=True),
        StructField("job_history", ArrayType(JOB_HISTORY_ENTRY), nullable=True),
        
        # Metadata
        StructField("metadata", METADATA, nullable=False),
    ])
    
    # Audit log document schema
    AUDIT_LOG = StructType([
        StructField("id", StringType(), nullable=False),
        StructField("partitionKey", StringType(), nullable=False),  # Year-month: "2025-10"
        StructField("timestamp", TimestampType(), nullable=False),
        StructField("operation", StringType(), nullable=False),  # CREATE, UPDATE, DELETE
        StructField("entity_type", StringType(), nullable=False),  # employee, department, etc.
        StructField("entity_id", StringType(), nullable=False),
        StructField("changed_by", StringType(), nullable=True),
        StructField("changes", StringType(), nullable=True),  # JSON string of changes
    ])


# ============================================================================
# TABLE NAME MAPPINGS
# ============================================================================

class TableNames:
    """Oracle table names."""
    REGIONS = "REGIONS"
    COUNTRIES = "COUNTRIES"
    LOCATIONS = "LOCATIONS"
    DEPARTMENTS = "DEPARTMENTS"
    JOBS = "JOBS"
    EMPLOYEES = "EMPLOYEES"
    JOB_HISTORY = "JOB_HISTORY"
    
    @classmethod
    def get_all_tables(cls) -> list:
        """Get list of all table names."""
        return [
            cls.REGIONS,
            cls.COUNTRIES,
            cls.LOCATIONS,
            cls.DEPARTMENTS,
            cls.JOBS,
            cls.EMPLOYEES,
            cls.JOB_HISTORY,
        ]
    
    @classmethod
    def get_reference_tables(cls) -> list:
        """Get list of reference data tables."""
        return [
            cls.REGIONS,
            cls.COUNTRIES,
            cls.LOCATIONS,
            cls.DEPARTMENTS,
            cls.JOBS,
        ]
    
    @classmethod
    def get_transaction_tables(cls) -> list:
        """Get list of transactional tables."""
        return [
            cls.EMPLOYEES,
            cls.JOB_HISTORY,
        ]


# ============================================================================
# SCHEMA REGISTRY
# ============================================================================

class SchemaRegistry:
    """
    Central registry for accessing schemas by table name.
    """
    
    _oracle_schemas = {
        TableNames.REGIONS: OracleSchemas.REGIONS,
        TableNames.COUNTRIES: OracleSchemas.COUNTRIES,
        TableNames.LOCATIONS: OracleSchemas.LOCATIONS,
        TableNames.DEPARTMENTS: OracleSchemas.DEPARTMENTS,
        TableNames.JOBS: OracleSchemas.JOBS,
        TableNames.EMPLOYEES: OracleSchemas.EMPLOYEES,
        TableNames.JOB_HISTORY: OracleSchemas.JOB_HISTORY,
    }
    
    @classmethod
    def get_oracle_schema(cls, table_name: str) -> StructType:
        """
        Get Oracle schema for a table.
        
        Args:
            table_name: Name of the Oracle table
            
        Returns:
            StructType schema definition
            
        Raises:
            ValueError: If table name not found
        """
        schema = cls._oracle_schemas.get(table_name.upper())
        if schema is None:
            raise ValueError(f"No schema found for table: {table_name}")
        return schema
    
    @classmethod
    def get_cosmos_schema(cls, document_type: str) -> StructType:
        """
        Get Cosmos DB schema for a document type.
        
        Args:
            document_type: Type of document (employee, reference_data, audit_log)
            
        Returns:
            StructType schema definition
            
        Raises:
            ValueError: If document type not found
        """
        schemas = {
            "employee": CosmosSchemas.EMPLOYEE_DOCUMENT,
            "reference_data": CosmosSchemas.REFERENCE_DATA,
            "audit_log": CosmosSchemas.AUDIT_LOG,
        }
        
        schema = schemas.get(document_type.lower())
        if schema is None:
            raise ValueError(f"No schema found for document type: {document_type}")
        return schema


if __name__ == "__main__":
    # Example: Print all Oracle table schemas
    print("Oracle Table Schemas:")
    print("=" * 60)
    
    for table_name in TableNames.get_all_tables():
        schema = SchemaRegistry.get_oracle_schema(table_name)
        print(f"\n{table_name}:")
        schema.printTreeString()
    
    # Example: Print Cosmos document schemas
    print("\n\nCosmos DB Document Schemas:")
    print("=" * 60)
    
    print("\nEmployee Document:")
    CosmosSchemas.EMPLOYEE_DOCUMENT.printTreeString()
    
    print("\nReference Data Document:")
    CosmosSchemas.REFERENCE_DATA.printTreeString()

"""
Oracle Extractor

Extracts data from Oracle database using JDBC connection.
Extends BaseExtractor to leverage automatic metrics, logging, and error handling.

Usage:
    from extractors import OracleExtractor
    from config import get_oracle_config
    
    config = get_oracle_config()
    extractor = OracleExtractor(config)
    
    # Extract single table
    df = extractor.extract_with_metrics("employees")
    
    # Extract multiple tables
    tables_dict = extractor.extract_all_tables()
"""

from typing import Dict, Optional, List, Any
from pyspark.sql import DataFrame
from pyspark.sql.types import StructType

from extractors.base_extractor import BaseExtractor
from config.connections import OracleConnectionConfig
from config.schema_definitions import OracleSchemas
from utils.spark_session import SparkSessionManager
from utils.logging_config import get_logger
from utils.metrics import MetricsCollector
from utils.error_handler import ExtractionError, retry


class OracleExtractor(BaseExtractor):
    """
    Extract data from Oracle database via JDBC.
    
    Features:
    - JDBC-based extraction with proper driver configuration
    - Schema validation using predefined schemas
    - Connection pooling and retry logic
    - Table-specific extraction methods
    - Batch extraction support
    - Query pushdown for filtering
    """
    
    # Available tables in Oracle HR schema
    AVAILABLE_TABLES = [
        "regions",
        "countries",
        "locations",
        "departments",
        "jobs",
        "employees",
        "job_history"
    ]
    
    def __init__(
        self,
        config: OracleConnectionConfig,
        logger: Optional[Any] = None,
        metrics: Optional[MetricsCollector] = None
    ):
        """
        Initialize Oracle extractor.
        
        Args:
            config: Oracle connection configuration
            logger: Optional logger instance (will create if not provided)
            metrics: Optional metrics collector (will create if not provided)
        """
        super().__init__(
            name="oracle_extractor",
            config=config,
            logger=logger or get_logger("oracle_extractor"),
            metrics=metrics or MetricsCollector("oracle_extractor")
        )
        
        self.config: OracleConnectionConfig = config
        self.spark = SparkSessionManager.get_session()
        self.schemas = OracleSchemas()
        
        # JDBC connection properties
        self.jdbc_properties = {
            "user": self.config.user,
            "password": self.config.password,
            "driver": "oracle.jdbc.driver.OracleDriver",
            "fetchsize": "10000",  # Fetch 10k rows at a time
            "oracle.jdbc.timezoneAsRegion": "false",  # Handle timezone properly
        }
        
        self.logger.info(
            "Oracle extractor initialized",
            jdbc_url=self.config.jdbc_url,
            available_tables=len(self.AVAILABLE_TABLES)
        )
    
    def validate_connection(self) -> bool:
        """
        Validate Oracle database connection.
        
        Returns:
            True if connection is valid, raises exception otherwise
            
        Raises:
            ExtractionError: If connection validation fails
        """
        self.logger.info("Validating Oracle connection")
        
        try:
            # Try a simple query
            test_query = "(SELECT 1 FROM DUAL) test_table"
            
            test_df = self.spark.read.jdbc(
                url=self.config.jdbc_url,
                table=test_query,
                properties=self.jdbc_properties
            )
            
            # Execute the query
            count = test_df.count()
            
            if count != 1:
                raise ExtractionError(
                    f"Connection test failed: expected 1 row, got {count}",
                    context={"jdbc_url": self.config.jdbc_url}
                )
            
            self.logger.info("Oracle connection validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(
                "Oracle connection validation failed",
                error=str(e),
                jdbc_url=self.config.jdbc_url
            )
            raise ExtractionError(
                f"Failed to connect to Oracle: {str(e)}",
                context={"jdbc_url": self.config.jdbc_url}
            ) from e
    
    def extract(
        self,
        table_name: str,
        where_clause: Optional[str] = None,
        columns: Optional[List[str]] = None,
        **kwargs
    ) -> DataFrame:
        """
        Extract data from a specific Oracle table.
        
        Args:
            table_name: Name of the table to extract
            where_clause: Optional WHERE clause for filtering (without WHERE keyword)
            columns: Optional list of columns to select (defaults to all)
            **kwargs: Additional arguments
            
        Returns:
            DataFrame with extracted data
            
        Raises:
            ExtractionError: If extraction fails
        """
        # Validate table name
        if table_name.lower() not in [t.lower() for t in self.AVAILABLE_TABLES]:
            raise ExtractionError(
                f"Table '{table_name}' not in available tables",
                context={"available_tables": self.AVAILABLE_TABLES}
            )
        
        # Get schema for the table
        schema = self._get_table_schema(table_name)
        
        # Build query
        query = self._build_query(table_name, where_clause, columns)
        
        self.logger.info(
            "Extracting from Oracle",
            table=table_name,
            query=query,
            has_where=where_clause is not None,
            has_columns=columns is not None
        )
        
        try:
            # Read from JDBC with schema
            df = self.spark.read.jdbc(
                url=self.config.jdbc_url,
                table=query,
                properties=self.jdbc_properties
            ).schema(schema) if schema else self.spark.read.jdbc(
                url=self.config.jdbc_url,
                table=query,
                properties=self.jdbc_properties
            )
            
            # Count records
            record_count = df.count()
            
            self.logger.info(
                "Extraction completed",
                table=table_name,
                records=record_count
            )
            
            return df
            
        except Exception as e:
            self.logger.error(
                "Extraction failed",
                table=table_name,
                error=str(e)
            )
            raise ExtractionError(
                f"Failed to extract from {table_name}: {str(e)}",
                context={
                    "table": table_name,
                    "query": query,
                    "jdbc_url": self.config.jdbc_url
                }
            ) from e
    
    def extract_all_tables(
        self,
        tables: Optional[List[str]] = None,
        validate: bool = True
    ) -> Dict[str, DataFrame]:
        """
        Extract multiple tables from Oracle.
        
        Args:
            tables: List of table names (defaults to all available tables)
            validate: Whether to validate connection first
            
        Returns:
            Dictionary mapping table names to DataFrames
            
        Raises:
            ExtractionError: If any extraction fails
        """
        if validate:
            self.validate_connection()
        
        tables_to_extract = tables or self.AVAILABLE_TABLES
        
        self.logger.info(
            "Extracting multiple tables",
            table_count=len(tables_to_extract),
            tables=tables_to_extract
        )
        
        results = {}
        
        for table in tables_to_extract:
            try:
                df = self.extract_with_metrics(table)
                results[table] = df
                
            except Exception as e:
                self.logger.error(
                    "Failed to extract table",
                    table=table,
                    error=str(e)
                )
                # Re-raise with context
                raise ExtractionError(
                    f"Failed to extract table {table}",
                    context={"table": table, "completed": list(results.keys())}
                ) from e
        
        self.logger.info(
            "Multiple table extraction completed",
            tables_extracted=len(results),
            total_records=sum(df.count() for df in results.values())
        )
        
        return results
    
    # Table-specific extraction methods for convenience
    
    def extract_regions(self) -> DataFrame:
        """Extract regions table."""
        return self.extract_with_metrics("regions")
    
    def extract_countries(self) -> DataFrame:
        """Extract countries table."""
        return self.extract_with_metrics("countries")
    
    def extract_locations(self) -> DataFrame:
        """Extract locations table."""
        return self.extract_with_metrics("locations")
    
    def extract_departments(self, include_null_managers: bool = True) -> DataFrame:
        """
        Extract departments table.
        
        Args:
            include_null_managers: If False, only extract departments with NULL manager_id
            
        Returns:
            DataFrame with departments
        """
        where_clause = None if include_null_managers else "manager_id IS NULL"
        return self.extract_with_metrics("departments", where_clause=where_clause)
    
    def extract_jobs(self) -> DataFrame:
        """Extract jobs table."""
        return self.extract_with_metrics("jobs")
    
    def extract_employees(self, active_only: bool = False) -> DataFrame:
        """
        Extract employees table.
        
        Args:
            active_only: If True, only extract employees with non-null department_id
            
        Returns:
            DataFrame with employees
        """
        where_clause = "department_id IS NOT NULL" if active_only else None
        return self.extract_with_metrics("employees", where_clause=where_clause)
    
    def extract_job_history(self, employee_id: Optional[int] = None) -> DataFrame:
        """
        Extract job_history table.
        
        Args:
            employee_id: Optional employee ID to filter by
            
        Returns:
            DataFrame with job history
        """
        where_clause = f"employee_id = {employee_id}" if employee_id else None
        return self.extract_with_metrics("job_history", where_clause=where_clause)
    
    def get_table_count(self, table_name: str, where_clause: Optional[str] = None) -> int:
        """
        Get row count for a table without loading data.
        
        Args:
            table_name: Name of the table
            where_clause: Optional WHERE clause for filtering
            
        Returns:
            Number of rows in the table
        """
        query = f"(SELECT COUNT(*) as cnt FROM {table_name.upper()}"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += ") count_query"
        
        try:
            count_df = self.spark.read.jdbc(
                url=self.config.jdbc_url,
                table=query,
                properties=self.jdbc_properties
            )
            
            count = count_df.collect()[0]["cnt"]
            
            self.logger.debug(
                "Table count retrieved",
                table=table_name,
                count=count,
                has_filter=where_clause is not None
            )
            
            return count
            
        except Exception as e:
            self.logger.error(
                "Failed to get table count",
                table=table_name,
                error=str(e)
            )
            raise ExtractionError(
                f"Failed to count rows in {table_name}: {str(e)}",
                context={"table": table_name, "where": where_clause}
            ) from e
    
    def get_all_table_counts(self) -> Dict[str, int]:
        """
        Get row counts for all available tables.
        
        Returns:
            Dictionary mapping table names to row counts
        """
        self.logger.info("Retrieving counts for all tables")
        
        counts = {}
        for table in self.AVAILABLE_TABLES:
            try:
                counts[table] = self.get_table_count(table)
            except Exception as e:
                self.logger.warning(
                    "Failed to get count for table",
                    table=table,
                    error=str(e)
                )
                counts[table] = -1  # Indicate error
        
        self.logger.info(
            "Table counts retrieved",
            tables=len(counts),
            total_records=sum(c for c in counts.values() if c > 0)
        )
        
        return counts
    
    # Private helper methods
    
    def _get_table_schema(self, table_name: str) -> Optional[StructType]:
        """
        Get PySpark schema for a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            StructType schema or None if not found
        """
        schema_map = {
            "regions": self.schemas.regions,
            "countries": self.schemas.countries,
            "locations": self.schemas.locations,
            "departments": self.schemas.departments,
            "jobs": self.schemas.jobs,
            "employees": self.schemas.employees,
            "job_history": self.schemas.job_history
        }
        
        return schema_map.get(table_name.lower())
    
    def _build_query(
        self,
        table_name: str,
        where_clause: Optional[str] = None,
        columns: Optional[List[str]] = None
    ) -> str:
        """
        Build JDBC query string.
        
        Args:
            table_name: Name of the table
            where_clause: Optional WHERE clause
            columns: Optional column list
            
        Returns:
            Query string formatted for JDBC
        """
        # Column selection
        col_str = ", ".join(columns) if columns else "*"
        
        # Build query
        query = f"(SELECT {col_str} FROM {table_name.upper()}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        query += f") {table_name}_query"
        
        return query


# Example usage and testing
if __name__ == "__main__":
    """
    Example usage of OracleExtractor.
    
    Prerequisites:
    - Oracle database running with HR schema
    - Environment variables set in .env file
    - ojdbc8.jar in Spark classpath
    """
    from config import get_oracle_config
    
    print("=" * 80)
    print("Oracle Extractor - Example Usage")
    print("=" * 80)
    
    try:
        # Initialize extractor
        config = get_oracle_config()
        extractor = OracleExtractor(config)
        
        print("\n1. Validating connection...")
        if extractor.validate_connection():
            print("✅ Connection validated successfully")
        
        print("\n2. Getting table counts...")
        counts = extractor.get_all_table_counts()
        for table, count in counts.items():
            print(f"   {table:15} : {count:>6} rows")
        
        print("\n3. Extracting regions table...")
        regions_df = extractor.extract_regions()
        print(f"✅ Extracted {regions_df.count()} regions")
        regions_df.show()
        
        print("\n4. Extracting employees (first 10)...")
        employees_df = extractor.extract_employees()
        print(f"✅ Extracted {employees_df.count()} employees")
        employees_df.show(10)
        
        print("\n5. Extracting departments with NULL manager_id...")
        null_mgr_depts = extractor.extract_departments(include_null_managers=False)
        print(f"✅ Found {null_mgr_depts.count()} departments with NULL manager_id")
        null_mgr_depts.show()
        
        print("\n6. Extracting multiple tables...")
        tables = extractor.extract_all_tables(tables=["regions", "countries", "jobs"])
        for table, df in tables.items():
            print(f"   {table:15} : {df.count()} rows")
        
        print("\n7. Metrics Report:")
        print(extractor.metrics.generate_report())
        
        print("\n" + "=" * 80)
        print("✅ All extractions completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

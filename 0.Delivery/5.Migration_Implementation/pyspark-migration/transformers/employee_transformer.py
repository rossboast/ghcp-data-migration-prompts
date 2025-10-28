"""
Employee Transformer

Complex transformer for denormalizing employee data from Oracle HR schema.
Performs 6-way joins and embeds related data to create rich employee documents.

Features:
- 6-way join: employees → departments → jobs → locations → countries → regions
- Manager details embedding (self-join on employees)
- Job history aggregation
- Synthetic partition key calculation
- Complete denormalization for Cosmos DB

Usage:
    from transformers import EmployeeTransformer
    
    transformer = EmployeeTransformer()
    
    # Transform all employees
    employee_docs = transformer.transform(
        employees_df,
        departments_df,
        jobs_df,
        locations_df,
        countries_df,
        regions_df,
        job_history_df
    )
"""

from typing import Optional, Any
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, struct, array, collect_list, concat, lit, 
    when, coalesce, expr, current_timestamp, hash
)
from pyspark.sql.window import Window

from transformers.base_transformer import BaseTransformer
from transformers.data_type_converter import DataTypeConverter
from transformers.common_transformations import CommonTransformations
from utils.logging_config import get_logger
from utils.metrics import MetricsCollector, MigrationMetrics

class EmployeeTransformer(BaseTransformer):
    """
    Transform employee data with complex denormalization.
    
    Performs:
    1. Convert Oracle types to JSON-compatible types
    2. 6-way join to denormalize employee data
    3. Embed manager details (self-join)
    4. Aggregate job history
    5. Calculate synthetic partition key
    6. Add metadata
    7. Create final document structure
    """
    
    def __init__(
        self,
        partition_key_formula: str = "dept_{department_id}_{employee_id % 10}",
        include_manager_details: bool = True,
        include_job_history: bool = True,
        logger: Optional[Any] = None,
        metrics: Optional[MetricsCollector] = None
    ):
        """
        Initialize employee transformer.
        
        Args:
            partition_key_formula: Formula for partition key calculation
            include_manager_details: Whether to embed manager details
            include_job_history: Whether to aggregate job history
            logger: Optional logger instance
            metrics: Optional metrics collector
        """
        super().__init__(
            name="employee_transformer",
            logger=logger or get_logger("employee_transformer"),
            metrics=metrics or MigrationMetrics(feed_name="employee_transformer")
        )
        
        self.partition_key_formula = partition_key_formula
        self.include_manager_details = include_manager_details
        self.include_job_history = include_job_history
        
        self.logger.info(
            "Employee transformer initialized",
            partition_key_formula=partition_key_formula,
            include_manager_details=include_manager_details,
            include_job_history=include_job_history
        )
    
    def validate_input(self, df: DataFrame) -> bool:
        """
        Validate input DataFrame has required columns.
        
        Args:
            df: Input DataFrame
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        required_columns = [
            "employee_id", "first_name", "last_name", "email",
            "hire_date", "job_id", "salary", "department_id"
        ]
        
        missing = [col for col in required_columns if col not in df.columns]
        
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        return True
    
    def transform(
        self,
        employees_df: DataFrame,
        departments_df: DataFrame,
        jobs_df: DataFrame,
        locations_df: DataFrame,
        countries_df: DataFrame,
        regions_df: DataFrame,
        job_history_df: Optional[DataFrame] = None
    ) -> DataFrame:
        """
        Transform employee data with full denormalization.
        
        Args:
            employees_df: Employees table
            departments_df: Departments table
            jobs_df: Jobs table
            locations_df: Locations table
            countries_df: Countries table
            regions_df: Regions table
            job_history_df: Job history table (optional)
            
        Returns:
            Transformed DataFrame with denormalized employee documents
        """
        self.logger.info("Starting employee transformation")
        
        # Validate input
        self.validate_input(employees_df)
        
        # Step 1: Convert Oracle types to JSON
        self.logger.info("Step 1: Converting Oracle types to JSON")
        employees_df = DataTypeConverter.convert_oracle_to_json_types(employees_df)
        departments_df = DataTypeConverter.convert_oracle_to_json_types(departments_df)
        jobs_df = DataTypeConverter.convert_oracle_to_json_types(jobs_df)
        locations_df = DataTypeConverter.convert_oracle_to_json_types(locations_df)
        countries_df = DataTypeConverter.convert_oracle_to_json_types(countries_df)
        regions_df = DataTypeConverter.convert_oracle_to_json_types(regions_df)
        if job_history_df is not None:
            job_history_df = DataTypeConverter.convert_oracle_to_json_types(job_history_df)
        
        # Step 2: Denormalize with 6-way join
        self.logger.info("Step 2: Performing 6-way join denormalization")
        result_df = self._denormalize_employee_data(
            employees_df,
            departments_df,
            jobs_df,
            locations_df,
            countries_df,
            regions_df
        )
        
        # Step 3: Add manager details (self-join)
        if self.include_manager_details:
            self.logger.info("Step 3: Adding manager details")
            result_df = self._add_manager_details(result_df, employees_df)
        
        # Step 4: Aggregate job history
        if self.include_job_history and job_history_df is not None:
            self.logger.info("Step 4: Aggregating job history")
            result_df = self._add_job_history(result_df, job_history_df, jobs_df, departments_df)
        
        # Step 5: Calculate partition key
        self.logger.info("Step 5: Calculating partition key")
        result_df = CommonTransformations.add_partition_key(
            result_df,
            key_formula=self.partition_key_formula
        )
        
        # Step 6: Add document ID
        self.logger.info("Step 6: Adding document ID")
        result_df = CommonTransformations.add_document_id(
            result_df,
            id_column="employee_id",
            prefix="emp_"
        )
        
        # Step 7: Add metadata
        self.logger.info("Step 7: Adding metadata")
        result_df = CommonTransformations.add_metadata(
            result_df,
            source="oracle_hr",
            entity_type="employee"
        )
        
        # Step 8: Create final document structure
        self.logger.info("Step 8: Creating final document structure")
        result_df = self._create_document_structure(result_df)
        
        count = result_df.count()
        self.logger.info(
            "Employee transformation completed",
            record_count=count
        )
        
        return result_df
    
    def _denormalize_employee_data(
        self,
        employees_df: DataFrame,
        departments_df: DataFrame,
        jobs_df: DataFrame,
        locations_df: DataFrame,
        countries_df: DataFrame,
        regions_df: DataFrame
    ) -> DataFrame:
        """
        Perform 6-way join to denormalize employee data.
        
        Join order:
        employees → departments → locations → countries → regions
        employees → jobs
        """
        # Join employees with departments
        result_df = employees_df.alias("emp").join(
            departments_df.alias("dept"),
            col("emp.department_id") == col("dept.department_id"),
            "left"
        ).select(
            # Employee fields
            col("emp.employee_id"),
            col("emp.first_name"),
            col("emp.last_name"),
            col("emp.email"),
            col("emp.phone_number"),
            col("emp.hire_date"),
            col("emp.salary"),
            col("emp.commission_pct"),
            col("emp.manager_id"),
            col("emp.job_id"),
            col("emp.department_id"),
            # Department fields
            struct(
                col("dept.department_id").alias("department_id"),
                col("dept.department_name").alias("department_name"),
                col("dept.manager_id").alias("manager_id")
            ).alias("department")
        )
        
        # Join with jobs
        result_df = result_df.alias("emp").join(
            jobs_df.alias("job"),
            col("emp.job_id") == col("job.job_id"),
            "left"
        ).select(
            col("emp.*"),
            struct(
                col("job.job_id").alias("job_id"),
                col("job.job_title").alias("job_title"),
                col("job.min_salary").alias("min_salary"),
                col("job.max_salary").alias("max_salary")
            ).alias("job")
        )
        
        # Join departments with locations
        dept_loc_df = departments_df.alias("dept").join(
            locations_df.alias("loc"),
            col("dept.location_id") == col("loc.location_id"),
            "left"
        ).select(
            col("dept.department_id"),
            struct(
                col("loc.location_id").alias("location_id"),
                col("loc.street_address").alias("street_address"),
                col("loc.postal_code").alias("postal_code"),
                col("loc.city").alias("city"),
                col("loc.state_province").alias("state_province"),
                col("loc.country_id").alias("country_id")
            ).alias("location")
        )
        
        # Join with location
        result_df = result_df.alias("emp").join(
            dept_loc_df.alias("dept_loc"),
            col("emp.department_id") == col("dept_loc.department_id"),
            "left"
        ).select(
            col("emp.*"),
            col("dept_loc.location")
        )
        
        # Join locations with countries
        loc_country_df = locations_df.alias("loc").join(
            countries_df.alias("country"),
            col("loc.country_id") == col("country.country_id"),
            "left"
        ).select(
            col("loc.location_id"),
            struct(
                col("country.country_id").alias("country_id"),
                col("country.country_name").alias("country_name"),
                col("country.region_id").alias("region_id")
            ).alias("country")
        )
        
        # Join with country
        result_df = result_df.alias("emp").join(
            loc_country_df.alias("loc_country"),
            col("emp.location.location_id") == col("loc_country.location_id"),
            "left"
        ).select(
            col("emp.*"),
            col("loc_country.country")
        )
        
        # Join countries with regions
        country_region_df = countries_df.alias("country").join(
            regions_df.alias("region"),
            col("country.region_id") == col("region.region_id"),
            "left"
        ).select(
            col("country.country_id"),
            struct(
                col("region.region_id").alias("region_id"),
                col("region.region_name").alias("region_name")
            ).alias("region")
        )
        
        # Join with region
        result_df = result_df.alias("emp").join(
            country_region_df.alias("country_region"),
            col("emp.country.country_id") == col("country_region.country_id"),
            "left"
        ).select(
            col("emp.*"),
            col("country_region.region")
        )
        
        return result_df
    
    def _add_manager_details(
        self,
        employees_df: DataFrame,
        managers_df: DataFrame
    ) -> DataFrame:
        """
        Add manager details via self-join.
        
        Args:
            employees_df: Employee DataFrame
            managers_df: Manager DataFrame (same as employees)
            
        Returns:
            DataFrame with manager details embedded
        """
        # Prepare manager data
        manager_details = managers_df.select(
            col("employee_id").alias("mgr_employee_id"),
            col("first_name").alias("mgr_first_name"),
            col("last_name").alias("mgr_last_name"),
            col("email").alias("mgr_email"),
            col("job_id").alias("mgr_job_id")
        )
        
        # Join with manager details
        result_df = employees_df.alias("emp").join(
            manager_details.alias("mgr"),
            col("emp.manager_id") == col("mgr.mgr_employee_id"),
            "left"
        ).select(
            col("emp.*"),
            when(
                col("mgr.mgr_employee_id").isNotNull(),
                struct(
                    col("mgr.mgr_employee_id").alias("employee_id"),
                    col("mgr.mgr_first_name").alias("first_name"),
                    col("mgr.mgr_last_name").alias("last_name"),
                    col("mgr.mgr_email").alias("email"),
                    col("mgr.mgr_job_id").alias("job_id")
                )
            ).alias("manager")
        )
        
        return result_df
    
    def _add_job_history(
        self,
        employees_df: DataFrame,
        job_history_df: DataFrame,
        jobs_df: DataFrame,
        departments_df: DataFrame
    ) -> DataFrame:
        """
        Aggregate job history for each employee.
        
        Args:
            employees_df: Employee DataFrame
            job_history_df: Job history DataFrame
            jobs_df: Jobs DataFrame (for job titles)
            departments_df: Departments DataFrame (for dept names)
            
        Returns:
            DataFrame with job history array
        """
        # Enrich job history with job titles and department names
        enriched_history = job_history_df.alias("hist") \
            .join(
                jobs_df.alias("job"),
                col("hist.job_id") == col("job.job_id"),
                "left"
            ) \
            .join(
                departments_df.alias("dept"),
                col("hist.department_id") == col("dept.department_id"),
                "left"
            ) \
            .select(
                col("hist.employee_id"),
                struct(
                    col("hist.start_date").alias("start_date"),
                    col("hist.end_date").alias("end_date"),
                    col("hist.job_id").alias("job_id"),
                    col("job.job_title").alias("job_title"),
                    col("hist.department_id").alias("department_id"),
                    col("dept.department_name").alias("department_name")
                ).alias("history_entry")
            )
        
        # Aggregate by employee
        # Order by start_date (most recent first)
        window = Window.partitionBy("employee_id").orderBy(col("history_entry.start_date").desc())
        
        aggregated_history = enriched_history \
            .groupBy("employee_id") \
            .agg(
                collect_list("history_entry").alias("job_history")
            )
        
        # Join with employees
        result_df = employees_df.alias("emp").join(
            aggregated_history.alias("hist"),
            col("emp.employee_id") == col("hist.employee_id"),
            "left"
        ).select(
            col("emp.*"),
            coalesce(col("hist.job_history"), array().cast("array<struct<start_date:string,end_date:string,job_id:string,job_title:string,department_id:int,department_name:string>>")).alias("job_history")
        )
        
        return result_df
    
    def _create_document_structure(self, df: DataFrame) -> DataFrame:
        """
        Create final Cosmos DB document structure.
        
        Organizes fields into logical groupings for cleaner documents.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with final document structure
        """
        # Select and organize fields
        result_df = df.select(
            # Required Cosmos fields
            col("id"),
            col("partitionKey"),
            
            # Core employee fields
            col("employee_id"),
            col("first_name"),
            col("last_name"),
            col("email"),
            col("phone_number"),
            col("hire_date"),
            
            # Employment details
            col("salary"),
            col("commission_pct"),
            
            # Relationships
            col("manager_id"),
            col("manager"),
            
            # Job details (embedded)
            col("job"),
            
            # Department details (embedded)
            col("department"),
            
            # Location details (embedded)
            col("location"),
            
            # Country details (embedded)
            col("country"),
            
            # Region details (embedded)
            col("region"),
            
            # Job history (array)
            col("job_history") if "job_history" in df.columns else array().alias("job_history"),
            
            # Metadata
            col("metadata")
        )
        
        return result_df


# Example usage
if __name__ == "__main__":
    """
    Example usage of EmployeeTransformer.
    
    Prerequisites:
    - Oracle database with HR schema
    - All reference tables loaded
    """
    from pyspark.sql import SparkSession
    from extractors import OracleExtractor
    from config import get_oracle_config
    
    print("=" * 80)
    print("Employee Transformer - Example Usage")
    print("=" * 80)
    
    try:
        # Initialize
        oracle_config = get_oracle_config()
        extractor = OracleExtractor(oracle_config)
        transformer = EmployeeTransformer()
        
        print("\n1. Extracting data from Oracle...")
        
        # Extract all required tables
        employees_df = extractor.extract_employees()
        departments_df = extractor.extract_departments()
        jobs_df = extractor.extract_jobs()
        locations_df = extractor.extract_locations()
        countries_df = extractor.extract_countries()
        regions_df = extractor.extract_regions()
        job_history_df = extractor.extract_job_history()
        
        print(f"✅ Extracted data:")
        print(f"   - Employees: {employees_df.count()}")
        print(f"   - Departments: {departments_df.count()}")
        print(f"   - Jobs: {jobs_df.count()}")
        print(f"   - Locations: {locations_df.count()}")
        print(f"   - Countries: {countries_df.count()}")
        print(f"   - Regions: {regions_df.count()}")
        print(f"   - Job History: {job_history_df.count()}")
        
        print("\n2. Transforming employee data...")
        
        # Transform
        employee_docs = transformer.transform_with_metrics(
            employees_df,
            departments_df,
            jobs_df,
            locations_df,
            countries_df,
            regions_df,
            job_history_df
        )
        
        print(f"✅ Transformed {employee_docs.count()} employee documents")
        
        print("\n3. Sample transformed document:")
        employee_docs.show(1, vertical=True, truncate=False)
        
        print("\n4. Document schema:")
        employee_docs.printSchema()
        
        print("\n5. Metrics Report:")
        print(transformer.metrics.generate_report())
        
        print("\n" + "=" * 80)
        print("✅ Transformation completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

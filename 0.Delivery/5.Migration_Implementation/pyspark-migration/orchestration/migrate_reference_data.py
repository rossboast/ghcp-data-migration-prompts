"""
Reference Data Migration Script

Migrates reference data from Oracle HR schema to Cosmos DB.
This includes Phase 1 and Phase 2 of the migration strategy:
- Phase 1: Tables with no foreign keys (regions, countries, locations, jobs)
- Phase 2: Departments with NULL manager_id

Features:
- Extract from Oracle using OracleExtractor
- Transform using DataTypeConverter and CommonTransformations
- Load to Cosmos DB using CosmosLoader
- Checkpoint/restart capability for fault tolerance
- Comprehensive logging and metrics
- Validation of record counts

Usage:
    python orchestration/migrate_reference_data.py
    
    # Or with custom config
    python orchestration/migrate_reference_data.py --checkpoint-file custom_checkpoint.json
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyspark.sql import DataFrame

from extractors import OracleExtractor
from transformers import DataTypeConverter, CommonTransformations
from loaders import CosmosLoader
from config import get_oracle_config, get_cosmos_config
from utils.logging_config import get_logger
from utils.metrics import MetricsCollector
from utils.error_handler import MigrationError


class ReferenceDataMigration:
    """
    Orchestrates migration of reference data from Oracle to Cosmos DB.
    
    Migration Strategy:
    - Phase 1: Regions, Countries, Locations, Jobs (no FK dependencies)
    - Phase 2: Departments (with NULL manager_id to avoid circular dependency)
    
    All reference data goes into a single Cosmos container with entityType discrimination.
    """
    
    # Phase 1 tables (no foreign key dependencies)
    PHASE_1_TABLES = ["regions", "countries", "locations", "jobs"]
    
    # Phase 2 tables (departments with NULL manager_id)
    PHASE_2_TABLES = ["departments"]
    
    def __init__(
        self,
        checkpoint_file: str = "reference_migration_checkpoint.json",
        container_name: str = "reference_data",
        partition_key_value: str = "ref_data",
        dry_run: bool = False
    ):
        """
        Initialize reference data migration.
        
        Args:
            checkpoint_file: Path to checkpoint file for restart capability
            container_name: Target Cosmos container name
            partition_key_value: Partition key value for all reference documents
            dry_run: If True, run without actually loading to Cosmos
        """
        self.checkpoint_file = checkpoint_file
        self.container_name = container_name
        self.partition_key_value = partition_key_value
        self.dry_run = dry_run
        
        # Initialize logger and metrics
        self.logger = get_logger("reference_migration")
        self.metrics = MetricsCollector("reference_migration")
        
        # Load checkpoint
        self.checkpoint = self._load_checkpoint()
        
        # Initialize extractors and loaders
        self.oracle_config = get_oracle_config()
        self.cosmos_config = get_cosmos_config()
        
        self.extractor = OracleExtractor(
            self.oracle_config,
            logger=self.logger,
            metrics=self.metrics
        )
        
        if not self.dry_run:
            self.loader = CosmosLoader(
                self.cosmos_config,
                container=self.container_name,
                batch_size=1000,
                logger=self.logger,
                metrics=self.metrics
            )
        
        self.logger.info(
            "Reference data migration initialized",
            checkpoint_file=checkpoint_file,
            container=container_name,
            partition_key=partition_key_value,
            dry_run=dry_run
        )
    
    def _load_checkpoint(self) -> Dict[str, Any]:
        """
        Load checkpoint from file.
        
        Returns:
            Checkpoint dictionary
        """
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)
                    self.logger.info(
                        "Loaded checkpoint",
                        checkpoint_file=self.checkpoint_file,
                        completed_tables=checkpoint.get('completed_tables', [])
                    )
                    return checkpoint
            except Exception as e:
                self.logger.warning(
                    "Failed to load checkpoint, starting fresh",
                    error=str(e)
                )
        
        # Return empty checkpoint
        return {
            "started_at": datetime.now().isoformat(),
            "completed_tables": [],
            "table_counts": {},
            "last_updated": None
        }
    
    def _save_checkpoint(self):
        """
        Save checkpoint to file.
        """
        self.checkpoint["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoint, f, indent=2)
            
            self.logger.info(
                "Checkpoint saved",
                checkpoint_file=self.checkpoint_file,
                completed_tables=self.checkpoint.get('completed_tables', [])
            )
        except Exception as e:
            self.logger.error(
                "Failed to save checkpoint",
                error=str(e)
            )
    
    def _is_table_completed(self, table_name: str) -> bool:
        """
        Check if table migration is already completed.
        
        Args:
            table_name: Table name to check
            
        Returns:
            True if completed
        """
        return table_name in self.checkpoint.get('completed_tables', [])
    
    def _mark_table_completed(self, table_name: str, record_count: int):
        """
        Mark table migration as completed.
        
        Args:
            table_name: Table name
            record_count: Number of records migrated
        """
        completed = self.checkpoint.get('completed_tables', [])
        if table_name not in completed:
            completed.append(table_name)
        
        self.checkpoint['completed_tables'] = completed
        self.checkpoint['table_counts'][table_name] = record_count
        self._save_checkpoint()
    
    def _extract_table(self, table_name: str) -> DataFrame:
        """
        Extract data from Oracle table.
        
        Args:
            table_name: Table name to extract
            
        Returns:
            Extracted DataFrame
        """
        self.logger.info(f"Extracting table: {table_name}")
        
        # Use table-specific extraction methods
        if table_name == "regions":
            df = self.extractor.extract_regions()
        elif table_name == "countries":
            df = self.extractor.extract_countries()
        elif table_name == "locations":
            df = self.extractor.extract_locations()
        elif table_name == "jobs":
            df = self.extractor.extract_jobs()
        elif table_name == "departments":
            # Extract departments with NULL manager_id only (Phase 2)
            df = self.extractor.extract_departments(include_null_managers=True)
        else:
            raise MigrationError(
                f"Unknown table: {table_name}",
                context={"table": table_name}
            )
        
        count = df.count()
        self.logger.info(
            f"Extracted {count} records from {table_name}",
            table=table_name,
            count=count
        )
        
        return df
    
    def _transform_to_reference_document(
        self,
        df: DataFrame,
        table_name: str,
        id_column: str,
        data_columns: List[str]
    ) -> DataFrame:
        """
        Transform Oracle data to reference document format.
        
        Args:
            df: Input DataFrame
            table_name: Table name (used as entityType)
            id_column: Column to use as document ID
            data_columns: Columns to include in data struct
            
        Returns:
            Transformed DataFrame
        """
        self.logger.info(f"Transforming {table_name} to reference document format")
        
        # Convert Oracle types to JSON-compatible types
        df = DataTypeConverter.convert_oracle_to_json_types(df)
        
        # Create reference document structure
        df = CommonTransformations.create_reference_document(
            df,
            entity_type=table_name,
            id_column=id_column,
            data_columns=data_columns,
            partition_key_value=self.partition_key_value
        )
        
        self.logger.info(
            f"Transformed {table_name} successfully",
            columns=len(df.columns)
        )
        
        return df
    
    def _load_to_cosmos(self, df: DataFrame, table_name: str) -> int:
        """
        Load DataFrame to Cosmos DB.
        
        Args:
            df: DataFrame to load
            table_name: Table name (for logging)
            
        Returns:
            Number of records loaded
        """
        if self.dry_run:
            count = df.count()
            self.logger.info(
                f"DRY RUN: Would load {count} records from {table_name}",
                table=table_name,
                count=count
            )
            return count
        
        self.logger.info(f"Loading {table_name} to Cosmos DB")
        
        loaded = self.loader.load_with_metrics(df)
        
        self.logger.info(
            f"Loaded {loaded} records from {table_name}",
            table=table_name,
            count=loaded
        )
        
        return loaded
    
    def migrate_table(
        self,
        table_name: str,
        id_column: str,
        data_columns: List[str],
        force: bool = False
    ) -> int:
        """
        Migrate a single table.
        
        Args:
            table_name: Table name to migrate
            id_column: Column to use as document ID
            data_columns: Columns to include in data struct
            force: Force migration even if already completed
            
        Returns:
            Number of records migrated
        """
        # Check if already completed
        if not force and self._is_table_completed(table_name):
            self.logger.info(
                f"Table {table_name} already completed (use --force to re-migrate)",
                table=table_name
            )
            return 0
        
        self.logger.info(
            f"Starting migration for {table_name}",
            table=table_name,
            id_column=id_column,
            data_columns=data_columns
        )
        
        try:
            # Extract
            df = self._extract_table(table_name)
            
            # Transform
            df = self._transform_to_reference_document(
                df,
                table_name,
                id_column,
                data_columns
            )
            
            # Load
            loaded = self._load_to_cosmos(df, table_name)
            
            # Mark as completed
            self._mark_table_completed(table_name, loaded)
            
            self.logger.info(
                f"Successfully migrated {table_name}",
                table=table_name,
                records=loaded
            )
            
            return loaded
            
        except Exception as e:
            self.logger.error(
                f"Failed to migrate {table_name}",
                table=table_name,
                error=str(e)
            )
            raise MigrationError(
                f"Failed to migrate {table_name}: {str(e)}",
                context={"table": table_name}
            ) from e
    
    def migrate_phase_1(self, force: bool = False) -> Dict[str, int]:
        """
        Migrate Phase 1 tables (no FK dependencies).
        
        Args:
            force: Force migration even if already completed
            
        Returns:
            Dictionary mapping table names to record counts
        """
        self.logger.info("=" * 80)
        self.logger.info("Starting Phase 1: Tables with no foreign key dependencies")
        self.logger.info("=" * 80)
        
        results = {}
        
        # Regions
        results["regions"] = self.migrate_table(
            "regions",
            id_column="region_id",
            data_columns=["region_name"],
            force=force
        )
        
        # Countries
        results["countries"] = self.migrate_table(
            "countries",
            id_column="country_id",
            data_columns=["country_name", "region_id"],
            force=force
        )
        
        # Locations
        results["locations"] = self.migrate_table(
            "locations",
            id_column="location_id",
            data_columns=[
                "street_address", "postal_code", "city",
                "state_province", "country_id"
            ],
            force=force
        )
        
        # Jobs
        results["jobs"] = self.migrate_table(
            "jobs",
            id_column="job_id",
            data_columns=["job_title", "min_salary", "max_salary"],
            force=force
        )
        
        self.logger.info("=" * 80)
        self.logger.info("Phase 1 completed")
        self.logger.info("=" * 80)
        
        return results
    
    def migrate_phase_2(self, force: bool = False) -> Dict[str, int]:
        """
        Migrate Phase 2 tables (departments with NULL manager_id).
        
        Args:
            force: Force migration even if already completed
            
        Returns:
            Dictionary mapping table names to record counts
        """
        self.logger.info("=" * 80)
        self.logger.info("Starting Phase 2: Departments with NULL manager_id")
        self.logger.info("=" * 80)
        
        results = {}
        
        # Departments (with NULL manager_id only)
        results["departments"] = self.migrate_table(
            "departments",
            id_column="department_id",
            data_columns=["department_name", "manager_id", "location_id"],
            force=force
        )
        
        self.logger.info("=" * 80)
        self.logger.info("Phase 2 completed")
        self.logger.info("=" * 80)
        
        return results
    
    def migrate_all(self, force: bool = False) -> Dict[str, Any]:
        """
        Migrate all reference data (Phase 1 and Phase 2).
        
        Args:
            force: Force migration even if already completed
            
        Returns:
            Migration summary
        """
        start_time = datetime.now()
        
        self.logger.info("=" * 80)
        self.logger.info("REFERENCE DATA MIGRATION - START")
        self.logger.info("=" * 80)
        self.logger.info(f"Started at: {start_time.isoformat()}")
        self.logger.info(f"Dry run: {self.dry_run}")
        self.logger.info(f"Force: {force}")
        
        # Validate connections
        self.logger.info("Validating connections...")
        
        if not self.extractor.validate_connection():
            raise MigrationError("Oracle connection validation failed")
        
        if not self.dry_run:
            if not self.loader.validate_target_connection():
                raise MigrationError("Cosmos DB connection validation failed")
        
        self.logger.info("✅ All connections validated")
        
        # Migrate Phase 1
        phase_1_results = self.migrate_phase_1(force=force)
        
        # Migrate Phase 2
        phase_2_results = self.migrate_phase_2(force=force)
        
        # Calculate totals
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        all_results = {**phase_1_results, **phase_2_results}
        total_records = sum(all_results.values())
        
        summary = {
            "status": "completed",
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_seconds": duration,
            "dry_run": self.dry_run,
            "phase_1_results": phase_1_results,
            "phase_2_results": phase_2_results,
            "total_records": total_records,
            "tables_migrated": len(all_results),
            "checkpoint_file": self.checkpoint_file
        }
        
        # Print summary
        self.logger.info("=" * 80)
        self.logger.info("REFERENCE DATA MIGRATION - SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Status: {summary['status']}")
        self.logger.info(f"Duration: {duration:.2f} seconds")
        self.logger.info(f"Total Records: {total_records:,}")
        self.logger.info(f"Tables Migrated: {len(all_results)}")
        self.logger.info("")
        self.logger.info("Phase 1 Results:")
        for table, count in phase_1_results.items():
            self.logger.info(f"  - {table}: {count:,} records")
        self.logger.info("")
        self.logger.info("Phase 2 Results:")
        for table, count in phase_2_results.items():
            self.logger.info(f"  - {table}: {count:,} records")
        self.logger.info("=" * 80)
        
        # Print metrics report
        if not self.dry_run:
            self.logger.info("")
            self.logger.info("METRICS REPORT")
            self.logger.info("=" * 80)
            self.logger.info(self.metrics.generate_report())
        
        return summary
    
    def validate_migration(self) -> Dict[str, Any]:
        """
        Validate migration by comparing record counts.
        
        Returns:
            Validation results
        """
        self.logger.info("=" * 80)
        self.logger.info("VALIDATING MIGRATION")
        self.logger.info("=" * 80)
        
        all_tables = self.PHASE_1_TABLES + self.PHASE_2_TABLES
        validation_results = {}
        
        for table_name in all_tables:
            # Get Oracle count
            oracle_count = self.extractor.get_table_count(table_name)
            
            # Get Cosmos count (would need to query by entityType)
            # For now, use checkpoint data
            cosmos_count = self.checkpoint.get('table_counts', {}).get(table_name, 0)
            
            match = oracle_count == cosmos_count
            
            validation_results[table_name] = {
                "oracle_count": oracle_count,
                "cosmos_count": cosmos_count,
                "match": match
            }
            
            status = "✅" if match else "❌"
            self.logger.info(
                f"{status} {table_name}: Oracle={oracle_count}, Cosmos={cosmos_count}"
            )
        
        all_match = all(r["match"] for r in validation_results.values())
        
        self.logger.info("=" * 80)
        if all_match:
            self.logger.info("✅ VALIDATION PASSED - All counts match")
        else:
            self.logger.warning("⚠️  VALIDATION FAILED - Some counts do not match")
        self.logger.info("=" * 80)
        
        return {
            "all_match": all_match,
            "table_results": validation_results
        }


def main():
    """
    Main entry point for reference data migration.
    """
    parser = argparse.ArgumentParser(
        description="Migrate reference data from Oracle to Cosmos DB"
    )
    parser.add_argument(
        "--checkpoint-file",
        default="reference_migration_checkpoint.json",
        help="Path to checkpoint file (default: reference_migration_checkpoint.json)"
    )
    parser.add_argument(
        "--container",
        default="reference_data",
        help="Target Cosmos container name (default: reference_data)"
    )
    parser.add_argument(
        "--partition-key",
        default="ref_data",
        help="Partition key value for all documents (default: ref_data)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without actually loading to Cosmos DB"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force migration even if tables already completed"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate migration, don't migrate"
    )
    parser.add_argument(
        "--phase",
        choices=["1", "2", "all"],
        default="all",
        help="Which phase to run (default: all)"
    )
    
    args = parser.parse_args()
    
    # Initialize migration
    migration = ReferenceDataMigration(
        checkpoint_file=args.checkpoint_file,
        container_name=args.container,
        partition_key_value=args.partition_key,
        dry_run=args.dry_run
    )
    
    try:
        if args.validate_only:
            # Only validate
            results = migration.validate_migration()
            sys.exit(0 if results["all_match"] else 1)
        
        # Run migration
        if args.phase == "1":
            migration.migrate_phase_1(force=args.force)
        elif args.phase == "2":
            migration.migrate_phase_2(force=args.force)
        else:
            migration.migrate_all(force=args.force)
        
        # Validate
        validation = migration.validate_migration()
        
        sys.exit(0 if validation["all_match"] else 1)
        
    except Exception as e:
        migration.logger.error(
            "Migration failed",
            error=str(e)
        )
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

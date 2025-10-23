"""
Employee Data Migration Script

Orchestrates Phase 3-4 migration of employee data from Oracle to Cosmos DB.
Implements complex denormalization with 6-way joins and circular dependency resolution.

Phases:
- Phase 3: Migrate employee documents with full denormalization
- Phase 4: Resolve circular department.manager_id references

Usage:
    # Migrate all phases
    python orchestration/migrate_employees.py --phase all
    
    # Dry run (no actual loading)
    python orchestration/migrate_employees.py --phase 3 --dry-run
    
    # Force re-migration
    python orchestration/migrate_employees.py --force
    
    # Validate only
    python orchestration/migrate_employees.py --validate-only
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from pyspark.sql import DataFrame

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from extractors.oracle_extractor import OracleExtractor
from transformers.employee_transformer import EmployeeTransformer
from transformers.data_type_converter import DataTypeConverter
from transformers.common_transformations import CommonTransformations
from validators.field_validator import FieldValidator
from validators.record_validator import RecordValidator
from validators.business_rule_validator import BusinessRuleValidator
from loaders.cosmos_loader import CosmosLoader
from config.connections import OracleConnectionConfig, CosmosDBConnectionConfig
from utils.logging_config import get_logger
from utils.error_handler import MigrationError


class EmployeeMigration:
    """
    Orchestrate employee data migration from Oracle to Cosmos DB.
    
    Handles complex denormalization and circular dependency resolution.
    """
    
    def __init__(
        self,
        checkpoint_file: str = "employee_migration_checkpoint.json",
        container_name: str = "employees",
        dry_run: bool = False
    ):
        """
        Initialize employee migration.
        
        Args:
            checkpoint_file: Path to checkpoint file
            container_name: Cosmos container name
            dry_run: If True, skip actual loading
        """
        self.logger = get_logger("employee_migration")
        self.checkpoint_file = checkpoint_file
        self.container_name = container_name
        self.dry_run = dry_run
        
        # Initialize components
        self.extractor = OracleExtractor(OracleConnectionConfig())
        self.transformer = EmployeeTransformer(
            partition_key_formula="dept_{department_id}_{employee_id % 10}",
            include_manager_details=True,
            include_job_history=True
        )
        
        # Initialize validators
        self.field_validator = FieldValidator(
            validation_rules={
                "employee_id": ["NOT_NULL", "POSITIVE"],
                "first_name": ["NOT_NULL", "LENGTH_MIN:1", "LENGTH_MAX:50"],
                "last_name": ["NOT_NULL", "LENGTH_MIN:1", "LENGTH_MAX:50"],
                "email": ["NOT_NULL", "EMAIL_FORMAT"],
                "hire_date": ["NOT_NULL", "DATE_RANGE:1990-01-01:2030-12-31"],
                "job_id": ["NOT_NULL"],
                "salary": ["NOT_NULL", "POSITIVE", "SALARY_RANGE:1000:100000"],
                "phone_number": ["PHONE_FORMAT"],
                "commission_pct": ["NON_NEGATIVE"],
            }
        )
        self.record_validator = RecordValidator()
        self.business_validator = BusinessRuleValidator()
        
        # Initialize loader
        if not dry_run:
            cosmos_config = CosmosDBConnectionConfig()
            self.loader = CosmosLoader(
                config=cosmos_config,
                container=container_name,
                batch_size=1000,
                write_mode="append"
            )
        else:
            self.loader = None
        
        # Load checkpoint
        self.checkpoint = self._load_checkpoint()
        
        self.logger.info(
            "Employee migration initialized",
            checkpoint_file=checkpoint_file,
            container=container_name,
            dry_run=dry_run
        )
    
    def _load_checkpoint(self) -> Dict:
        """Load checkpoint from file."""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                self.logger.info(
                    "Loaded checkpoint",
                    completed_phases=checkpoint.get("completed_phases", [])
                )
                return checkpoint
        return {
            "started_at": datetime.now().isoformat(),
            "completed_phases": [],
            "phase_details": {},
            "last_updated": None
        }
    
    def _save_checkpoint(self):
        """Save checkpoint to file."""
        self.checkpoint["last_updated"] = datetime.now().isoformat()
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)
        self.logger.debug("Checkpoint saved")
    
    def _is_phase_completed(self, phase: str) -> bool:
        """Check if phase is completed."""
        return phase in self.checkpoint.get("completed_phases", [])
    
    def _mark_phase_completed(self, phase: str, details: Dict):
        """Mark phase as completed."""
        if phase not in self.checkpoint.get("completed_phases", []):
            self.checkpoint["completed_phases"].append(phase)
        self.checkpoint["phase_details"][phase] = details
        self._save_checkpoint()
    
    def migrate_phase_3(self, force: bool = False) -> Dict:
        """
        Migrate Phase 3: Employee documents with full denormalization.
        
        Args:
            force: If True, re-migrate even if completed
            
        Returns:
            Dictionary with migration details
        """
        phase = "phase_3"
        
        if self._is_phase_completed(phase) and not force:
            self.logger.info("Phase 3 already completed (use --force to re-run)")
            return self.checkpoint["phase_details"][phase]
        
        self.logger.info("=" * 80)
        self.logger.info("Starting Phase 3: Employee Migration")
        self.logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # Extract all required tables
            self.logger.info("Extracting data from Oracle...")
            
            employees_df = self.extractor.extract_employees()
            departments_df = self.extractor.extract_departments()
            jobs_df = self.extractor.extract_jobs()
            locations_df = self.extractor.extract_locations()
            countries_df = self.extractor.extract_countries()
            regions_df = self.extractor.extract_regions()
            job_history_df = self.extractor.extract_job_history()
            
            employee_count = employees_df.count()
            self.logger.info(f"Extracted {employee_count} employees")
            
            # Transform with denormalization
            self.logger.info("Transforming employee data (6-way join)...")
            
            transformed_df = self.transformer.transform(
                employees_df=employees_df,
                departments_df=departments_df,
                jobs_df=jobs_df,
                locations_df=locations_df,
                countries_df=countries_df,
                regions_df=regions_df,
                job_history_df=job_history_df
            )
            
            self.logger.info("Transformation completed")
            
            # Validate
            self.logger.info("Validating employee data...")
            
            # Field validation
            field_result = self.field_validator.validate_with_metrics(transformed_df)
            self.logger.info(
                "Field validation completed",
                is_valid=field_result.is_valid,
                errors=len(field_result.errors)
            )
            
            # Record validation
            record_result = self.record_validator.validate_with_metrics(
                transformed_df,
                reference_data={
                    "departments": departments_df,
                    "jobs": jobs_df,
                    "locations": locations_df
                }
            )
            self.logger.info(
                "Record validation completed",
                is_valid=record_result.is_valid,
                errors=len(record_result.errors)
            )
            
            # Business rule validation
            business_result = self.business_validator.validate_with_metrics(
                transformed_df,
                business_context={
                    "departments": departments_df,
                    "jobs": jobs_df,
                    "job_history": job_history_df
                }
            )
            self.logger.info(
                "Business rule validation completed",
                is_valid=business_result.is_valid,
                errors=len(business_result.errors)
            )
            
            # Check if validation passed
            all_valid = (
                field_result.is_valid and
                record_result.is_valid and
                business_result.is_valid
            )
            
            if not all_valid:
                self.logger.warning("Validation errors found - review before loading")
                for error in field_result.errors + record_result.errors + business_result.errors:
                    self.logger.warning(f"  - {error['message']}")
            
            # Load to Cosmos
            if self.dry_run:
                self.logger.info("DRY RUN: Skipping Cosmos load")
                loaded_count = employee_count
            else:
                self.logger.info(f"Loading {employee_count} employees to Cosmos...")
                self.loader.load(transformed_df, validate_connection=True)
                loaded_count = employee_count
                self.logger.info("Load completed successfully")
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            
            # Phase details
            details = {
                "completed_at": datetime.now().isoformat(),
                "duration_seconds": duration,
                "employee_count": employee_count,
                "loaded_count": loaded_count,
                "validation_passed": all_valid,
                "field_errors": len(field_result.errors),
                "record_errors": len(record_result.errors),
                "business_errors": len(business_result.errors)
            }
            
            self._mark_phase_completed(phase, details)
            
            self.logger.info("=" * 80)
            self.logger.info("Phase 3 completed successfully")
            self.logger.info(f"  Employees migrated: {loaded_count}")
            self.logger.info(f"  Duration: {duration:.1f}s")
            self.logger.info(f"  Validation passed: {all_valid}")
            self.logger.info("=" * 80)
            
            return details
            
        except Exception as e:
            self.logger.error(f"Phase 3 failed: {e}", exc_info=True)
            raise MigrationError(f"Phase 3 migration failed: {e}")
    
    def migrate_phase_4(self, force: bool = False) -> Dict:
        """
        Migrate Phase 4: Resolve circular department.manager_id references.
        
        Updates department documents to add manager_id after employees are loaded.
        
        Args:
            force: If True, re-migrate even if completed
            
        Returns:
            Dictionary with migration details
        """
        phase = "phase_4"
        
        if self._is_phase_completed(phase) and not force:
            self.logger.info("Phase 4 already completed (use --force to re-run)")
            return self.checkpoint["phase_details"][phase]
        
        self.logger.info("=" * 80)
        self.logger.info("Starting Phase 4: Resolve Department Manager References")
        self.logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # Extract departments with non-NULL manager_id
            self.logger.info("Extracting departments with managers...")
            
            departments_df = self.extractor.extract_departments()
            departments_with_managers = departments_df.filter(
                departments_df.manager_id.isNotNull()
            )
            
            dept_count = departments_with_managers.count()
            self.logger.info(f"Found {dept_count} departments with managers")
            
            if dept_count == 0:
                self.logger.info("No departments to update - skipping Phase 4")
                details = {
                    "completed_at": datetime.now().isoformat(),
                    "duration_seconds": 0,
                    "department_count": 0,
                    "updated_count": 0
                }
                self._mark_phase_completed(phase, details)
                return details
            
            # Transform to reference documents
            self.logger.info("Transforming department updates...")
            
            # Convert types
            converted_df = DataTypeConverter.convert_dataframe(
                departments_with_managers
            )
            
            # Create reference documents (will update existing)
            transformed_df = CommonTransformations.create_reference_document(
                df=converted_df,
                entity_type="department",
                id_column="department_id",
                partition_key_value="ref_data",
                data_columns=[
                    "department_name",
                    "manager_id",
                    "location_id"
                ]
            )
            
            # Load to Cosmos (upsert mode to update existing)
            if self.dry_run:
                self.logger.info("DRY RUN: Skipping department updates")
                updated_count = dept_count
            else:
                self.logger.info(f"Updating {dept_count} departments in Cosmos...")
                # Use upsert mode
                loader = CosmosLoader(
                    config=CosmosDBConnectionConfig(),
                    container="reference_data",
                    batch_size=100,
                    write_mode="upsert"
                )
                loader.upsert_records(transformed_df)
                updated_count = dept_count
                self.logger.info("Updates completed successfully")
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            
            # Phase details
            details = {
                "completed_at": datetime.now().isoformat(),
                "duration_seconds": duration,
                "department_count": dept_count,
                "updated_count": updated_count
            }
            
            self._mark_phase_completed(phase, details)
            
            self.logger.info("=" * 80)
            self.logger.info("Phase 4 completed successfully")
            self.logger.info(f"  Departments updated: {updated_count}")
            self.logger.info(f"  Duration: {duration:.1f}s")
            self.logger.info("=" * 80)
            
            return details
            
        except Exception as e:
            self.logger.error(f"Phase 4 failed: {e}", exc_info=True)
            raise MigrationError(f"Phase 4 migration failed: {e}")
    
    def migrate_all(self, force: bool = False) -> Dict:
        """
        Migrate all phases (3-4).
        
        Args:
            force: If True, re-migrate completed phases
            
        Returns:
            Dictionary with overall migration summary
        """
        self.logger.info("=" * 80)
        self.logger.info("EMPLOYEE MIGRATION - ALL PHASES")
        self.logger.info("=" * 80)
        
        overall_start = datetime.now()
        
        # Validate connections
        self.logger.info("Validating connections...")
        self.extractor.validate_source_connection()
        if not self.dry_run:
            self.loader.validate_target_connection()
        self.logger.info("✓ Connections validated")
        
        # Run Phase 3
        phase3_details = self.migrate_phase_3(force=force)
        
        # Run Phase 4
        phase4_details = self.migrate_phase_4(force=force)
        
        # Calculate totals
        overall_duration = (datetime.now() - overall_start).total_seconds()
        total_employees = phase3_details["employee_count"]
        total_departments = phase4_details["department_count"]
        
        summary = {
            "completed_at": datetime.now().isoformat(),
            "total_duration_seconds": overall_duration,
            "phase_3": phase3_details,
            "phase_4": phase4_details,
            "totals": {
                "employees": total_employees,
                "departments_updated": total_departments,
                "total_records": total_employees + total_departments
            }
        }
        
        self.logger.info("=" * 80)
        self.logger.info("EMPLOYEE MIGRATION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Total Duration: {overall_duration:.1f}s")
        self.logger.info(f"Employees Migrated: {total_employees}")
        self.logger.info(f"Departments Updated: {total_departments}")
        self.logger.info(f"Total Records: {total_employees + total_departments}")
        self.logger.info("=" * 80)
        
        return summary
    
    def validate_migration(self) -> Dict:
        """
        Validate migration by comparing record counts.
        
        Returns:
            Dictionary with validation results
        """
        self.logger.info("Validating employee migration...")
        
        # Get Oracle counts
        employees_df = self.extractor.extract_employees()
        oracle_employee_count = employees_df.count()
        
        departments_df = self.extractor.extract_departments()
        departments_with_managers = departments_df.filter(
            departments_df.manager_id.isNotNull()
        )
        oracle_dept_count = departments_with_managers.count()
        
        # Get checkpoint counts
        phase3_details = self.checkpoint.get("phase_details", {}).get("phase_3", {})
        phase4_details = self.checkpoint.get("phase_details", {}).get("phase_4", {})
        
        checkpoint_employee_count = phase3_details.get("loaded_count", 0)
        checkpoint_dept_count = phase4_details.get("updated_count", 0)
        
        # Compare
        employees_match = oracle_employee_count == checkpoint_employee_count
        departments_match = oracle_dept_count == checkpoint_dept_count
        
        results = {
            "employees": {
                "oracle_count": oracle_employee_count,
                "checkpoint_count": checkpoint_employee_count,
                "match": employees_match
            },
            "departments": {
                "oracle_count": oracle_dept_count,
                "checkpoint_count": checkpoint_dept_count,
                "match": departments_match
            },
            "overall_match": employees_match and departments_match
        }
        
        self.logger.info("Validation results:")
        self.logger.info(f"  Employees: Oracle={oracle_employee_count}, Checkpoint={checkpoint_employee_count}, Match={employees_match}")
        self.logger.info(f"  Departments: Oracle={oracle_dept_count}, Checkpoint={checkpoint_dept_count}, Match={departments_match}")
        
        return results


def main():
    """Main entry point for employee migration."""
    parser = argparse.ArgumentParser(
        description="Migrate employee data from Oracle to Cosmos DB"
    )
    
    parser.add_argument(
        "--checkpoint-file",
        default="employee_migration_checkpoint.json",
        help="Path to checkpoint file"
    )
    
    parser.add_argument(
        "--container",
        default="employees",
        help="Cosmos container name for employees"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without actually loading to Cosmos"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-migration of completed phases"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate migration (no migration)"
    )
    
    parser.add_argument(
        "--phase",
        choices=["3", "4", "all"],
        default="all",
        help="Which phase to run (default: all)"
    )
    
    args = parser.parse_args()
    
    # Create migration instance
    migration = EmployeeMigration(
        checkpoint_file=args.checkpoint_file,
        container_name=args.container,
        dry_run=args.dry_run
    )
    
    try:
        if args.validate_only:
            # Validation only
            results = migration.validate_migration()
            if results["overall_match"]:
                print("\n✅ Migration validation PASSED")
                sys.exit(0)
            else:
                print("\n❌ Migration validation FAILED")
                sys.exit(1)
        
        elif args.phase == "3":
            # Phase 3 only
            migration.migrate_phase_3(force=args.force)
            print("\n✅ Phase 3 completed successfully")
            
        elif args.phase == "4":
            # Phase 4 only
            migration.migrate_phase_4(force=args.force)
            print("\n✅ Phase 4 completed successfully")
            
        else:
            # All phases
            migration.migrate_all(force=args.force)
            print("\n✅ Employee migration completed successfully")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

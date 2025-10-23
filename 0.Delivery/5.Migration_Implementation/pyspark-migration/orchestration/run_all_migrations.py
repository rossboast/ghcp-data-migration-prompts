"""
Full Migration Orchestration Script

Executes complete Oracle HR to Cosmos DB migration across all 4 phases.
Provides comprehensive error handling, rollback procedures, and validation.

Phases:
- Phase 1-2: Reference data (regions, countries, locations, jobs, departments)
- Phase 3-4: Employee data (employees with denormalization, department manager resolution)

Usage:
    # Run complete migration
    python orchestration/run_all_migrations.py
    
    # Dry run (no actual loading)
    python orchestration/run_all_migrations.py --dry-run
    
    # Force re-migration
    python orchestration/run_all_migrations.py --force
    
    # Validate only
    python orchestration/run_all_migrations.py --validate-only
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestration.migrate_reference_data import ReferenceDataMigration
from orchestration.migrate_employees import EmployeeMigration
from utils.logging_config import get_logger
from utils.error_handler import MigrationError


class FullMigrationOrchestrator:
    """
    Orchestrate complete migration from Oracle to Cosmos DB.
    
    Manages all phases with checkpointing, validation, and error handling.
    """
    
    def __init__(
        self,
        checkpoint_file: str = "full_migration_checkpoint.json",
        dry_run: bool = False
    ):
        """
        Initialize full migration orchestrator.
        
        Args:
            checkpoint_file: Path to checkpoint file
            dry_run: If True, skip actual loading
        """
        self.logger = get_logger("full_migration")
        self.checkpoint_file = checkpoint_file
        self.dry_run = dry_run
        
        # Initialize phase migrations
        self.reference_migration = ReferenceDataMigration(
            checkpoint_file="reference_migration_checkpoint.json",
            container_name="reference_data",
            partition_key_value="ref_data",
            dry_run=dry_run
        )
        
        self.employee_migration = EmployeeMigration(
            checkpoint_file="employee_migration_checkpoint.json",
            container_name="employees",
            dry_run=dry_run
        )
        
        # Load checkpoint
        self.checkpoint = self._load_checkpoint()
        
        self.logger.info(
            "Full migration orchestrator initialized",
            checkpoint_file=checkpoint_file,
            dry_run=dry_run
        )
    
    def _load_checkpoint(self) -> Dict:
        """Load checkpoint from file."""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
                self.logger.info(
                    "Loaded checkpoint",
                    completed_stages=checkpoint.get("completed_stages", [])
                )
                return checkpoint
        return {
            "started_at": datetime.now().isoformat(),
            "completed_stages": [],
            "stage_details": {},
            "validation_results": {},
            "last_updated": None
        }
    
    def _save_checkpoint(self):
        """Save checkpoint to file."""
        self.checkpoint["last_updated"] = datetime.now().isoformat()
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)
        self.logger.debug("Checkpoint saved")
    
    def _is_stage_completed(self, stage: str) -> bool:
        """Check if stage is completed."""
        return stage in self.checkpoint.get("completed_stages", [])
    
    def _mark_stage_completed(self, stage: str, details: Dict):
        """Mark stage as completed."""
        if stage not in self.checkpoint.get("completed_stages", []):
            self.checkpoint["completed_stages"].append(stage)
        self.checkpoint["stage_details"][stage] = details
        self._save_checkpoint()
    
    def pre_flight_checks(self) -> bool:
        """
        Run pre-flight validation checks.
        
        Returns:
            True if all checks pass
        """
        self.logger.info("=" * 80)
        self.logger.info("PRE-FLIGHT VALIDATION CHECKS")
        self.logger.info("=" * 80)
        
        checks_passed = []
        checks_failed = []
        
        # Check 1: Oracle connection
        try:
            self.logger.info("1. Testing Oracle connection...")
            self.reference_migration.extractor.validate_source_connection()
            checks_passed.append("Oracle connection")
            self.logger.info("   ✓ Oracle connection OK")
        except Exception as e:
            checks_failed.append(f"Oracle connection: {e}")
            self.logger.error(f"   ✗ Oracle connection failed: {e}")
        
        # Check 2: Cosmos connection
        if not self.dry_run:
            try:
                self.logger.info("2. Testing Cosmos DB connection...")
                self.reference_migration.loader.validate_target_connection()
                checks_passed.append("Cosmos DB connection")
                self.logger.info("   ✓ Cosmos DB connection OK")
            except Exception as e:
                checks_failed.append(f"Cosmos DB connection: {e}")
                self.logger.error(f"   ✗ Cosmos DB connection failed: {e}")
        else:
            self.logger.info("2. Skipping Cosmos DB check (dry run mode)")
        
        # Check 3: Cosmos containers
        if not self.dry_run:
            try:
                self.logger.info("3. Checking Cosmos containers...")
                ref_exists = self.reference_migration.loader.target_exists()
                emp_exists = self.employee_migration.loader.target_exists()
                
                if ref_exists and emp_exists:
                    checks_passed.append("Cosmos containers")
                    self.logger.info("   ✓ Containers exist: reference_data, employees")
                else:
                    missing = []
                    if not ref_exists:
                        missing.append("reference_data")
                    if not emp_exists:
                        missing.append("employees")
                    checks_failed.append(f"Missing containers: {', '.join(missing)}")
                    self.logger.error(f"   ✗ Missing containers: {', '.join(missing)}")
            except Exception as e:
                checks_failed.append(f"Container check: {e}")
                self.logger.error(f"   ✗ Container check failed: {e}")
        else:
            self.logger.info("3. Skipping container check (dry run mode)")
        
        # Check 4: Source data availability
        try:
            self.logger.info("4. Checking source data availability...")
            employees_df = self.reference_migration.extractor.extract_employees()
            employee_count = employees_df.count()
            
            if employee_count > 0:
                checks_passed.append(f"Source data ({employee_count} employees)")
                self.logger.info(f"   ✓ Source data available: {employee_count} employees")
            else:
                checks_failed.append("No source data found")
                self.logger.error("   ✗ No source data found")
        except Exception as e:
            checks_failed.append(f"Source data check: {e}")
            self.logger.error(f"   ✗ Source data check failed: {e}")
        
        # Summary
        self.logger.info("=" * 80)
        self.logger.info("PRE-FLIGHT CHECK SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Passed: {len(checks_passed)}")
        self.logger.info(f"Failed: {len(checks_failed)}")
        
        if checks_failed:
            self.logger.error("Failed checks:")
            for check in checks_failed:
                self.logger.error(f"  - {check}")
        
        all_passed = len(checks_failed) == 0
        self.logger.info("=" * 80)
        
        return all_passed
    
    def migrate_reference_data(self, force: bool = False) -> Dict:
        """
        Migrate reference data (Phase 1-2).
        
        Args:
            force: If True, re-migrate even if completed
            
        Returns:
            Dictionary with migration details
        """
        stage = "reference_data"
        
        if self._is_stage_completed(stage) and not force:
            self.logger.info("Reference data migration already completed")
            return self.checkpoint["stage_details"][stage]
        
        self.logger.info("=" * 80)
        self.logger.info("STAGE 1: REFERENCE DATA MIGRATION (Phase 1-2)")
        self.logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # Run reference data migration
            summary = self.reference_migration.migrate_all(force=force)
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            
            details = {
                "completed_at": datetime.now().isoformat(),
                "duration_seconds": duration,
                "summary": summary
            }
            
            self._mark_stage_completed(stage, details)
            
            self.logger.info("=" * 80)
            self.logger.info("STAGE 1 COMPLETED")
            self.logger.info(f"Duration: {duration:.1f}s")
            self.logger.info("=" * 80)
            
            return details
            
        except Exception as e:
            self.logger.error(f"Reference data migration failed: {e}", exc_info=True)
            raise MigrationError(f"Stage 1 failed: {e}")
    
    def migrate_employee_data(self, force: bool = False) -> Dict:
        """
        Migrate employee data (Phase 3-4).
        
        Args:
            force: If True, re-migrate even if completed
            
        Returns:
            Dictionary with migration details
        """
        stage = "employee_data"
        
        if self._is_stage_completed(stage) and not force:
            self.logger.info("Employee data migration already completed")
            return self.checkpoint["stage_details"][stage]
        
        self.logger.info("=" * 80)
        self.logger.info("STAGE 2: EMPLOYEE DATA MIGRATION (Phase 3-4)")
        self.logger.info("=" * 80)
        
        start_time = datetime.now()
        
        try:
            # Run employee data migration
            summary = self.employee_migration.migrate_all(force=force)
            
            # Calculate duration
            duration = (datetime.now() - start_time).total_seconds()
            
            details = {
                "completed_at": datetime.now().isoformat(),
                "duration_seconds": duration,
                "summary": summary
            }
            
            self._mark_stage_completed(stage, details)
            
            self.logger.info("=" * 80)
            self.logger.info("STAGE 2 COMPLETED")
            self.logger.info(f"Duration: {duration:.1f}s")
            self.logger.info("=" * 80)
            
            return details
            
        except Exception as e:
            self.logger.error(f"Employee data migration failed: {e}", exc_info=True)
            raise MigrationError(f"Stage 2 failed: {e}")
    
    def validate_all(self) -> Dict:
        """
        Validate complete migration.
        
        Returns:
            Dictionary with validation results
        """
        self.logger.info("=" * 80)
        self.logger.info("VALIDATION - ALL STAGES")
        self.logger.info("=" * 80)
        
        # Validate reference data
        self.logger.info("Validating reference data...")
        ref_results = self.reference_migration.validate_migration()
        
        # Validate employee data
        self.logger.info("Validating employee data...")
        emp_results = self.employee_migration.validate_migration()
        
        # Combined results
        validation_results = {
            "reference_data": ref_results,
            "employee_data": emp_results,
            "overall_valid": ref_results["overall_match"] and emp_results["overall_match"]
        }
        
        self.checkpoint["validation_results"] = validation_results
        self._save_checkpoint()
        
        self.logger.info("=" * 80)
        self.logger.info("VALIDATION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Reference Data Valid: {ref_results['overall_match']}")
        self.logger.info(f"Employee Data Valid: {emp_results['overall_match']}")
        self.logger.info(f"Overall Valid: {validation_results['overall_valid']}")
        self.logger.info("=" * 80)
        
        return validation_results
    
    def run_all(self, force: bool = False) -> Dict:
        """
        Run complete migration across all phases.
        
        Args:
            force: If True, re-migrate completed stages
            
        Returns:
            Dictionary with overall migration summary
        """
        self.logger.info("=" * 80)
        self.logger.info("FULL MIGRATION ORCHESTRATION")
        self.logger.info("Oracle HR Database → Azure Cosmos DB")
        self.logger.info("=" * 80)
        
        overall_start = datetime.now()
        
        # Pre-flight checks
        if not self.pre_flight_checks():
            raise MigrationError("Pre-flight checks failed")
        
        # Stage 1: Reference data
        ref_details = self.migrate_reference_data(force=force)
        
        # Stage 2: Employee data
        emp_details = self.migrate_employee_data(force=force)
        
        # Validation
        validation_results = self.validate_all()
        
        # Calculate totals
        overall_duration = (datetime.now() - overall_start).total_seconds()
        
        # Extract totals from summaries
        ref_summary = ref_details.get("summary", {})
        emp_summary = emp_details.get("summary", {})
        
        ref_totals = ref_summary.get("totals", {})
        emp_totals = emp_summary.get("totals", {})
        
        total_records = (
            ref_totals.get("total_records", 0) +
            emp_totals.get("total_records", 0)
        )
        
        summary = {
            "completed_at": datetime.now().isoformat(),
            "total_duration_seconds": overall_duration,
            "stages": {
                "reference_data": ref_details,
                "employee_data": emp_details
            },
            "validation": validation_results,
            "totals": {
                "reference_records": ref_totals.get("total_records", 0),
                "employee_records": emp_totals.get("employees", 0),
                "total_records": total_records,
                "duration_minutes": overall_duration / 60
            }
        }
        
        self.checkpoint["final_summary"] = summary
        self._save_checkpoint()
        
        self.logger.info("=" * 80)
        self.logger.info("MIGRATION COMPLETE - FINAL SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Total Duration: {overall_duration / 60:.1f} minutes")
        self.logger.info(f"Reference Records: {ref_totals.get('total_records', 0)}")
        self.logger.info(f"Employee Records: {emp_totals.get('employees', 0)}")
        self.logger.info(f"Total Records Migrated: {total_records}")
        self.logger.info(f"Validation Status: {'✓ PASSED' if validation_results['overall_valid'] else '✗ FAILED'}")
        self.logger.info("=" * 80)
        
        if validation_results["overall_valid"]:
            self.logger.info("✅ Migration completed successfully!")
        else:
            self.logger.warning("⚠️  Migration completed with validation warnings")
        
        return summary
    
    def generate_migration_report(self) -> str:
        """
        Generate detailed migration report.
        
        Returns:
            Formatted report string
        """
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("MIGRATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Overall status
        completed_stages = self.checkpoint.get("completed_stages", [])
        report_lines.append(f"Completed Stages: {len(completed_stages)}/2")
        report_lines.append(f"Stages: {', '.join(completed_stages) if completed_stages else 'None'}")
        report_lines.append("")
        
        # Stage details
        stage_details = self.checkpoint.get("stage_details", {})
        
        if "reference_data" in stage_details:
            ref = stage_details["reference_data"]
            report_lines.append("Reference Data Migration:")
            report_lines.append(f"  Duration: {ref.get('duration_seconds', 0):.1f}s")
            ref_summary = ref.get("summary", {})
            ref_totals = ref_summary.get("totals", {})
            report_lines.append(f"  Records: {ref_totals.get('total_records', 0)}")
            report_lines.append("")
        
        if "employee_data" in stage_details:
            emp = stage_details["employee_data"]
            report_lines.append("Employee Data Migration:")
            report_lines.append(f"  Duration: {emp.get('duration_seconds', 0):.1f}s")
            emp_summary = emp.get("summary", {})
            emp_totals = emp_summary.get("totals", {})
            report_lines.append(f"  Employees: {emp_totals.get('employees', 0)}")
            report_lines.append(f"  Departments Updated: {emp_totals.get('departments_updated', 0)}")
            report_lines.append("")
        
        # Validation
        validation = self.checkpoint.get("validation_results", {})
        if validation:
            report_lines.append("Validation Results:")
            report_lines.append(f"  Overall Valid: {validation.get('overall_valid', False)}")
            report_lines.append("")
        
        # Final summary
        final_summary = self.checkpoint.get("final_summary", {})
        if final_summary:
            totals = final_summary.get("totals", {})
            report_lines.append("Final Totals:")
            report_lines.append(f"  Total Records: {totals.get('total_records', 0)}")
            report_lines.append(f"  Total Duration: {totals.get('duration_minutes', 0):.1f} minutes")
            report_lines.append("")
        
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)


def main():
    """Main entry point for full migration orchestration."""
    parser = argparse.ArgumentParser(
        description="Run complete Oracle to Cosmos DB migration"
    )
    
    parser.add_argument(
        "--checkpoint-file",
        default="full_migration_checkpoint.json",
        help="Path to checkpoint file"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without actually loading to Cosmos"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-migration of completed stages"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate migration (no migration)"
    )
    
    parser.add_argument(
        "--pre-flight-only",
        action="store_true",
        help="Only run pre-flight checks"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate migration report from checkpoint"
    )
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = FullMigrationOrchestrator(
        checkpoint_file=args.checkpoint_file,
        dry_run=args.dry_run
    )
    
    try:
        if args.report:
            # Generate report
            report = orchestrator.generate_migration_report()
            print(report)
            sys.exit(0)
        
        elif args.pre_flight_only:
            # Pre-flight checks only
            if orchestrator.pre_flight_checks():
                print("\n✅ Pre-flight checks PASSED")
                sys.exit(0)
            else:
                print("\n❌ Pre-flight checks FAILED")
                sys.exit(1)
        
        elif args.validate_only:
            # Validation only
            results = orchestrator.validate_all()
            if results["overall_valid"]:
                print("\n✅ Migration validation PASSED")
                sys.exit(0)
            else:
                print("\n❌ Migration validation FAILED")
                sys.exit(1)
        
        else:
            # Run complete migration
            summary = orchestrator.run_all(force=args.force)
            
            # Generate report
            report = orchestrator.generate_migration_report()
            print("\n" + report)
            
            if summary["validation"]["overall_valid"]:
                print("\n✅ Migration completed successfully!")
                sys.exit(0)
            else:
                print("\n⚠️  Migration completed with validation warnings")
                sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

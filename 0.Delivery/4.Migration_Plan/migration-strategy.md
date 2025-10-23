# Migration Strategy

## Executive Summary

**Chosen Approach**: Denormalized Document Model with Phased Migration  
**Timeline**: 2-3 weeks (development and testing)  
**Risk Level**: Low-Medium  
**Key Success Factors**:
- Proper handling of circular dependencies (departments ↔ employees)
- Effective denormalization of 6-way joins into single documents
- Comprehensive validation of referential integrity
- Performance optimization through partition key strategy

## Approach Selection

### Options Evaluated

#### Option 1: Direct Table-to-Container Mapping
**Description**: Create one CosmosDB container per Oracle table, maintaining relational structure
**Pros**: 
- Simple, direct mapping
- Minimal transformation logic
- Easy to understand and maintain
**Cons**: 
- Requires multiple queries for complete employee details (6-way join)
- Doesn't leverage CosmosDB's document model strengths
- Higher RU consumption for complex queries
**Best For**: Quick POC migrations, maintaining relational mindset
**Risk Level**: Low (technical), High (performance)

#### Option 2: Denormalized Document Model (RECOMMENDED)
**Description**: Embed related data into primary documents, reducing need for joins
**Pros**: 
- Single document read for complete employee information
- Optimal CosmosDB performance pattern
- Reduced RU consumption
- Better alignment with NoSQL best practices
**Cons**: 
- More complex transformation logic
- Data duplication (reference data embedded)
- Update complexity for shared reference data
**Best For**: Production migrations requiring optimal performance
**Risk Level**: Medium (development complexity), Low (performance)

#### Option 3: Hybrid Model
**Description**: Mix of normalized containers for reference data and denormalized for transactional data
**Pros**: 
- Balance between normalization and denormalization
- Reference data easy to update
- Good for datasets with frequent reference updates
**Cons**: 
- Still requires some cross-container queries
- More containers to manage
**Best For**: Scenarios with frequently changing reference data
**Risk Level**: Medium

### Selected Approach: Denormalized Document Model

**Rationale**: 
1. **Small reference data volume** (~98 documents total for jobs, departments, locations, countries, regions) means duplication cost is minimal
2. **Query pattern analysis** shows most queries need complete employee details (job title, department, location, manager)
3. **Read-heavy workload** typical for HR systems benefits from denormalization
4. **Job history tracking** naturally fits as nested array within employee document
5. **Small dataset** (~215 rows) makes migration testing straightforward

**High-Level Steps**:
1. **Phase 1**: Load reference data (regions, countries, locations, jobs) into staging
2. **Phase 2**: Load departments with NULL manager_id, then employees with NULL manager_id
3. **Phase 3**: Resolve circular dependencies (update department managers and employee managers)
4. **Phase 4**: Denormalize and load employee documents with embedded data
5. **Phase 5**: Load reference data container (for admin updates)
6. **Phase 6**: Validate all data and relationships

## Migration Principles

1. **Data Integrity First**: All foreign key relationships must be validated before and after migration
2. **Denormalization for Performance**: Embed frequently-accessed related data to minimize RU consumption
3. **Idempotent Operations**: All PySpark transformations must be re-runnable without side effects
4. **Comprehensive Logging**: Track every record's migration status for troubleshooting
5. **Validation at Every Step**: Validate data after each migration phase
6. **Preserve Business Logic**: Replicate trigger behavior using application logic or change feeds

## Success Criteria

### Functional Success
- ✅ All 215 rows migrated to CosmosDB
- ✅ 100% referential integrity validation passes
- ✅ All self-referencing relationships (manager hierarchy) preserved
- ✅ Job history embedded correctly for all employees
- ✅ No data loss or corruption

### Performance Success
- ✅ Single-digit millisecond read latency for employee documents
- ✅ RU consumption < 50 RU/s for typical query patterns
- ✅ Query for complete employee details requires only 1 document read

### Operational Success
- ✅ Migration scripts are idempotent and can be re-run
- ✅ Comprehensive error logging in audit container
- ✅ Rollback procedure tested and documented
- ✅ Data validation reports generated

## Constraints & Assumptions

### Constraints
- **Small dataset**: Only ~215 rows, so performance at scale is not a concern
- **PySpark required**: Customer requirement to use PySpark for transformations
- **Azure CosmosDB target**: NoSQL document database
- **Read-heavy workload**: HR systems typically have more reads than writes
- **No downtime window**: Migration can happen in parallel (old system continues running)

### Assumptions
- Oracle database is read-only during migration (or changes can be replayed)
- Azure CosmosDB account is provisioned with appropriate throughput
- PySpark cluster (Databricks or Synapse) is available
- Source Oracle database is accessible from PySpark environment
- Reference data (jobs, departments, locations) changes infrequently
- Job history tracking will move to application layer or Azure Functions Change Feed

## Rollback Strategy

### Pre-Migration Safeguards
1. **Full Oracle export**: Export all data before migration begins
2. **CosmosDB snapshots**: Take snapshots of empty containers
3. **Audit trail**: Log all operations in audit_log container

### Rollback Scenarios

#### Scenario A: Validation Fails During Migration
**Action**: 
- Stop migration immediately
- Delete all documents from employees and reference_data containers
- Review error logs in audit_log container
- Fix transformation logic
- Re-run migration from start

#### Scenario B: Data Corruption Discovered Post-Migration
**Action**:
- Keep Oracle database as source of truth
- Delete corrupted CosmosDB containers
- Restore from Oracle backup if needed
- Identify root cause
- Implement fix
- Re-run migration with additional validation

#### Scenario C: Performance Issues in Production
**Action**:
- Investigate query patterns and RU consumption
- Adjust partition key if needed (requires migration to new container)
- Add/remove indexing policies
- Consider enabling cache for reference data
- May require data model adjustments

### Recovery Time Objective (RTO)
- **Time to detect issue**: < 1 hour (validation reports)
- **Time to rollback**: < 30 minutes (delete containers, restore from Oracle)
- **Time to fix and re-run**: 2-4 hours (depending on issue complexity)

## Migration Timeline

### Week 1: Development
- Day 1-2: PySpark data extraction and staging
- Day 3-4: Transformation logic development
- Day 5: Validation framework implementation

### Week 2: Testing
- Day 1-2: Unit testing of transformations
- Day 3: End-to-end migration test run
- Day 4: Data validation and quality checks
- Day 5: Performance testing and optimization

### Week 3: Production Migration
- Day 1: Final pre-migration checks
- Day 2: Production migration execution
- Day 3: Post-migration validation
- Day 4: Parallel run (Oracle + CosmosDB)
- Day 5: Sign-off and documentation

## Next Steps

1. Review and approve this migration strategy
2. Begin detailed CosmosDB data model design
3. Design PySpark transformation architecture
4. Create implementation task breakdown
5. Set up development environment

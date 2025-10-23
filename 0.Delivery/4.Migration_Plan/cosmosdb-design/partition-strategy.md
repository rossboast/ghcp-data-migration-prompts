# Partition Strategy

## Overview

Proper partition key selection is critical for CosmosDB performance and cost optimization. This document outlines the partition strategy for each container in the HR migration.

## Partition Key Selection Process

### Evaluation Criteria

1. **Cardinality**: Number of distinct partition key values
   - Target: 10-100 for small datasets, 100+ for large datasets
   - Too low = hot partitions, too high = overhead

2. **Even Distribution**: How evenly data is distributed across partitions
   - Target: Balanced distribution (no single partition > 20% of data)

3. **Query Pattern Alignment**: How well partition key supports common queries
   - Target: 80%+ of queries can provide partition key

4. **Write Pattern Alignment**: Avoid hot partitions during writes
   - Target: Writes distributed across multiple partitions

5. **Future Growth**: Partition key should scale with data growth
   - Target: Supports 10x growth without rearchitecture

## Container 1: employees

### Option 1: Partition by employee_id ❌

**Partition Key**: `/employee/employee_id`

**Analysis**:
```
Cardinality: 107 (one per employee) ✅
Distribution: Perfect (1 document per partition) ✅
Query Efficiency: Poor (most queries cross partitions) ❌
Write Efficiency: Excellent (distributed) ✅
```

**Pros**:
- Perfect distribution
- No hot partitions
- Point reads are efficient with known employee_id

**Cons**:
- "Get all employees in department" crosses all partitions
- "Get employees by manager" crosses all partitions
- "Search by name" crosses all partitions
- Poor for reporting queries

**Verdict**: ❌ Not recommended - Too many cross-partition queries

---

### Option 2: Partition by department_id ❌

**Partition Key**: `/department/department_id`

**Analysis**:
```
Cardinality: 27 (one per department) ⚠️
Distribution: Uneven (some depts have 1 employee, others have 40+) ❌
Query Efficiency: Good (dept queries efficient) ✅
Write Efficiency: Risk of hot partitions ❌
```

**Pros**:
- "Get all employees in department" is single-partition query
- Natural grouping by business unit
- Aligns with common reporting needs

**Cons**:
- Shipping dept (dept_id 50) has ~45 employees = hot partition
- Executive dept (dept_id 90) has only ~3 employees
- Uneven distribution impacts performance
- Could become hot partition with writes

**Verdict**: ❌ Not recommended for production - Uneven distribution

---

### Option 3: Synthetic Partition Key (RECOMMENDED) ✅

**Partition Key**: `/partitionKey`

**Formula**: `dept_${department_id}_${employee_id % 10}`

**Examples**:
- Employee 100 in dept 90: `dept_90_0`
- Employee 101 in dept 90: `dept_90_1`
- Employee 145 in dept 50: `dept_50_5`

**Analysis**:
```
Cardinality: ~270 (27 depts × 10 buckets) ✅
Distribution: Excellent (evenly distributed) ✅
Query Efficiency: Good (dept queries fan-out 10x) ⚠️
Write Efficiency: Excellent (distributed) ✅
Future Growth: Excellent (scales linearly) ✅
```

**Evaluation Scores**:

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Cardinality | 5 | ~270 unique values, excellent for this dataset |
| Even Distribution | 5 | Employee ID mod 10 ensures even split within dept |
| Query Efficiency | 4 | Dept queries hit 10 partitions (acceptable fan-out) |
| Write Efficiency | 5 | Writes distributed across many partitions |
| Future Growth | 5 | Supports 10x growth (270 → 2700 partitions) |

**Pros**:
- ✅ Prevents hot partitions (splits large departments into 10 buckets)
- ✅ Dept queries require only 10 partition reads (manageable fan-out)
- ✅ Even distribution across partitions
- ✅ Scales well with employee growth
- ✅ Write operations well-distributed

**Cons**:
- ⚠️ Slightly more complex (requires calculation)
- ⚠️ Dept queries not single-partition (but bounded to 10)
- ⚠️ Application must calculate partition key

**Implementation**:

```python
def calculate_partition_key(department_id, employee_id):
    """Calculate synthetic partition key for employee"""
    bucket = employee_id % 10
    return f"dept_{department_id}_{bucket}"

# Examples
calculate_partition_key(90, 100)  # "dept_90_0"
calculate_partition_key(50, 145)  # "dept_50_5"
```

**Verdict**: ✅ **RECOMMENDED** - Best balance of distribution and query efficiency

---

### Partition Distribution Projection

For current dataset (107 employees):

| Department | Employees | Partitions | Avg per Partition | Max per Partition |
|------------|-----------|------------|-------------------|-------------------|
| 10 (Admin) | 1 | 1 | 1 | 1 |
| 20 (Marketing) | 2 | 2 | 1 | 1 |
| 50 (Shipping) | 45 | 10 | 4.5 | 5 |
| 60 (IT) | 5 | 5 | 1 | 1 |
| 80 (Sales) | 34 | 10 | 3.4 | 4 |
| 90 (Executive) | 3 | 3 | 1 | 1 |
| Others | 17 | varies | ~1-2 | 2 |

**Analysis**: 
- Largest partition: ~5 documents (Shipping department, bucket 5)
- Most partitions: 1-2 documents
- Excellent distribution, no hot partitions

## Container 2: reference_data

### Partition Key: /type ✅

**Partition Key**: `/type`

**Partition Values**: 
- `"region"` - 4 documents
- `"country"` - 25 documents
- `"location"` - 23 documents
- `"department"` - 27 documents
- `"job"` - 19 documents

**Analysis**:
```
Cardinality: 5 (one per entity type) ⚠️
Distribution: Uneven but acceptable for reference data ✅
Query Efficiency: Excellent (always know the type) ✅
Write Efficiency: N/A (reference data rarely written) ✅
```

**Evaluation Scores**:

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Cardinality | 2 | Only 5 partitions, but acceptable for reference data |
| Even Distribution | 3 | Uneven (4 to 27 docs), but small total size |
| Query Efficiency | 5 | Always query by type (single partition) |
| Write Efficiency | 5 | Infrequent writes, not a concern |

**Pros**:
- ✅ Natural grouping by entity type
- ✅ Queries always single-partition ("get all jobs", "get all locations")
- ✅ Simple and intuitive
- ✅ Perfect for admin UI (list all jobs, list all departments)

**Cons**:
- ⚠️ Low cardinality (only 5 partitions)
- ⚠️ Uneven distribution (but total size is small)

**Verdict**: ✅ **RECOMMENDED** - Perfect for reference data use case

**Note**: For reference data, we can enable Azure Cache for Redis to minimize RU consumption for frequent lookups.

---

## Container 3: audit_log

### Partition Key: /date ✅

**Partition Key**: `/partitionKey` (stored as date string: "YYYY-MM-DD")

**Examples**:
- Migration on Oct 21, 2025: `"2025-10-21"`
- Validation on Oct 22, 2025: `"2025-10-22"`

**Analysis**:
```
Cardinality: High (one per day) ✅
Distribution: Excellent (one day of logs per partition) ✅
Query Efficiency: Excellent (queries by date range) ✅
Write Efficiency: Good (all writes for day go to same partition) ⚠️
```

**Evaluation Scores**:

| Criteria | Score (1-5) | Notes |
|----------|-------------|-------|
| Cardinality | 5 | One partition per day = high cardinality |
| Even Distribution | 5 | Each day roughly equal log volume |
| Query Efficiency | 5 | Queries typically by date/date range |
| Write Efficiency | 4 | During migration, heavy writes to single partition (acceptable) |

**Pros**:
- ✅ Natural time-series partitioning
- ✅ Queries by date are single-partition
- ✅ Easy to implement TTL (delete old partitions)
- ✅ Scales indefinitely with time

**Cons**:
- ⚠️ During migration day, all writes go to single partition (but temporary)
- ⚠️ Queries spanning multiple days cross partitions (acceptable for audit logs)

**Verdict**: ✅ **RECOMMENDED** - Standard pattern for time-series data

---

## Hot Partition Prevention

### For employees Container

**Risk**: Large departments (Shipping, Sales) could become hot if using department_id alone

**Mitigation**: Synthetic partition key splits departments into 10 buckets

**Monitoring**:
```
-- Query to check partition distribution
SELECT c.partitionKey, COUNT(1) as doc_count
FROM c
GROUP BY c.partitionKey
ORDER BY doc_count DESC
```

**Threshold**: No partition should have > 10 documents

**Action if threshold exceeded**: 
- Increase bucket count (mod 10 → mod 20)
- Requires data migration to new container

### For reference_data Container

**Risk**: Low, as reference data is small and infrequently updated

**Mitigation**: None needed - cache frequently accessed data in Azure Cache for Redis

### For audit_log Container

**Risk**: During migration day, all writes go to single partition

**Mitigation**: 
- Acceptable for one-time migration
- Provision sufficient RUs for migration day
- Scale down after migration complete

---

## Cross-Partition Queries

### Queries Requiring Cross-Partition

#### 1. "Search employees by name"
```sql
SELECT * FROM c WHERE CONTAINS(c.employee.last_name, 'King')
```
**Justification**: Name search is infrequent, acceptable to scan all partitions  
**Mitigation**: Add index on last_name to minimize RU cost  
**Expected RU Cost**: ~20-50 RU (for 107 documents)

#### 2. "Get all employees"
```sql
SELECT * FROM c
```
**Justification**: Rare query, typically for reporting/analytics  
**Mitigation**: Use Azure Synapse Link for OLAP queries  
**Expected RU Cost**: ~50-100 RU (for 107 documents)

#### 3. "Get employees by manager_id"
```sql
SELECT * FROM c WHERE c.manager.manager_id = 100
```
**Justification**: Infrequent query, manager hierarchy usually top-down  
**Mitigation**: If frequent, consider adding manager_id to partition key  
**Expected RU Cost**: ~20-50 RU (for 107 documents)

#### 4. "Get employees in department"
```sql
SELECT * FROM c WHERE c.department.department_id = 50
```
**Justification**: With synthetic key, queries 10 partitions (bounded fan-out)  
**Mitigation**: 10 partitions is acceptable for this query pattern  
**Expected RU Cost**: ~10-20 RU (reads 10 partitions, ~45 docs for dept 50)

---

## Partition Key Evolution

### Scenario: Need to Change Partition Key

**When might this happen?**
- Query patterns change significantly
- Hot partitions develop despite initial design
- Data volume grows 100x+

**Migration Strategy**:
1. Create new container with new partition key
2. Migrate data using PySpark (similar to original migration)
3. Update application to write to both containers (dual-write pattern)
4. Validate new container
5. Switch application read traffic to new container
6. Decommission old container

**Estimated Effort**: 1-2 weeks (for this small dataset)

### Scenario: Department Reorganization

**Example**: Company merges two departments

**Impact**: Partition keys remain valid (`dept_50_0` still exists)

**Action**: Update reference_data container, optionally update employee documents

---

## Testing & Validation

### Partition Distribution Test

```python
# PySpark code to validate partition distribution
from pyspark.sql import SparkJar
from pyspark.sql.functions import col

# Read all employees
df = spark.read.format("cosmos.oltp")\
    .option("spark.cosmos.accountEndpoint", cosmos_endpoint)\
    .option("spark.cosmos.container", "employees")\
    .load()

# Check partition distribution
partition_dist = df.groupBy("partitionKey")\
    .count()\
    .orderBy(col("count").desc())

partition_dist.show(50)

# Validation checks
max_docs_per_partition = partition_dist.agg({"count": "max"}).collect()[0][0]
min_docs_per_partition = partition_dist.agg({"count": "min"}).collect()[0][0]

print(f"Max documents per partition: {max_docs_per_partition}")
print(f"Min documents per partition: {min_docs_per_partition}")

# Flag if max > threshold
if max_docs_per_partition > 10:
    print("WARNING: Hot partition detected!")
```

### Query Performance Test

```python
# Test query patterns with explain plan
queries = [
    ("Point read", "SELECT * FROM c WHERE c.id = 'emp_100'"),
    ("Dept query", "SELECT * FROM c WHERE c.department.department_id = 50"),
    ("Name search", "SELECT * FROM c WHERE CONTAINS(c.employee.last_name, 'King')"),
    ("All employees", "SELECT * FROM c"),
]

for name, query in queries:
    # Execute with explain plan to see RU cost
    print(f"\n{name}: {query}")
    # Check x-ms-request-charge header for RU cost
```

---

## Summary & Recommendations

### Employees Container
- **Partition Key**: `/partitionKey` (synthetic: `dept_{dept_id}_{emp_id % 10}`)
- **Rationale**: Best balance of distribution and query efficiency
- **Expected Partitions**: ~270
- **Max Docs per Partition**: ~5

### Reference_Data Container
- **Partition Key**: `/type`
- **Rationale**: Natural grouping, single-partition queries
- **Expected Partitions**: 5
- **Max Docs per Partition**: ~27

### Audit_Log Container
- **Partition Key**: `/partitionKey` (date: "YYYY-MM-DD")
- **Rationale**: Standard time-series pattern
- **Expected Partitions**: Grows daily
- **Max Docs per Partition**: Variable (one migration day's logs)

### Implementation Notes

1. Application must calculate synthetic partition key for employees
2. Cache reference_data in Azure Cache for Redis for frequent lookups
3. Monitor partition distribution post-migration
4. Scale RUs for migration day, then scale down
5. Consider adding Synapse Link for analytics/reporting queries

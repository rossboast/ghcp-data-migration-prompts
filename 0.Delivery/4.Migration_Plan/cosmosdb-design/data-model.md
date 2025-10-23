# CosmosDB Data Model

## Design Philosophy

**Modeling Approach**: Denormalized document model with selective embedding  
**Rationale**: 
- Oracle HR schema requires 6-way joins for complete employee information
- CosmosDB excels at single-document reads
- Small reference data volume (~98 documents) makes embedding cost-effective
- Read-heavy HR workload benefits from pre-joined data
- Job history naturally fits as nested array within employee document

## Container Design

### Container 1: employees

**Purpose**: Store all employee records with denormalized related data  
**Source Tables**: employees, jobs, departments, locations, countries, regions, job_history  
**Partition Key**: `/partitionKey` (synthetic key based on department_id)  
**Expected Document Count**: ~107 documents  
**Average Document Size**: ~2-3 KB

#### Document Structure

```json
{
  "id": "emp_100",
  "partitionKey": "dept_90_0",
  "entityType": "employee",
  "version": "1.0",
  
  "employee": {
    "employee_id": 100,
    "first_name": "Steven",
    "last_name": "King",
    "email": "SKING",
    "phone_number": "515.123.4567",
    "hire_date": "2003-06-17T00:00:00Z",
    "salary": 24000,
    "commission_pct": null
  },
  
  "job": {
    "job_id": "AD_PRES",
    "job_title": "President",
    "min_salary": 20000,
    "max_salary": 40000
  },
  
  "department": {
    "department_id": 90,
    "department_name": "Executive",
    "manager_id": 100,
    "manager_name": "Steven King"
  },
  
  "location": {
    "location_id": 1700,
    "street_address": "2004 Charade Rd",
    "postal_code": "98199",
    "city": "Seattle",
    "state_province": "Washington",
    "country_id": "US",
    "country_name": "United States of America",
    "region_id": 2,
    "region_name": "Americas"
  },
  
  "manager": {
    "manager_id": null,
    "manager_name": null,
    "manager_email": null
  },
  
  "job_history": [
    {
      "start_date": "2001-09-21T00:00:00Z",
      "end_date": "2003-06-17T00:00:00Z",
      "job_id": "AD_VP",
      "job_title": "Vice President",
      "department_id": 90,
      "department_name": "Executive"
    }
  ],
  
  "metadata": {
    "created_date": "2025-10-21T00:00:00Z",
    "migrated_date": "2025-10-21T00:00:00Z",
    "source_system": "Oracle HR",
    "last_modified": "2025-10-21T00:00:00Z"
  }
}
```

#### Document Example - Employee with Manager

```json
{
  "id": "emp_101",
  "partitionKey": "dept_90_1",
  "entityType": "employee",
  "version": "1.0",
  
  "employee": {
    "employee_id": 101,
    "first_name": "Neena",
    "last_name": "Kochhar",
    "email": "NKOCHHAR",
    "phone_number": "515.123.4568",
    "hire_date": "2005-09-21T00:00:00Z",
    "salary": 17000,
    "commission_pct": null
  },
  
  "job": {
    "job_id": "AD_VP",
    "job_title": "Administration Vice President",
    "min_salary": 15000,
    "max_salary": 30000
  },
  
  "department": {
    "department_id": 90,
    "department_name": "Executive",
    "manager_id": 100,
    "manager_name": "Steven King"
  },
  
  "location": {
    "location_id": 1700,
    "street_address": "2004 Charade Rd",
    "postal_code": "98199",
    "city": "Seattle",
    "state_province": "Washington",
    "country_id": "US",
    "country_name": "United States of America",
    "region_id": 2,
    "region_name": "Americas"
  },
  
  "manager": {
    "manager_id": 100,
    "manager_name": "Steven King",
    "manager_email": "SKING"
  },
  
  "job_history": [],
  
  "metadata": {
    "created_date": "2025-10-21T00:00:00Z",
    "migrated_date": "2025-10-21T00:00:00Z",
    "source_system": "Oracle HR",
    "last_modified": "2025-10-21T00:00:00Z"
  }
}
```

### Container 2: reference_data

**Purpose**: Store reference/lookup data for administrative updates  
**Source Tables**: regions, countries, locations, departments, jobs  
**Partition Key**: `/type` (e.g., "region", "country", "location", "department", "job")  
**Expected Document Count**: ~98 documents  
**Average Document Size**: ~0.5-1 KB

#### Document Structure - Region

```json
{
  "id": "region_1",
  "partitionKey": "region",
  "entityType": "region",
  "version": "1.0",
  
  "data": {
    "region_id": 1,
    "region_name": "Europe"
  },
  
  "metadata": {
    "created_date": "2025-10-21T00:00:00Z",
    "migrated_date": "2025-10-21T00:00:00Z",
    "source_system": "Oracle HR",
    "last_modified": "2025-10-21T00:00:00Z"
  }
}
```

#### Document Structure - Department

```json
{
  "id": "dept_90",
  "partitionKey": "department",
  "entityType": "department",
  "version": "1.0",
  
  "data": {
    "department_id": 90,
    "department_name": "Executive",
    "manager_id": 100,
    "manager_name": "Steven King",
    "location_id": 1700,
    "location_name": "Seattle, Washington, US"
  },
  
  "metadata": {
    "created_date": "2025-10-21T00:00:00Z",
    "migrated_date": "2025-10-21T00:00:00Z",
    "source_system": "Oracle HR",
    "last_modified": "2025-10-21T00:00:00Z"
  }
}
```

#### Document Structure - Job

```json
{
  "id": "job_AD_PRES",
  "partitionKey": "job",
  "entityType": "job",
  "version": "1.0",
  
  "data": {
    "job_id": "AD_PRES",
    "job_title": "President",
    "min_salary": 20000,
    "max_salary": 40000
  },
  
  "metadata": {
    "created_date": "2025-10-21T00:00:00Z",
    "migrated_date": "2025-10-21T00:00:00Z",
    "source_system": "Oracle HR",
    "last_modified": "2025-10-21T00:00:00Z"
  }
}
```

### Container 3: audit_log

**Purpose**: Track migration operations, validation results, and errors  
**Partition Key**: `/date` (YYYY-MM-DD format)  
**Expected Document Count**: Variable (depends on migration operations)  
**Retention**: 90 days

#### Document Structure - Migration Event

```json
{
  "id": "migration_20251021_001",
  "partitionKey": "2025-10-21",
  "entityType": "migration_event",
  "version": "1.0",
  
  "event": {
    "event_type": "migration_start",
    "phase": "phase_1_reference_data",
    "timestamp": "2025-10-21T10:00:00Z",
    "table_name": "regions",
    "records_processed": 0,
    "records_success": 0,
    "records_failed": 0,
    "status": "in_progress"
  },
  
  "metadata": {
    "created_date": "2025-10-21T10:00:00Z"
  }
}
```

#### Document Structure - Validation Result

```json
{
  "id": "validation_20251021_001",
  "partitionKey": "2025-10-21",
  "entityType": "validation_result",
  "version": "1.0",
  
  "validation": {
    "validation_type": "foreign_key_check",
    "timestamp": "2025-10-21T11:00:00Z",
    "check_description": "Validate employee.department_id exists in departments",
    "records_checked": 107,
    "records_passed": 107,
    "records_failed": 0,
    "status": "passed",
    "failures": []
  },
  
  "metadata": {
    "created_date": "2025-10-21T11:00:00Z"
  }
}
```

## Data Type Mappings

| Oracle Type | CosmosDB Type | Transformation Notes | Example |
|-------------|---------------|---------------------|---------|
| NUMBER(p,s) | number | Direct mapping for numeric data | 24000 |
| NUMBER(p) | number | Direct mapping for integers | 100 |
| VARCHAR2(n) | string | Direct mapping | "Steven King" |
| CHAR(n) | string | Trim trailing spaces | "US" |
| DATE | string | Convert to ISO 8601 format | "2003-06-17T00:00:00Z" |
| TIMESTAMP | string | Convert to ISO 8601 with milliseconds | "2003-06-17T10:30:45.123Z" |
| BLOB | string | Base64 encode (not in HR schema) | N/A |
| CLOB | string | Direct string mapping (not in HR schema) | N/A |

### Special Handling

- **NULL values**: Represented as JSON `null`, not omitted
- **Sequences**: Replaced with document `id` values (e.g., `emp_100`)
- **Triggers**: Replicated via application logic or Azure Functions Change Feed
- **Index-Organized Tables (IOT)**: Treated as regular documents in CosmosDB

## Denormalization Strategy

### Employee Entity (Primary Document)

**Embedded Data**:
- ✅ Job details (job_id, job_title, min/max salary)
- ✅ Department details (dept_id, name, manager info)
- ✅ Full location hierarchy (location → country → region)
- ✅ Manager summary (id, name, email)
- ✅ Job history array (complete history with job/dept names)

**Referenced Data**: None (fully denormalized)

**Rationale**:
- Most queries need complete employee context
- Reference data is relatively static
- Small dataset makes duplication acceptable
- Eliminates need for 6-way joins
- Job history naturally belongs with employee

### Reference Data (Secondary Container)

**Purpose**: 
- Administrative interface for updating reference data
- Potential source for batch updates to employee documents
- Reporting and analytics

**Not Embedded**: Reference data stands alone for updates

### Update Strategy

When reference data changes (e.g., department name update):

**Option A: Accept Stale Data** (Recommended for HR)
- Reference data updates are infrequent
- Employees retain historical context
- Example: If department renamed, employee shows name at time of assignment

**Option B: Batch Update via Change Feed**
- Azure Function triggered by reference_data changes
- Updates all affected employee documents
- Use for critical fields like location addresses

**Option C: Application-Level Refresh**
- Periodic job to sync reference data changes
- Run nightly or weekly depending on requirements

## Query Optimization

### Expected Query Patterns

#### 1. Get Employee by ID
```sql
SELECT * FROM c WHERE c.employee.employee_id = 101
```
**Data Model Support**: Single document read, partition key may need to be provided
**RU Cost**: ~1 RU

#### 2. Get All Employees in Department
```sql
SELECT * FROM c WHERE c.department.department_id = 90
```
**Data Model Support**: Query within single partition (if partition key is based on dept)
**RU Cost**: ~5-10 RU

#### 3. Get Employee's Full Details (6-way join in Oracle)
```sql
SELECT * FROM c WHERE c.id = 'emp_101'
```
**Data Model Support**: Single document read with all embedded data
**RU Cost**: ~1 RU (vs. 50+ RU for 6 separate queries)

#### 4. Search Employees by Name
```sql
SELECT * FROM c WHERE CONTAINS(c.employee.last_name, 'King')
```
**Data Model Support**: Cross-partition query with index
**RU Cost**: ~10-20 RU

#### 5. Get Employee's Job History
```sql
SELECT c.employee.employee_id, c.employee.first_name, c.job_history 
FROM c WHERE c.id = 'emp_101'
```
**Data Model Support**: Single document read, job history embedded as array
**RU Cost**: ~1 RU

#### 6. Get All Employees with Manager Info
```sql
SELECT c.employee.employee_id, c.employee.first_name, c.manager 
FROM c WHERE c.manager.manager_id != null
```
**Data Model Support**: Cross-partition query (all employees)
**RU Cost**: ~20-50 RU

## Migration from Relational Model

### Relationships Handling

#### One-to-Many: Department → Employees
**Oracle Model**: `employees.department_id → departments.department_id`  
**CosmosDB Strategy**: Embed department details in employee document  
**Implementation**: 
- Join departments table during PySpark transformation
- Embed department_id, department_name, manager info
- Reference data container maintains master department list

#### One-to-Many: Location → Departments
**Oracle Model**: `departments.location_id → locations.location_id`  
**CosmosDB Strategy**: Embed full location hierarchy in employee document  
**Implementation**: 
- Join locations → countries → regions during transformation
- Create complete geographic context
- Single document read provides full address

#### Many-to-One: Employees → Jobs
**Oracle Model**: `employees.job_id → jobs.job_id`  
**CosmosDB Strategy**: Embed job details in employee document  
**Implementation**: 
- Join jobs table during transformation
- Embed job_id, job_title, salary range
- Job changes trigger new entries in job_history array

#### Self-Referencing: Employee → Manager
**Oracle Model**: `employees.manager_id → employees.employee_id`  
**CosmosDB Strategy**: Embed manager summary (not full manager document)  
**Implementation**: 
- During transformation, lookup manager details
- Embed manager_id, name, email only
- Avoid circular references by not embedding full manager doc
- For manager hierarchy queries, use recursive application logic

#### One-to-Many: Employee → Job History
**Oracle Model**: `job_history.employee_id → employees.employee_id`  
**CosmosDB Strategy**: Embed job history as array in employee document  
**Implementation**: 
- Group job_history by employee_id during transformation
- Create array of history entries with denormalized job/dept names
- Maintain chronological order (oldest to newest)
- Empty array for employees with no history

### Circular Dependency: Departments ↔ Employees

**Oracle Challenge**: 
- `departments.manager_id → employees.employee_id`
- `employees.department_id → departments.department_id`

**CosmosDB Resolution**:
1. Embed department details in employee document (one direction)
2. Store manager summary in department details (manager_id and name)
3. Do not embed full manager employee document (would create circular reference)
4. For full manager details, perform separate query if needed

**Example**:
```json
{
  "employee": {"employee_id": 101, ...},
  "department": {
    "department_id": 90,
    "department_name": "Executive",
    "manager_id": 100,
    "manager_name": "Steven King"  // Summary only
  }
}
```

## Data Model Versioning

**Version Field**: `"version": "1.0"`  
**Purpose**: Support future schema evolution

**Version Update Scenarios**:
- Adding new embedded fields
- Changing document structure
- Supporting multiple data models during transition

**Backward Compatibility Strategy**:
- Application code checks version field
- Handles multiple versions gracefully
- Migration scripts can upgrade document versions

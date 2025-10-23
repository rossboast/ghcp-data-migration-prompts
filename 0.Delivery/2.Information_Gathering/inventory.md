# Information Gathering - Oracle HR Schema Migration

## Overview
This document inventories all gathered information about the source Oracle HR (Human Resources) schema for migration to Azure CosmosDB.

**Source Schema:** Oracle HR (Human Resources) Sample Schema  
**Schema Version:** 21  
**Last Updated:** 03-FEB-2022  
**Location:** `db-sample-schemas/human_resources/`

---

## 1. Database Schema Information

### Schema Summary
The HR schema is a simple, well-documented Oracle sample schema that models a Human Resources department for a company. It tracks:
- Employee information (personnel records)
- Department organization
- Job roles and history
- Geographic locations (countries, regions, locations)

### Tables Inventory

| # | Table Name | Purpose | Row Count Estimate | Primary Key |
|---|------------|---------|-------------------|-------------|
| 1 | `regions` | Geographic regions | Small (~4) | `region_id` |
| 2 | `countries` | Country information | Medium (~25) | `country_id` |
| 3 | `locations` | Physical addresses | Medium (~23) | `location_id` |
| 4 | `departments` | Company departments | Medium (~27) | `department_id` |
| 5 | `jobs` | Job roles/titles | Medium (~19) | `job_id` |
| 6 | `employees` | Employee records | Medium (~107) | `employee_id` |
| 7 | `job_history` | Employment history | Medium (~10) | `employee_id, start_date` |

**Total Tables:** 7 (Close to estimated 10)

---

## 2. Table Structures

### 2.1 REGIONS
```sql
CREATE TABLE regions (
    region_id      NUMBER       NOT NULL,
    region_name    VARCHAR2(25)
);
PRIMARY KEY: region_id
```

### 2.2 COUNTRIES
```sql
CREATE TABLE countries (
    country_id      CHAR(2)      NOT NULL,
    country_name    VARCHAR2(60),
    region_id       NUMBER
);
PRIMARY KEY: country_id
FOREIGN KEY: region_id -> regions(region_id)
ORGANIZATION INDEX (IOT)
```

### 2.3 LOCATIONS
```sql
CREATE TABLE locations (
    location_id      NUMBER(4),
    street_address   VARCHAR2(40),
    postal_code      VARCHAR2(12),
    city             VARCHAR2(30)  NOT NULL,
    state_province   VARCHAR2(25),
    country_id       CHAR(2)
);
PRIMARY KEY: location_id
FOREIGN KEY: country_id -> countries(country_id)
SEQUENCE: locations_seq (starts at 3300, increment 100)
```

### 2.4 DEPARTMENTS
```sql
CREATE TABLE departments (
    department_id    NUMBER(4),
    department_name  VARCHAR2(30)  NOT NULL,
    manager_id       NUMBER(6),
    location_id      NUMBER(4)
);
PRIMARY KEY: department_id
FOREIGN KEY: manager_id -> employees(employee_id)
FOREIGN KEY: location_id -> locations(location_id)
SEQUENCE: departments_seq (starts at 280, increment 10)
```

### 2.5 JOBS
```sql
CREATE TABLE jobs (
    job_id         VARCHAR2(10),
    job_title      VARCHAR2(35)  NOT NULL,
    min_salary     NUMBER(6),
    max_salary     NUMBER(6)
);
PRIMARY KEY: job_id
```

### 2.6 EMPLOYEES
```sql
CREATE TABLE employees (
    employee_id    NUMBER(6),
    first_name     VARCHAR2(20),
    last_name      VARCHAR2(25)  NOT NULL,
    email          VARCHAR2(25)  NOT NULL UNIQUE,
    phone_number   VARCHAR2(20),
    hire_date      DATE          NOT NULL,
    job_id         VARCHAR2(10)  NOT NULL,
    salary         NUMBER(8,2),
    commission_pct NUMBER(2,2),
    manager_id     NUMBER(6),
    department_id  NUMBER(4)
);
PRIMARY KEY: employee_id
FOREIGN KEY: department_id -> departments(department_id)
FOREIGN KEY: job_id -> jobs(job_id)
FOREIGN KEY: manager_id -> employees(employee_id) -- SELF-REFERENCING
CHECK: salary > 0
UNIQUE: email
SEQUENCE: employees_seq (starts at 207, increment 1)
```

### 2.7 JOB_HISTORY
```sql
CREATE TABLE job_history (
    employee_id     NUMBER(6)     NOT NULL,
    start_date      DATE          NOT NULL,
    end_date        DATE          NOT NULL,
    job_id          VARCHAR2(10)  NOT NULL,
    department_id   NUMBER(4)
);
PRIMARY KEY: (employee_id, start_date) -- COMPOSITE KEY
FOREIGN KEY: job_id -> jobs(job_id)
FOREIGN KEY: employee_id -> employees(employee_id)
FOREIGN KEY: department_id -> departments(department_id)
CHECK: end_date > start_date
```

---

## 3. Relationships and Dependencies

### Foreign Key Dependencies (Migration Order)
```
1. regions (no dependencies)
2. countries (depends on regions)
3. locations (depends on countries)
4. jobs (no dependencies)
5. departments (depends on locations) - circular with employees
6. employees (depends on departments, jobs, self) - circular with departments
7. job_history (depends on employees, jobs, departments)
```

**IMPORTANT:** `departments` and `employees` have a circular dependency:
- `departments.manager_id` references `employees.employee_id`
- `employees.department_id` references `departments.department_id`

This will require special handling during migration (load departments first without manager_id, then update).

---

## 4. PL/SQL Objects

### 4.1 Stored Procedures

#### `secure_dml`
```sql
CREATE OR REPLACE PROCEDURE secure_dml IS
BEGIN
  IF TO_CHAR (SYSDATE, 'HH24:MI') NOT BETWEEN '08:00' AND '18:00'
     OR TO_CHAR (SYSDATE, 'DY') IN ('SAT', 'SUN') THEN
    RAISE_APPLICATION_ERROR (-20205, 
      'You may only make changes during normal office hours');
  END IF;
END secure_dml;
```
**Purpose:** Enforces business hours for DML operations  
**Migration Note:** This is application logic - will need to be replicated in Azure Functions or application layer

#### `add_job_history`
```sql
CREATE OR REPLACE PROCEDURE add_job_history (
    p_emp_id          job_history.employee_id%type,
    p_start_date      job_history.start_date%type,
    p_end_date        job_history.end_date%type,
    p_job_id          job_history.job_id%type,
    p_department_id   job_history.department_id%type
) IS
BEGIN
  INSERT INTO job_history (employee_id, start_date, end_date, 
                           job_id, department_id)
  VALUES (p_emp_id, p_start_date, p_end_date, p_job_id, p_department_id);
END add_job_history;
```
**Purpose:** Inserts records into job_history table  
**Migration Note:** Simple INSERT logic - can be replaced with application code or Azure Function

### 4.2 Triggers

#### `secure_employees`
```sql
CREATE OR REPLACE TRIGGER secure_employees
  BEFORE INSERT OR UPDATE OR DELETE ON employees
BEGIN
  secure_dml;
END secure_employees;
```
**Type:** Statement-level trigger  
**Status:** DISABLED by default  
**Purpose:** Calls secure_dml procedure to enforce business hours  
**Migration Note:** Should be implemented as pre-validation in application layer

#### `update_job_history`
```sql
CREATE OR REPLACE TRIGGER update_job_history
  AFTER UPDATE OF job_id, department_id ON employees
  FOR EACH ROW
BEGIN
  add_job_history(:old.employee_id, :old.hire_date, sysdate, 
                  :old.job_id, :old.department_id);
END update_job_history;
```
**Type:** Row-level trigger  
**Purpose:** Automatically logs job changes to job_history when employee's job_id or department_id changes  
**Migration Note:** Critical business logic - must be replicated via Change Feed triggers in CosmosDB or application logic

---

## 5. Views

### `emp_details_view`
A view that joins employees, jobs, departments, locations, countries, and regions to provide comprehensive employee details.

**Migration Note:** Views will be replaced with CosmosDB queries or denormalized data structures

---

## 6. Sequences

| Sequence Name | Start Value | Increment | Max Value | Purpose |
|--------------|-------------|-----------|-----------|---------|
| `locations_seq` | 3300 | 100 | 9900 | Generate location IDs |
| `departments_seq` | 280 | 10 | 9990 | Generate department IDs |
| `employees_seq` | 207 | 1 | N/A | Generate employee IDs |

**Migration Note:** CosmosDB doesn't have sequences. Options:
1. Use Azure Functions with atomic counters in a dedicated container
2. Use GUIDs instead of sequential numbers
3. Pre-generate IDs during migration and handle new records via application logic

---

## 7. Data Characteristics

### Data Volume Estimates
- **Total records:** ~215 rows across all tables
- **Data size:** Small (< 1 MB)
- **Complexity:** Low - simple relational structure

### Data Types Used
- `NUMBER` (various precisions)
- `VARCHAR2` (various lengths)
- `CHAR` (fixed length)
- `DATE`

**Migration Note:** All Oracle data types have direct equivalents in CosmosDB (stored as JSON types)

---

## 8. Source Files Located

### SQL Scripts
- ✅ `hr_create.sql` - Table and constraint definitions
- ✅ `hr_populate.sql` - Sample data inserts
- ✅ `hr_code.sql` - Procedures and triggers
- ✅ `hr_install.sql` - Master installation script
- ✅ `hr_uninstall.sql` - Cleanup script

### Documentation
- ✅ `README.md` - Schema documentation
- ✅ Schema description with table relationships

**File Location:** `db-sample-schemas/human_resources/`

---

## 9. Special Considerations

### Circular Dependencies
- `departments` ↔ `employees` (manager relationship)
- Requires two-phase loading strategy

### Self-Referencing Foreign Keys
- `employees.manager_id` references `employees.employee_id`
- Requires careful ordering during migration

### Index Organization Table
- `countries` table uses IOT (Index-Organized Table)
- In CosmosDB, this becomes a regular document collection with indexed `country_id`

### Business Logic in Database
- Time-based access control (secure_dml)
- Automatic history tracking (triggers)
- These must be moved to application layer or Azure Functions

---

## 10. Migration Readiness Assessment

| Category | Status | Notes |
|----------|--------|-------|
| Schema Definition | ✅ Complete | All DDL scripts available |
| Sample Data | ✅ Complete | Populate scripts available |
| PL/SQL Code | ✅ Documented | 2 procedures, 2 triggers identified |
| Relationships | ✅ Mapped | All FK relationships documented |
| Data Volume | ✅ Small | Migration will be quick |
| Complexity | ✅ Low | Straightforward schema |

**Overall Assessment:** This is an excellent candidate for a simple migration. The schema is well-documented, data volume is small, and the PL/SQL logic is minimal and easily replicated in application code.

---

## Next Steps
1. ✅ Inventory complete
2. ⏭️ Move to Phase 3: Database Documentation (create detailed entity diagrams)
3. ⏭️ Move to Phase 4: Design CosmosDB data model
4. ⏭️ Move to Phase 5: Implement PySpark migration scripts

---

**Document Created:** 2025-10-21  
**Last Updated:** 2025-10-21  
**Status:** Complete

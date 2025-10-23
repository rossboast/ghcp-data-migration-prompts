# Oracle HR Schema - Database Documentation

## Executive Summary

The Oracle Human Resources (HR) schema is a well-designed relational database that manages employee information, organizational structure, and geographic data for a company. This documentation provides a comprehensive overview of the schema structure, relationships, and business logic to support migration to Azure CosmosDB.

**Schema Name:** HR (Human Resources)  
**Database Type:** Oracle Database 19c+  
**Version:** 21  
**Complexity Level:** Low to Medium  
**Data Volume:** Small (~215 rows)  
**Last Updated:** October 21, 2025

---

## Table of Contents
1. [Schema Overview](#schema-overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Table Definitions](#table-definitions)
4. [Relationships and Dependencies](#relationships-and-dependencies)
5. [Business Logic](#business-logic)
6. [Data Flows](#data-flows)
7. [Access Patterns](#access-patterns)
8. [Migration Considerations](#migration-considerations)

---

## Schema Overview

### Purpose
The HR schema models a company's human resources system, tracking:
- **Employee Management**: Personal information, job assignments, salary, reporting structure
- **Organizational Structure**: Departments, job roles, management hierarchy
- **Geographic Data**: Regions, countries, and physical locations
- **Employment History**: Historical record of job changes

### Domain Model

```
┌─────────────────────────────────────────────────────────────────┐
│                      HR SCHEMA DOMAIN MODEL                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  GEOGRAPHIC HIERARCHY          ORGANIZATIONAL HIERARCHY          │
│  ┌──────────┐                 ┌──────────────┐                 │
│  │ Regions  │                 │ Departments  │                 │
│  └────┬─────┘                 └──────┬───────┘                 │
│       │                              │                          │
│       ▼                              ▼                          │
│  ┌──────────┐                 ┌──────────────┐                 │
│  │Countries │                 │  Employees   │◄────┐           │
│  └────┬─────┘                 └──────┬───────┘     │           │
│       │                              │             │           │
│       ▼                              │             │           │
│  ┌──────────┐                       │      Self-Referencing    │
│  │Locations │◄──────────────────────┘        (Manager)         │
│  └──────────┘                                                   │
│                                                                  │
│  JOB SYSTEM                     HISTORY TRACKING                │
│  ┌──────────┐                 ┌──────────────┐                 │
│  │   Jobs   │                 │ Job History  │                 │
│  └──────────┘                 └──────────────┘                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Schema Statistics

| Metric | Value |
|--------|-------|
| Total Tables | 7 |
| Total Views | 1 |
| Total Stored Procedures | 2 |
| Total Triggers | 2 |
| Total Sequences | 3 |
| Total Indexes | 19 |
| Total Foreign Keys | 10 |
| Estimated Total Rows | ~215 |
| Estimated Data Size | < 1 MB |

---

## Entity Relationship Diagram

### Complete ER Diagram

```
┌─────────────┐
│   REGIONS   │
│─────────────│
│ region_id◄──┼─────┐
│ region_name │     │
└─────────────┘     │
                    │ FK
                    │
┌─────────────┐     │
│  COUNTRIES  │     │
│─────────────│     │
│ country_id◄─┼─────┼──────┐
│ country_name│     │      │
│ region_id───┼─────┘      │
└─────────────┘            │
                           │ FK
                           │
┌─────────────┐            │
│  LOCATIONS  │            │
│─────────────│            │
│ location_id◄┼────┬───────┼──────┐
│ street_addr │    │       │      │
│ postal_code │    │       │      │
│ city        │    │       │      │
│ state_prov  │    │       │      │
│ country_id──┼────┘       │      │
└─────────────┘            │      │
                           │      │ FK
                           │      │
┌─────────────┐            │      │
│ DEPARTMENTS │            │      │
│─────────────│            │      │
│ department◄─┼────┬───────┼──────┼──────┐
│   _id       │    │       │      │      │
│ dept_name   │    │       │      │      │
│ manager_id──┼────┼───────┼──────┼────┐ │
│ location_id─┼────┘       │      │    │ │
└─────────────┘            │      │    │ │
                           │      │    │ │
                           │      │    │ │ FK (circular)
┌─────────────┐            │      │    │ │
│    JOBS     │            │      │    │ │
│─────────────│            │      │    │ │
│ job_id◄─────┼────┐       │      │    │ │
│ job_title   │    │       │      │    │ │
│ min_salary  │    │       │      │    │ │
│ max_salary  │    │       │      │    │ │
└─────────────┘    │       │      │    │ │
                   │ FK    │ FK   │    │ │
                   │       │      │    │ │
┌─────────────┐    │       │      │    │ │
│  EMPLOYEES  │    │       │      │    │ │
│─────────────│    │       │      │    │ │
│ employee_id◄┼────┼───────┼──────┼────┼─┼──┐
│ first_name  │    │       │      │    │ │  │
│ last_name   │    │       │      │    │ │  │
│ email       │    │       │      │    │ │  │
│ phone_number│    │       │      │    │ │  │
│ hire_date   │    │       │      │    │ │  │
│ job_id──────┼────┘       │      │    │ │  │
│ salary      │            │      │    │ │  │
│ commission  │            │      │    │ │  │
│ manager_id──┼────────────┼──────┼────┘ │  │ Self-referencing FK
│ department──┼────────────┘      │      │  │
│   _id       │                   │      │  │
└─────────────┘                   │      │  │
                                  │      │  │
                                  │ FK   │  │
┌─────────────┐                   │      │  │
│JOB_HISTORY  │                   │      │  │
│─────────────│                   │      │  │
│ employee_id─┼───────────────────┘      │  │
│ start_date  │ (Composite PK)           │  │
│ end_date    │                          │  │
│ job_id──────┼──────────────────────────┘  │
│ department──┼─────────────────────────────┘
│   _id       │
└─────────────┘
```

### Relationship Summary

| From Table | To Table | Relationship Type | Cardinality | Notes |
|------------|----------|------------------|-------------|-------|
| countries | regions | Many-to-One | N:1 | Each country in one region |
| locations | countries | Many-to-One | N:1 | Each location in one country |
| departments | locations | Many-to-One | N:1 | Each dept has one location |
| departments | employees | Many-to-One | N:1 | **Circular**: Each dept has one manager (employee) |
| employees | departments | Many-to-One | N:1 | **Circular**: Each employee in one dept |
| employees | jobs | Many-to-One | N:1 | Each employee has one current job |
| employees | employees | Many-to-One | N:1 | **Self-ref**: Each employee has one manager |
| job_history | employees | Many-to-One | N:1 | Each history entry for one employee |
| job_history | jobs | Many-to-One | N:1 | Each history entry for one job |
| job_history | departments | Many-to-One | N:1 | Each history entry for one dept |

---

## Table Definitions

### 1. REGIONS

**Purpose:** Stores geographic regions for organizing countries.

**Business Description:**  
Top-level geographic categorization (e.g., Americas, Europe, Asia, Middle East and Africa).

**Schema Definition:**
```sql
CREATE TABLE regions (
    region_id      NUMBER          NOT NULL,
    region_name    VARCHAR2(25)
);
PRIMARY KEY: region_id
```

**Columns:**

| Column | Data Type | Nullable | Default | Description |
|--------|-----------|----------|---------|-------------|
| `region_id` | NUMBER | No | - | Unique identifier for the region |
| `region_name` | VARCHAR2(25) | Yes | - | Name of the region (e.g., "Europe") |

**Indexes:**
- `reg_id_pk` (UNIQUE) on `region_id`

**Sample Data:**
```
region_id | region_name
----------|------------------
1         | Europe
2         | Americas
3         | Asia
4         | Middle East and Africa
```

**Row Count:** ~4 rows

---

### 2. COUNTRIES

**Purpose:** Stores country information for locations.

**Business Description:**  
Countries where the company operates, associated with their geographic region.

**Schema Definition:**
```sql
CREATE TABLE countries (
    country_id      CHAR(2)         NOT NULL,
    country_name    VARCHAR2(60),
    region_id       NUMBER
)
ORGANIZATION INDEX;  -- Index-Organized Table (IOT)
```

**Columns:**

| Column | Data Type | Nullable | Default | Description |
|--------|-----------|----------|---------|-------------|
| `country_id` | CHAR(2) | No | - | ISO 2-letter country code (e.g., "US", "UK") |
| `country_name` | VARCHAR2(60) | Yes | - | Full country name |
| `region_id` | NUMBER | Yes | - | Foreign key to regions table |

**Constraints:**
- PRIMARY KEY: `country_id`
- FOREIGN KEY: `region_id` → `regions(region_id)`

**Special Features:**
- **Index-Organized Table (IOT)**: Data stored in B-tree index structure for faster lookups

**Sample Data:**
```
country_id | country_name        | region_id
-----------|---------------------|----------
US         | United States       | 2
UK         | United Kingdom      | 1
CA         | Canada              | 2
DE         | Germany             | 1
```

**Row Count:** ~25 rows

**Migration Note:** IOT structure will become a regular document collection in CosmosDB with indexing on `country_id`.

---

### 3. LOCATIONS

**Purpose:** Stores physical address information for company facilities.

**Business Description:**  
Physical addresses of warehouses, offices, and departments. Each location is in a specific country.

**Schema Definition:**
```sql
CREATE TABLE locations (
    location_id      NUMBER(4),
    street_address   VARCHAR2(40),
    postal_code      VARCHAR2(12),
    city             VARCHAR2(30)    NOT NULL,
    state_province   VARCHAR2(25),
    country_id       CHAR(2)
);
SEQUENCE: locations_seq (START 3300, INCREMENT 100)
```

**Columns:**

| Column | Data Type | Nullable | Default | Description |
|--------|-----------|----------|---------|-------------|
| `location_id` | NUMBER(4) | Yes | - | Unique identifier for the location |
| `street_address` | VARCHAR2(40) | Yes | - | Street address |
| `postal_code` | VARCHAR2(12) | Yes | - | Postal/ZIP code |
| `city` | VARCHAR2(30) | No | - | City name (required) |
| `state_province` | VARCHAR2(25) | Yes | - | State or province name |
| `country_id` | CHAR(2) | Yes | - | Foreign key to countries |

**Constraints:**
- PRIMARY KEY: `location_id`
- FOREIGN KEY: `country_id` → `countries(country_id)`
- NOT NULL: `city`

**Indexes:**
- `loc_id_pk` (UNIQUE) on `location_id`
- `loc_city_ix` on `city`
- `loc_state_province_ix` on `state_province`
- `loc_country_ix` on `country_id`

**ID Generation:**
- Sequence: `locations_seq` starting at 3300, increment by 100

**Sample Data:**
```
location_id | street_address       | city        | state_province | country_id
------------|---------------------|-------------|----------------|------------
1400        | 2014 Jabberwocky Rd | Southlake   | Texas          | US
1500        | 2011 Interiors Blvd | South San   | California     | US
1700        | 2004 Charade Rd     | Seattle     | Washington     | US
```

**Row Count:** ~23 rows

---

### 4. DEPARTMENTS

**Purpose:** Stores company department information.

**Business Description:**  
Organizational units within the company. Each department has a name, a location, and optionally a manager (employee).

**Schema Definition:**
```sql
CREATE TABLE departments (
    department_id    NUMBER(4),
    department_name  VARCHAR2(30)    NOT NULL,
    manager_id       NUMBER(6),
    location_id      NUMBER(4)
);
SEQUENCE: departments_seq (START 280, INCREMENT 10)
```

**Columns:**

| Column | Data Type | Nullable | Default | Description |
|--------|-----------|----------|---------|-------------|
| `department_id` | NUMBER(4) | Yes | - | Unique identifier for the department |
| `department_name` | VARCHAR2(30) | No | - | Name of the department |
| `manager_id` | NUMBER(6) | Yes | - | Foreign key to employees (department manager) |
| `location_id` | NUMBER(4) | Yes | - | Foreign key to locations |

**Constraints:**
- PRIMARY KEY: `department_id`
- FOREIGN KEY: `manager_id` → `employees(employee_id)` ⚠️ **CIRCULAR**
- FOREIGN KEY: `location_id` → `locations(location_id)`
- NOT NULL: `department_name`

**Indexes:**
- `dept_id_pk` (UNIQUE) on `department_id`
- `dept_location_ix` on `location_id`

**ID Generation:**
- Sequence: `departments_seq` starting at 280, increment by 10

**Sample Data:**
```
department_id | department_name     | manager_id | location_id
--------------|---------------------|------------|-------------
10            | Administration      | 200        | 1700
20            | Marketing           | 201        | 1800
50            | Shipping            | 124        | 1500
60            | IT                  | 103        | 1400
```

**Row Count:** ~27 rows

**⚠️ Migration Warning:** Circular dependency with employees table requires two-phase loading.

---

### 5. JOBS

**Purpose:** Stores job role definitions.

**Business Description:**  
Job titles and salary ranges for positions within the company. Each employee is assigned to one job.

**Schema Definition:**
```sql
CREATE TABLE jobs (
    job_id         VARCHAR2(10),
    job_title      VARCHAR2(35)    NOT NULL,
    min_salary     NUMBER(6),
    max_salary     NUMBER(6)
);
```

**Columns:**

| Column | Data Type | Nullable | Default | Description |
|--------|-----------|----------|---------|-------------|
| `job_id` | VARCHAR2(10) | Yes | - | Unique code for the job (e.g., "IT_PROG") |
| `job_title` | VARCHAR2(35) | No | - | Full job title |
| `min_salary` | NUMBER(6) | Yes | - | Minimum salary for this role |
| `max_salary` | NUMBER(6) | Yes | - | Maximum salary for this role |

**Constraints:**
- PRIMARY KEY: `job_id`
- NOT NULL: `job_title`

**Indexes:**
- `job_id_pk` (UNIQUE) on `job_id`

**Sample Data:**
```
job_id    | job_title                | min_salary | max_salary
----------|--------------------------|------------|------------
AD_PRES   | President                | 20000      | 40000
AD_VP     | Administration VP        | 15000      | 30000
IT_PROG   | Programmer               | 4000       | 10000
SA_REP    | Sales Representative     | 6000       | 12000
```

**Row Count:** ~19 rows

---

### 6. EMPLOYEES

**Purpose:** Stores employee information.

**Business Description:**  
Core table containing all employee personnel information including personal details, job assignment, salary, and reporting structure.

**Schema Definition:**
```sql
CREATE TABLE employees (
    employee_id    NUMBER(6),
    first_name     VARCHAR2(20),
    last_name      VARCHAR2(25)    NOT NULL,
    email          VARCHAR2(25)    NOT NULL UNIQUE,
    phone_number   VARCHAR2(20),
    hire_date      DATE            NOT NULL,
    job_id         VARCHAR2(10)    NOT NULL,
    salary         NUMBER(8,2),
    commission_pct NUMBER(2,2),
    manager_id     NUMBER(6),
    department_id  NUMBER(4)
);
SEQUENCE: employees_seq (START 207, INCREMENT 1)
```

**Columns:**

| Column | Data Type | Nullable | Default | Description |
|--------|-----------|----------|---------|-------------|
| `employee_id` | NUMBER(6) | Yes | - | Unique identifier for the employee |
| `first_name` | VARCHAR2(20) | Yes | - | Employee's first name |
| `last_name` | VARCHAR2(25) | No | - | Employee's last name (required) |
| `email` | VARCHAR2(25) | No | - | Email address (unique) |
| `phone_number` | VARCHAR2(20) | Yes | - | Contact phone number |
| `hire_date` | DATE | No | - | Date employee was hired |
| `job_id` | VARCHAR2(10) | No | - | Foreign key to jobs |
| `salary` | NUMBER(8,2) | Yes | - | Current salary |
| `commission_pct` | NUMBER(2,2) | Yes | - | Commission percentage (0.00-0.99) |
| `manager_id` | NUMBER(6) | Yes | - | Foreign key to employees (self-ref) |
| `department_id` | NUMBER(4) | Yes | - | Foreign key to departments |

**Constraints:**
- PRIMARY KEY: `employee_id`
- FOREIGN KEY: `department_id` → `departments(department_id)` ⚠️ **CIRCULAR**
- FOREIGN KEY: `job_id` → `jobs(job_id)`
- FOREIGN KEY: `manager_id` → `employees(employee_id)` ⚠️ **SELF-REFERENCING**
- UNIQUE: `email`
- NOT NULL: `last_name`, `email`, `hire_date`, `job_id`
- CHECK: `salary > 0`

**Indexes:**
- `emp_emp_id_pk` (UNIQUE) on `employee_id`
- `emp_email_uk` (UNIQUE) on `email`
- `emp_department_ix` on `department_id`
- `emp_job_ix` on `job_id`
- `emp_manager_ix` on `manager_id`
- `emp_name_ix` on `last_name`, `first_name`

**ID Generation:**
- Sequence: `employees_seq` starting at 207, increment by 1

**Sample Data:**
```
employee_id | first_name | last_name | email    | hire_date  | job_id  | salary | manager_id | department_id
------------|------------|-----------|----------|------------|---------|--------|------------|---------------
100         | Steven     | King      | SKING    | 2003-06-17 | AD_PRES | 24000  | NULL       | 90
101         | Neena      | Kochhar   | NKOCHHAR | 2005-09-21 | AD_VP   | 17000  | 100        | 90
102         | Lex        | De Haan   | LDEHAAN  | 2001-01-13 | AD_VP   | 17000  | 100        | 90
```

**Row Count:** ~107 rows

**⚠️ Migration Warnings:**
1. Circular dependency with departments table
2. Self-referencing foreign key (manager hierarchy)
3. NULL manager_id indicates top-level executives

---

### 7. JOB_HISTORY

**Purpose:** Tracks historical job assignments for employees.

**Business Description:**  
Audit trail of employee job changes. When an employee changes jobs or departments, a record is automatically created via trigger.

**Schema Definition:**
```sql
CREATE TABLE job_history (
    employee_id     NUMBER(6)       NOT NULL,
    start_date      DATE            NOT NULL,
    end_date        DATE            NOT NULL,
    job_id          VARCHAR2(10)    NOT NULL,
    department_id   NUMBER(4)
);
```

**Columns:**

| Column | Data Type | Nullable | Default | Description |
|--------|-----------|----------|---------|-------------|
| `employee_id` | NUMBER(6) | No | - | Foreign key to employees |
| `start_date` | DATE | No | - | Start date of this job assignment |
| `end_date` | DATE | No | - | End date of this job assignment |
| `job_id` | VARCHAR2(10) | No | - | Foreign key to jobs |
| `department_id` | NUMBER(4) | Yes | - | Foreign key to departments |

**Constraints:**
- PRIMARY KEY: (`employee_id`, `start_date`) ⚠️ **COMPOSITE KEY**
- FOREIGN KEY: `employee_id` → `employees(employee_id)`
- FOREIGN KEY: `job_id` → `jobs(job_id)`
- FOREIGN KEY: `department_id` → `departments(department_id)`
- NOT NULL: `employee_id`, `start_date`, `end_date`, `job_id`
- CHECK: `end_date > start_date`

**Indexes:**
- `jhist_emp_id_st_date_pk` (UNIQUE) on `employee_id`, `start_date`
- `jhist_employee_ix` on `employee_id`
- `jhist_job_ix` on `job_id`
- `jhist_department_ix` on `department_id`

**Sample Data:**
```
employee_id | start_date  | end_date    | job_id  | department_id
------------|-------------|-------------|---------|---------------
102         | 2001-01-13  | 2006-07-24  | IT_PROG | 60
101         | 1997-09-21  | 2001-10-27  | AC_ACCOUNT | 110
101         | 2001-10-28  | 2005-03-15  | AC_MGR  | 110
```

**Row Count:** ~10 rows

**🔔 Business Logic:** This table is automatically populated by the `update_job_history` trigger when an employee's job or department changes.

---

## Relationships and Dependencies

### Foreign Key Relationships

#### Standard Relationships
```
regions (1) ←──── (N) countries
countries (1) ←──── (N) locations
locations (1) ←──── (N) departments
jobs (1) ←──── (N) employees
jobs (1) ←──── (N) job_history
```

#### Circular Relationship
```
departments (1) ←──── (N) employees
    ↑                      │
    │                      │ manager_id
    └──────────────────────┘
```
**Resolution:** Load departments first with NULL manager_id, then load employees, then update departments.manager_id.

#### Self-Referencing Relationship
```
employees (1) ←──── (N) employees
   (manager)            (subordinates)
```
**Resolution:** Load employees in hierarchical order (top-down) or load all then update manager_id.

### Dependency Graph

```
Migration Order:
┌─────────────────────────────────────────────────┐
│ Phase 1: Independent Tables                     │
├─────────────────────────────────────────────────┤
│ 1. regions                                      │
│ 2. countries (depends on regions)               │
│ 3. locations (depends on countries)             │
│ 4. jobs                                         │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Phase 2: Circular Dependencies                   │
├─────────────────────────────────────────────────┤
│ 5a. departments (without manager_id)            │
│ 5b. employees (without manager_id)              │
│ 5c. departments.manager_id UPDATE               │
│ 5d. employees.manager_id UPDATE                 │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Phase 3: Dependent Tables                       │
├─────────────────────────────────────────────────┤
│ 6. job_history (depends on employees, jobs,     │
│                 departments)                    │
└─────────────────────────────────────────────────┘
```

---

## Business Logic

### Stored Procedures

#### 1. secure_dml

**Purpose:** Enforce business hours for database modifications.

**Logic:**
```sql
IF current_time NOT BETWEEN 08:00 AND 18:00
   OR current_day IN (Saturday, Sunday)
THEN
   RAISE ERROR: "You may only make changes during normal office hours"
END IF
```

**Business Rule:** Data modifications only allowed Monday-Friday, 8 AM - 6 PM.

**Migration Strategy:** Move to Azure Functions or application layer with time-based validation.

---

#### 2. add_job_history

**Purpose:** Insert a record into job_history table.

**Parameters:**
- `p_emp_id`: Employee ID
- `p_start_date`: Start date
- `p_end_date`: End date
- `p_job_id`: Job ID
- `p_department_id`: Department ID

**Logic:**
```sql
INSERT INTO job_history 
VALUES (p_emp_id, p_start_date, p_end_date, p_job_id, p_department_id);
```

**Migration Strategy:** Replace with application code or Azure Function.

---

### Triggers

#### 1. secure_employees

**Type:** BEFORE INSERT OR UPDATE OR DELETE (Statement-Level)  
**Target:** employees table  
**Status:** DISABLED by default

**Purpose:** Call secure_dml procedure before any DML on employees.

**Logic:**
```sql
BEFORE INSERT OR UPDATE OR DELETE ON employees
BEGIN
  secure_dml();  -- Check business hours
END
```

**Migration Strategy:** Implement as pre-validation in application layer or Azure Functions.

---

#### 2. update_job_history

**Type:** AFTER UPDATE (Row-Level)  
**Target:** employees table  
**Fires On:** UPDATE of job_id OR department_id

**Purpose:** Automatically log job changes to job_history when employee changes jobs or departments.

**Logic:**
```sql
AFTER UPDATE OF job_id, department_id ON employees
FOR EACH ROW
BEGIN
  INSERT INTO job_history
  VALUES (:OLD.employee_id, :OLD.hire_date, SYSDATE, 
          :OLD.job_id, :OLD.department_id);
END
```

**Business Rule:** Maintain complete audit trail of employee job changes.

**Migration Strategy:**
- Option 1: Use CosmosDB Change Feed with Azure Functions to detect changes and insert history
- Option 2: Implement in application layer before updating employee
- Option 3: Store history as nested array within employee document (denormalization)

**⚠️ Critical:** This is important business logic that must be preserved in migration.

---

### Views

#### emp_details_view

**Purpose:** Consolidated view of employee information with related data.

**Query:**
```sql
SELECT 
  e.employee_id, e.first_name, e.last_name, e.email,
  e.phone_number, e.hire_date, e.salary,
  j.job_title,
  d.department_name,
  l.city, l.state_province,
  c.country_name,
  r.region_name
FROM employees e
JOIN jobs j ON e.job_id = j.job_id
JOIN departments d ON e.department_id = d.department_id
JOIN locations l ON d.location_id = l.location_id
JOIN countries c ON l.country_id = c.country_id
JOIN regions r ON c.region_id = r.region_id
```

**Usage:** Frequently used for reporting and display purposes.

**Migration Strategy:**
- Option 1: Denormalize data in CosmosDB (embed related data in employee documents)
- Option 2: Query across containers (less efficient)
- Option 3: Create materialized view in separate container updated via Change Feed

---

## Data Flows

### Employee Lifecycle

```
1. HIRE NEW EMPLOYEE
   ┌─────────────────────────────────────────────┐
   │ 1. Generate employee_id from sequence       │
   │ 2. INSERT INTO employees                    │
   │    - Assign to department                   │
   │    - Assign to job                          │
   │    - Set manager                            │
   │    - Set hire_date = today                  │
   └─────────────────────────────────────────────┘

2. JOB CHANGE
   ┌─────────────────────────────────────────────┐
   │ 1. UPDATE employees                         │
   │    - Change job_id OR department_id         │
   │                                             │
   │ 2. TRIGGER: update_job_history fires        │
   │    - Automatically creates job_history row  │
   │    - Records old job/dept and dates         │
   └─────────────────────────────────────────────┘

3. PROMOTION TO MANAGER
   ┌─────────────────────────────────────────────┐
   │ 1. UPDATE departments                       │
   │    - SET manager_id = employee_id           │
   │                                             │
   │ 2. UPDATE employees (subordinates)          │
   │    - SET manager_id = new manager           │
   └─────────────────────────────────────────────┘

4. TERMINATION
   ┌─────────────────────────────────────────────┐
   │ 1. UPDATE employees                         │
   │    - SET department_id = NULL               │
   │    - SET job_id = 'TERMINATED'              │
   │    (Or DELETE employee record)              │
   │                                             │
   │ 2. TRIGGER: update_job_history fires        │
   │    - Records final job assignment           │
   └─────────────────────────────────────────────┘
```

### Department Creation Flow

```
1. CREATE NEW DEPARTMENT
   ┌─────────────────────────────────────────────┐
   │ 1. Generate department_id from sequence     │
   │ 2. INSERT INTO departments                  │
   │    - department_name (required)             │
   │    - location_id                            │
   │    - manager_id = NULL (initially)          │
   └─────────────────────────────────────────────┘

2. ASSIGN MANAGER
   ┌─────────────────────────────────────────────┐
   │ 1. UPDATE departments                       │
   │    - SET manager_id = employee_id           │
   │                                             │
   │ 2. UPDATE employees (manager)               │
   │    - SET department_id = new dept (if diff) │
   └─────────────────────────────────────────────┘
```

---

## Access Patterns

### Common Query Patterns

#### 1. Employee Lookup
```sql
-- By ID
SELECT * FROM employees WHERE employee_id = ?

-- By email
SELECT * FROM employees WHERE email = ?

-- By name
SELECT * FROM employees 
WHERE last_name = ? AND first_name = ?
```
**Indexes Used:** `emp_emp_id_pk`, `emp_email_uk`, `emp_name_ix`

---

#### 2. Department Employees
```sql
SELECT * FROM employees 
WHERE department_id = ?
ORDER BY last_name, first_name
```
**Index Used:** `emp_department_ix`

---

#### 3. Manager's Direct Reports
```sql
SELECT * FROM employees 
WHERE manager_id = ?
ORDER BY last_name, first_name
```
**Index Used:** `emp_manager_ix`

---

#### 4. Employee Full Details (with joins)
```sql
SELECT e.*, j.job_title, d.department_name, l.city
FROM employees e
JOIN jobs j ON e.job_id = j.job_id
JOIN departments d ON e.department_id = d.department_id
JOIN locations l ON d.location_id = l.location_id
WHERE e.employee_id = ?
```
**View Alternative:** `emp_details_view`

---

#### 5. Employee Job History
```sql
SELECT jh.*, j.job_title, d.department_name
FROM job_history jh
JOIN jobs j ON jh.job_id = j.job_id
JOIN departments d ON jh.department_id = d.department_id
WHERE jh.employee_id = ?
ORDER BY jh.start_date DESC
```
**Index Used:** `jhist_employee_ix`

---

#### 6. Departments by Location
```sql
SELECT d.*, l.city, l.state_province, c.country_name
FROM departments d
JOIN locations l ON d.location_id = l.location_id
JOIN countries c ON l.country_id = c.country_id
WHERE c.country_id = ?
```
**Index Used:** `dept_loc_fk`, `loc_country_ix`

---

#### 7. Employees in Salary Range
```sql
SELECT e.*, j.job_title
FROM employees e
JOIN jobs j ON e.job_id = j.job_id
WHERE e.salary BETWEEN j.min_salary AND j.max_salary
  AND j.job_id = ?
```

---

### CosmosDB Access Pattern Implications

For efficient CosmosDB queries, consider these patterns:

1. **Employee Lookup** → Partition by `employee_id` or `department_id`
2. **Department Queries** → Partition by `department_id`
3. **Manager Hierarchy** → May require cross-partition queries (less efficient)
4. **Job History** → Embed in employee document OR separate container with partition key `employee_id`

---

## Migration Considerations

### Critical Issues

#### 1. Circular Dependency (departments ↔ employees)

**Problem:** Cannot load departments without employees (manager_id FK), cannot load employees without departments (department_id FK).

**Solutions:**
- **Option A (Two-Phase):** Load departments with NULL manager_id → Load employees → Update departments.manager_id
- **Option B (Defer Constraints):** Disable FK constraints during load, re-enable after
- **Option C (CosmosDB):** No FK constraints, load in any order, resolve references in application

**Recommended:** Option A for data integrity

---

#### 2. Self-Referencing FK (employees.manager_id)

**Problem:** Cannot load employees without their managers existing first.

**Solutions:**
- **Option A (Hierarchical):** Load in order: CEO (no manager) → VPs → Managers → Employees
- **Option B (Two-Phase):** Load all employees with NULL manager_id → Update manager_id in second pass
- **Option C (Topological Sort):** Analyze dependency graph and load in correct order

**Recommended:** Option A or B depending on data completeness

---

#### 3. Sequences → ID Generation

**Problem:** Oracle sequences don't exist in CosmosDB.

**Solutions:**
- **Option A (GUIDs):** Use GUIDs for new records (breaks existing ID structure)
- **Option B (Counter Container):** Maintain counter documents in CosmosDB
- **Option C (Pre-Generation):** Generate all IDs during migration, handle new records in application
- **Option D (Azure Functions):** Implement sequence service as Azure Function with atomic operations

**Recommended:** Option C for migration + Option D for new records

---

#### 4. Triggers → Business Logic

**Problem:** Database triggers don't exist in CosmosDB.

**Solutions:**
- **Option A (Change Feed):** Use CosmosDB Change Feed with Azure Functions to detect changes and perform actions
- **Option B (Application Layer):** Move logic to application code
- **Option C (Stored Procedures):** CosmosDB stored procedures (JavaScript, limited functionality)

**Recommended:** Option A for `update_job_history` trigger (critical audit trail)

---

#### 5. Views → Data Access

**Problem:** Views don't exist in CosmosDB.

**Solutions:**
- **Option A (Denormalization):** Embed related data in documents (e.g., employee document contains job, department info)
- **Option B (Materialized Views):** Create separate container with pre-joined data, updated via Change Feed
- **Option C (Application Joins):** Perform joins in application layer (multiple queries)

**Recommended:** Option A (denormalization) for read-heavy workloads

---

#### 6. Referential Integrity

**Problem:** CosmosDB doesn't enforce foreign key constraints.

**Solutions:**
- **Option A (Application Validation):** Validate references in application layer before writes
- **Option B (Azure Functions):** Pre-write validation functions
- **Option C (Accept Risk):** Allow orphaned references, handle in queries

**Recommended:** Option A for critical relationships (employee → department, employee → job)

---

### Data Model Design for CosmosDB

#### Option 1: Normalized (Relational-like)

**Structure:** 7 separate containers, similar to tables

**Pros:**
- Easy migration
- Flexible updates
- Lower storage

**Cons:**
- Multiple queries for related data
- Higher RU consumption
- No referential integrity

---

#### Option 2: Denormalized (Recommended)

**Structure:** 
- **employees** container (partition key: `department_id` or `employee_id`)
  - Embed: job info, department info, location info, manager info
  - Nested array: job_history[]
- **departments** container
- **locations** container
- **jobs** container

**Pros:**
- Single query for employee details
- Lower RU consumption for reads
- Better performance

**Cons:**
- Data duplication
- Update complexity (must update multiple docs)
- Larger document size

---

#### Option 3: Hybrid

**Structure:**
- **employees** container with embedded job_history
- **reference_data** container for jobs, departments, locations, countries, regions
- Use Azure Cache for Redis for reference data lookups

**Pros:**
- Balance between normalization and denormalization
- Reference data changes infrequently
- Good query performance

---

### Recommended CosmosDB Design

```json
// employees container (partition key: department_id)
{
  "id": "100",
  "employee_id": 100,
  "first_name": "Steven",
  "last_name": "King",
  "email": "SKING",
  "phone_number": "515.123.4567",
  "hire_date": "2003-06-17",
  "salary": 24000,
  "commission_pct": null,
  
  // Embedded job info (denormalized)
  "job": {
    "job_id": "AD_PRES",
    "job_title": "President",
    "min_salary": 20000,
    "max_salary": 40000
  },
  
  // Embedded department info (denormalized)
  "department": {
    "department_id": 90,
    "department_name": "Executive"
  },
  
  // Embedded manager info (optional)
  "manager": null,
  
  // Nested job history array
  "job_history": [
    {
      "start_date": "2001-01-13",
      "end_date": "2003-06-16",
      "job_id": "AD_VP",
      "job_title": "Administration VP",
      "department_id": 90,
      "department_name": "Executive"
    }
  ],
  
  // Metadata
  "created_date": "2025-10-21T00:00:00Z",
  "modified_date": "2025-10-21T00:00:00Z",
  "type": "employee"
}
```

---

## Summary

The Oracle HR schema is a well-designed, straightforward relational database that is an excellent candidate for migration to Azure CosmosDB. Key considerations:

### Strengths
✅ Small data volume (~215 rows)  
✅ Clear business logic  
✅ Well-documented schema  
✅ Comprehensive sample data available  

### Challenges
⚠️ Circular dependencies (departments ↔ employees)  
⚠️ Self-referencing relationships (manager hierarchy)  
⚠️ Active triggers for business logic  
⚠️ Sequences for ID generation  

### Migration Approach
1. **Extract** all data from Oracle
2. **Transform** to denormalized JSON documents
3. **Resolve** circular and self-referencing relationships
4. **Load** into CosmosDB containers
5. **Implement** trigger logic via Azure Functions + Change Feed
6. **Test** all access patterns and business rules

---

**Next Phase:** Migration Planning (Phase 4)  
- Design CosmosDB container strategy
- Define partition keys
- Plan data transformation logic
- Create PySpark migration scripts

---

**Document Version:** 1.0  
**Created:** October 21, 2025  
**Last Updated:** October 21, 2025  
**Status:** ✅ Complete

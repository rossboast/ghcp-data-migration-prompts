# HR Schema - Entity Relationship Diagrams

This document contains various ER diagrams visualizing the Oracle HR schema relationships using Mermaid syntax.

> **Note:** These Mermaid diagrams will render interactively in GitHub, VS Code (with Mermaid extension), and other Markdown viewers that support Mermaid.

---

## Complete Schema Diagram

```mermaid
erDiagram
    REGIONS ||--o{ COUNTRIES : contains
    COUNTRIES ||--o{ LOCATIONS : "has offices in"
    LOCATIONS ||--o{ DEPARTMENTS : "houses"
    JOBS ||--o{ EMPLOYEES : "assigned to"
    DEPARTMENTS ||--o{ EMPLOYEES : "works in"
    DEPARTMENTS ||--o| EMPLOYEES : "managed by"
    EMPLOYEES ||--o{ EMPLOYEES : "reports to"
    EMPLOYEES ||--o{ JOB_HISTORY : "has history"
    JOBS ||--o{ JOB_HISTORY : "tracks"
    DEPARTMENTS ||--o{ JOB_HISTORY : "involved in"

    REGIONS {
        number region_id PK
        varchar region_name
    }
    
    COUNTRIES {
        char country_id PK "ISO 2-letter code"
        varchar country_name
        number region_id FK
    }
    
    LOCATIONS {
        number location_id PK "SEQ:3300+100"
        varchar street_address
        varchar postal_code
        varchar city "NOT NULL"
        varchar state_province
        char country_id FK
    }
    
    DEPARTMENTS {
        number department_id PK "SEQ:280+10"
        varchar department_name "NOT NULL"
        number manager_id FK "Circular with EMPLOYEES"
        number location_id FK
    }
    
    JOBS {
        varchar job_id PK
        varchar job_title "NOT NULL"
        number min_salary
        number max_salary
    }
    
    EMPLOYEES {
        number employee_id PK "SEQ:207+1"
        varchar first_name
        varchar last_name "NOT NULL"
        varchar email "UNIQUE, NOT NULL"
        varchar phone_number
        date hire_date "NOT NULL"
        varchar job_id FK "NOT NULL"
        number salary "CHECK > 0"
        number commission_pct
        number manager_id FK "Self-referencing"
        number department_id FK
    }
    
    JOB_HISTORY {
        number employee_id PK_FK "Composite PK"
        date start_date PK "Composite PK"
        date end_date "CHECK > start_date"
        varchar job_id FK
        number department_id FK
    }
```

---

## Geographic Hierarchy

```mermaid
graph TD
    R["REGIONS
    ~4 rows
    Examples:
    Europe, Americas
    Asia, Middle East"]
    
    R -->|1:N| C1[US - United States]
    R -->|1:N| C2[UK - United Kingdom]
    R -->|1:N| C3[CA - Canada]
    R -->|1:N| C4[DE - Germany]
    R -->|1:N| C5[... 21 more countries]
    
    C1 -->|1:N| L1["1400: Southlake, Texas"]
    C1 -->|1:N| L2["1500: South San Francisco, CA"]
    C1 -->|1:N| L3["1700: Seattle, Washington"]
    C2 -->|1:N| L4["2400: London"]
    C3 -->|1:N| L5[... more locations]
    
    style R fill:#e1f5ff
    style C1 fill:#fff4e1
    style C2 fill:#fff4e1
    style C3 fill:#fff4e1
    style C4 fill:#fff4e1
    style C5 fill:#fff4e1
    style L1 fill:#e8f5e9
    style L2 fill:#e8f5e9
    style L3 fill:#e8f5e9
    style L4 fill:#e8f5e9
    style L5 fill:#e8f5e9
```

**Access Pattern:** `regions → countries → locations`  
**Use Case:** "Find all office locations in Europe"

---

## Organizational Hierarchy

```mermaid
graph TB
    subgraph "Reference Data"
        JOBS["JOBS
        job_id, job_title
        min_salary, max_salary"]
        DEPT["DEPARTMENTS
        department_id
        department_name
        location_id"]
    end
    
    subgraph "Circular Dependency Challenge"
        DEPT -->|"manager_id
        N:1"| EMP["EMPLOYEES
        employee_id
        first_name, last_name
        email, hire_date
        salary"]
        EMP -->|"department_id
        N:1"| DEPT
    end
    
    JOBS -->|"job_id
    1:N"| EMP
    EMP -->|"manager_id
    Self-Referencing"| EMP
    
    style JOBS fill:#e1f5ff
    style DEPT fill:#fff4e1
    style EMP fill:#e8f5e9
```

### Management Hierarchy Example

```mermaid
graph TD
    CEO["Steven King
    CEO
    employee_id: 100
    manager_id: NULL"]
    
    CEO --> VP1["Neena Kochhar
    VP
    employee_id: 101
    manager_id: 100"]
    
    CEO --> VP2["Lex De Haan
    VP
    employee_id: 102
    manager_id: 100"]
    
    VP1 --> MGR1["Nancy Greenberg
    Manager
    employee_id: 108
    manager_id: 101"]
    
    MGR1 --> EMP1["Daniel Faviet
    employee_id: 109
    manager_id: 108"]
    
    MGR1 --> EMP2["John Chen
    employee_id: 110
    manager_id: 108"]
    
    style CEO fill:#ff6b6b
    style VP1 fill:#4ecdc4
    style VP2 fill:#4ecdc4
    style MGR1 fill:#95e1d3
    style EMP1 fill:#f9f9f9
    style EMP2 fill:#f9f9f9
```

**⚠️ Circular Dependency Challenge:**
- `departments.manager_id` → `employees.employee_id`
- `employees.department_id` → `departments.department_id`

---

## Employee Detail Relationships

### Six-Way Join for Complete Employee Information

```mermaid
graph LR
    E["EMPLOYEES
    Core Data"]
    J["JOBS
    job_title"]
    D["DEPARTMENTS
    dept_name"]
    L["LOCATIONS
    city, state"]
    C["COUNTRIES
    country_name"]
    R["REGIONS
    region_name"]
    M["EMPLOYEES
    Manager Info"]
    
    E -->|job_id| J
    E -->|department_id| D
    D -->|location_id| L
    L -->|country_id| C
    C -->|region_id| R
    E -->|manager_id| M
    
    style E fill:#e8f5e9
    style J fill:#e1f5ff
    style D fill:#fff4e1
    style L fill:#ffe1e1
    style C fill:#f3e5f5
    style R fill:#e0f2f1
    style M fill:#fff9c4
```

### SQL Query Pattern

```sql
SELECT 
    e.employee_id, 
    e.first_name, 
    e.last_name,
    e.email,
    e.hire_date,
    e.salary,
    j.job_title,                    -- JOIN 1: jobs
    d.department_name,              -- JOIN 2: departments
    l.city, 
    l.state_province,               -- JOIN 3: locations
    c.country_name,                 -- JOIN 4: countries
    r.region_name,                  -- JOIN 5: regions
    m.first_name || ' ' || 
    m.last_name as manager_name     -- JOIN 6: employees (self)
FROM employees e
JOIN jobs j ON e.job_id = j.job_id
JOIN departments d ON e.department_id = d.department_id
JOIN locations l ON d.location_id = l.location_id
JOIN countries c ON l.country_id = c.country_id
JOIN regions r ON c.region_id = r.region_id
LEFT JOIN employees m ON e.manager_id = m.employee_id
WHERE e.employee_id = ?
```

### CosmosDB Denormalized Document

```mermaid
graph TD
    DOC[Employee Document]
    
    DOC --> CORE["Core Fields
    employee_id, name
    email, hire_date
    salary"]
    DOC --> JOB["Embedded Job
    job_id, job_title
    min_salary, max_salary"]
    DOC --> DEPT["Embedded Department
    department_id
    department_name"]
    DOC --> LOC["Embedded Location
    city, state_province
    country_name
    region_name"]
    DOC --> MGR["Embedded Manager
    manager_id
    manager_name"]
    DOC --> HIST["Job History Array
    start_date, end_date
    previous jobs"]
    
    style DOC fill:#4caf50,color:#fff
    style CORE fill:#e8f5e9
    style JOB fill:#e1f5ff
    style DEPT fill:#fff4e1
    style LOC fill:#ffe1e1
    style MGR fill:#fff9c4
    style HIST fill:#f3e5f5
```

**💡 CosmosDB Implication:**  
Six-way join in relational model → **Single document read** in CosmosDB through denormalization

---

## Job History Tracking

### Oracle Trigger Mechanism

```mermaid
sequenceDiagram
    participant App as Application
    participant Emp as EMPLOYEES Table
    participant Trg as update_job_history TRIGGER
    participant Proc as add_job_history PROCEDURE
    participant Hist as JOB_HISTORY Table
    
    App->>Emp: UPDATE employees<br/>SET job_id='IT_MANAGER'<br/>WHERE employee_id=101
    
    Note over Emp: BEFORE: job_id='IT_PROG'
    Note over Emp: AFTER: job_id='IT_MANAGER'
    
    Emp->>Trg: AFTER UPDATE trigger fires
    
    Trg->>Proc: Call add_job_history()<br/>with OLD values
    
    Note over Proc: Parameters:<br/>- emp_id: 101<br/>- start: OLD.hire_date<br/>- end: SYSDATE<br/>- job_id: 'IT_PROG'<br/>- dept_id: OLD.dept
    
    Proc->>Hist: INSERT INTO job_history
    
    Hist-->>App: Success
```

### Example Flow

```mermaid
stateDiagram-v2
    [*] --> Initial
    Initial --> Updating
    Updating --> TriggerFired
    TriggerFired --> HistoryCreated
    HistoryCreated --> Complete
    Complete --> [*]
    
    note right of Initial
        Employee 101
        Job: IT_PROG
        Dept: 60
    end note
    
    note right of Updating
        UPDATE job_id
        to IT_MANAGER
    end note
    
    note right of TriggerFired
        AFTER UPDATE
        trigger activates
    end note
    
    note right of HistoryCreated
        INSERT job_history:
        - emp: 101
        - start: 2020-01-01
        - end: 2025-10-21
        - old job: IT_PROG
        - old dept: 60
    end note
    
    note right of Complete
        Employee updated
        History preserved
    end note
```

### CosmosDB Migration Solutions

```mermaid
graph TB
    subgraph "Option A: Change Feed + Azure Functions"
        CF["CosmosDB
        Change Feed"]
        AF["Azure Function
        Triggered by changes"]
        HC["job_history
        container"]
        
        CF -->|"Detects job_id or
        department_id change"| AF
        AF -->|Inserts history record| HC
    end
    
    subgraph "Option B: Application Layer"
        AL[Application Code]
        EMP["employees
        container"]
        HIS["job_history
        container"]
        
        AL -->|1. Insert history| HIS
        AL -->|2. Update employee| EMP
    end
    
    subgraph "Option C: Denormalization (Recommended)"
        DOC[Employee Document]
        ARR["job_history
        nested array"]
        
        DOC -->|Contains| ARR
        ARR -->|"Append on
        job change"| ARR
    end
    
    style CF fill:#e1f5ff
    style AF fill:#4caf50,color:#fff
    style AL fill:#ff9800,color:#fff
    style DOC fill:#9c27b0,color:#fff
```

**⚠️ Migration Challenge:** CosmosDB doesn't have triggers that fire on UPDATE  
**✅ Recommended Solution:** Option C (Denormalization) or Option A (Change Feed)

---

## Partition Key Strategy for CosmosDB

### Option 1: Partition by department_id

```mermaid
graph LR
    subgraph "Partition: dept_10 (Admin)"
        E100[Employee 100]
        E200[Employee 200]
        E203[Employee 203]
    end
    
    subgraph "Partition: dept_20 (Marketing)"
        E201[Employee 201]
        E202[Employee 202]
        E204[Employee 204]
    end
    
    subgraph "Partition: dept_50 (Shipping)"
        E124[Employee 124]
        E125[Employee 125]
        E126[Employee 126]
    end
    
    style E100 fill:#e8f5e9
    style E200 fill:#e8f5e9
    style E203 fill:#e8f5e9
    style E201 fill:#fff4e1
    style E202 fill:#fff4e1
    style E204 fill:#fff4e1
    style E124 fill:#e1f5ff
    style E125 fill:#e1f5ff
    style E126 fill:#e1f5ff
```

**Pros:**
- ✅ Efficient for "get all employees in department"
- ✅ Natural grouping
- ✅ Manager queries efficient (if manager in same dept)

**Cons:**
- ❌ Cross-partition query for manager hierarchy
- ❌ Uneven distribution (some depts larger than others)
- ❌ Hot partitions possible

---

### Option 2: Partition by employee_id

```mermaid
graph LR
    subgraph "Partition: emp_100"
        E100["Employee 100
        + job_history array"]
    end
    
    subgraph "Partition: emp_101"
        E101["Employee 101
        + job_history array"]
    end
    
    subgraph "Partition: emp_102"
        E102["Employee 102
        + job_history array"]
    end
    
    subgraph "Partition: emp_103"
        E103["Employee 103
        + job_history array"]
    end
    
    style E100 fill:#4caf50,color:#fff
    style E101 fill:#2196f3,color:#fff
    style E102 fill:#ff9800,color:#fff
    style E103 fill:#9c27b0,color:#fff
```

**Pros:**
- ✅ Perfect distribution
- ✅ Point reads super efficient
- ✅ Job history co-located with employee

**Cons:**
- ❌ All aggregation queries are cross-partition
- ❌ "List all employees" is expensive
- ❌ Department queries cross-partition

---

### Option 3: Synthetic Partition Key (Recommended)

```mermaid
graph TB
    subgraph "Department 10 - Split by employee_id % 10"
        P10_0["Partition: dept_10_0
        Employees: 100, 110, 120"]
        P10_1["Partition: dept_10_1
        Employees: 101, 111, 121"]
        P10_2["Partition: dept_10_2
        Employees: 102, 112, 122"]
    end
    
    subgraph "Department 20 - Split by employee_id % 10"
        P20_0["Partition: dept_20_0
        Employees: 200, 210, 220"]
        P20_1["Partition: dept_20_1
        Employees: 201, 211, 221"]
    end
    
    style P10_0 fill:#e8f5e9
    style P10_1 fill:#c8e6c9
    style P10_2 fill:#a5d6a7
    style P20_0 fill:#fff4e1
    style P20_1 fill:#ffe0b2
```

**Partition Key Formula:** `${department_id}_${employee_id % 10}`

**Pros:**
- ✅ Better distribution within departments
- ✅ Department queries hit multiple partitions (fan-out) but bounded
- ✅ Prevents hot partitions

**Cons:**
- ❌ More complex
- ❌ Requires calculation

---

### Reference Data Container Strategy

```mermaid
graph TB
    subgraph "reference_data Container"
        subgraph "Partition: type=job"
            J1[IT_PROG]
            J2[SA_REP]
            J3[AD_VP]
            J4[... 16 more jobs]
        end
        
        subgraph "Partition: type=department"
            D1[10: Administration]
            D2[20: Marketing]
            D3[50: Shipping]
            D4[... 24 more depts]
        end
        
        subgraph "Partition: type=location"
            L1[1400: Southlake, TX]
            L2[1500: South SF, CA]
            L3[1700: Seattle, WA]
            L4[... 20 more locations]
        end
    end
    
    CACHE["Azure Cache
    for Redis"]
    
    reference_data --> CACHE
    
    style J1 fill:#e1f5ff
    style J2 fill:#e1f5ff
    style J3 fill:#e1f5ff
    style J4 fill:#e1f5ff
    style D1 fill:#fff4e1
    style D2 fill:#fff4e1
    style D3 fill:#fff4e1
    style D4 fill:#fff4e1
    style L1 fill:#e8f5e9
    style L2 fill:#e8f5e9
    style L3 fill:#e8f5e9
    style L4 fill:#e8f5e9
    style CACHE fill:#ff6b6b,color:#fff
```

**Strategy:** Combine reference data container with Azure Cache for Redis for frequent lookups

---

## Migration Dependency Graph

### Migration Flow Diagram

```mermaid
graph TD
    Start([Start Migration])
    
    Start --> Phase1[Phase 1: Independent Tables]
    
    Phase1 --> R["Load REGIONS
    4 rows"]
    Phase1 --> J["Load JOBS
    19 rows"]
    
    R --> Phase2[Phase 2: Simple Dependencies]
    J --> Phase2
    
    Phase2 --> C["Load COUNTRIES
    25 rows
    Depends on: REGIONS"]
    C --> L["Load LOCATIONS
    23 rows
    Depends on: COUNTRIES"]
    
    L --> Phase3[Phase 3: Circular Dependencies]
    J --> Phase3
    
    Phase3 --> D1["Load DEPARTMENTS
    27 rows
    manager_id = NULL
    Depends on: LOCATIONS"]
    
    D1 --> E1["Load EMPLOYEES
    107 rows
    manager_id = NULL
    Depends on: DEPARTMENTS, JOBS"]
    
    E1 --> D2["UPDATE DEPARTMENTS
    Set manager_id
    Now employees exist"]
    
    D2 --> E2["UPDATE EMPLOYEES
    Set manager_id
    Hierarchical order"]
    
    E2 --> Phase4[Phase 4: Final Dependencies]
    
    Phase4 --> H["Load JOB_HISTORY
    10 rows
    Depends on: EMPLOYEES,
    JOBS, DEPARTMENTS"]
    
    H --> Validate{"Validation
    Checks"}
    
    Validate -->|All Pass| Success([Migration Complete])
    Validate -->|Failures| Rollback[Rollback Strategy]
    
    Rollback --> Fix[Fix Issues]
    Fix --> Start
    
    style Start fill:#4caf50,color:#fff
    style Phase1 fill:#2196f3,color:#fff
    style Phase2 fill:#ff9800,color:#fff
    style Phase3 fill:#f44336,color:#fff
    style Phase4 fill:#9c27b0,color:#fff
    style Success fill:#4caf50,color:#fff
    style Validate fill:#ffc107
    style Rollback fill:#f44336,color:#fff
```

### Validation Checks

```mermaid
graph LR
    subgraph "Foreign Key Validation"
        V1["employee.department_id
        exists in departments"]
        V2["employee.job_id
        exists in jobs"]
        V3["employee.manager_id
        exists in employees"]
        V4["department.manager_id
        exists in employees"]
        V5["department.location_id
        exists in locations"]
        V6["location.country_id
        exists in countries"]
        V7["country.region_id
        exists in regions"]
        V8[job_history FKs valid]
    end
    
    subgraph "Business Rule Validation"
        V9["No self-referencing
        managers"]
        V10["No circular
        manager chains"]
        V11[All salaries > 0]
        V12[All emails unique]
    end
    
    style V1 fill:#e8f5e9
    style V2 fill:#e8f5e9
    style V3 fill:#e8f5e9
    style V4 fill:#e8f5e9
    style V5 fill:#e8f5e9
    style V6 fill:#e8f5e9
    style V7 fill:#e8f5e9
    style V8 fill:#e8f5e9
    style V9 fill:#fff4e1
    style V10 fill:#fff4e1
    style V11 fill:#fff4e1
    style V12 fill:#fff4e1
```

### CosmosDB Containers

```mermaid
graph TB
    subgraph "CosmosDB Account"
        subgraph "employees container"
            EP["Partition Key:
            department_id or
            synthetic key"]
            ED["107 employee documents
            with embedded data
            and job_history arrays"]
        end
        
        subgraph "reference_data container"
            RP[Partition Key: type]
            RD["Jobs, Departments,
            Locations, Countries,
            Regions
            ~98 documents"]
        end
        
        subgraph "audit_log container"
            AP[Partition Key: date]
            AD["Migration tracking
            and validation logs"]
        end
    end
    
    style EP fill:#4caf50,color:#fff
    style RP fill:#2196f3,color:#fff
    style AP fill:#ff9800,color:#fff
```

### Rollback Strategy

```mermaid
stateDiagram-v2
    [*] --> Running: Start Migration
    
    Running --> Success: All validations pass
    Running --> Failed: Validation fails
    
    Failed --> Analyze: Log error context
    Analyze --> Decision: Determine strategy
    
    Decision --> RollbackAll
    Decision --> ContinuePartial
    
    RollbackAll --> Retry: Re-run from start
    ContinuePartial --> FixData: Correct issues
    
    FixData --> Retry
    
    Retry --> Running
    
    Success --> [*]
    
    note right of RollbackAll
        Option A:
        Delete all containers
    end note
    
    note right of ContinuePartial
        Option B:
        Continue with fixes
    end note
    
    note right of FixData
        Resume from
        failed step
    end note
```

---

## Summary

This ER documentation provides interactive Mermaid diagrams for:

1. **Complete Schema Diagram** - Full view of all 7 tables and relationships (ERD format)
2. **Geographic Hierarchy** - Visual tree showing regions → countries → locations
3. **Organizational Hierarchy** - Departments, employees, jobs, and circular dependencies
4. **Management Hierarchy Example** - Actual employee reporting structure
5. **Employee Detail Relationships** - The 6-way join visualization
6. **CosmosDB Denormalized Document** - Recommended document structure
7. **Job History Tracking** - Oracle trigger mechanism and CosmosDB alternatives (sequence diagrams)
8. **Partition Key Strategies** - Three options with visual representation
9. **Migration Dependency Graph** - Step-by-step migration flow with validation
10. **Rollback Strategy** - Error handling state diagram

### Diagram Features

✨ **Interactive**: Mermaid diagrams render natively in:
- GitHub
- VS Code (with Mermaid extension)
- Azure DevOps
- Most modern Markdown viewers

🎨 **Color-coded**: Different colors for different entity types:
- 🟢 Green: Core employee data
- 🔵 Blue: Job/reference data
- 🟡 Yellow: Location/geographic data
- 🟣 Purple: Historical/audit data
- 🔴 Red: Critical migration phases

### Key Takeaways

- ⚠️ **Two circular dependencies** must be resolved with two-phase loading
- 🔄 **Self-referencing manager hierarchy** requires hierarchical or two-phase loading
- 📊 **Denormalization recommended** for CosmosDB to avoid 6-way joins
- 🎯 **Partition by department_id** or synthetic key for best performance
- 🔔 **Trigger logic** must be replicated via Change Feed + Azure Functions
- ✅ **4-phase migration** process with validation at each step

### How to View

```bash
# VS Code: Install Mermaid extension
# Extension ID: bierner.markdown-mermaid

# Or view on GitHub:
# Just push this file - Mermaid renders automatically!
```

---

**Document Version:** 2.0 (Updated with Mermaid diagrams)  
**Created:** October 21, 2025  
**Last Updated:** October 21, 2025  
**Status:** ✅ Complete with Interactive Diagrams

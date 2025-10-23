# Getting Started Guide

Complete guide to setting up and running your first migration with the PySpark migration framework for Oracle HR to Azure Cosmos DB.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Oracle Database Setup](#oracle-database-setup)
5. [Azure Cosmos DB Setup](#azure-cosmos-db-setup)
6. [Configuration](#configuration)
7. [Running Your First Migration](#running-your-first-migration)
8. [Verification](#verification)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

**TL;DR** - Get running in 5 minutes:

```bash
# 1. Clone and setup Python environment
git clone <repo-url>
cd pyspark-migration
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Setup Oracle with Docker (automatic!)
./scripts/setup-oracle-docker.sh  # Windows: .\scripts\setup-oracle-docker.ps1

# 3. Setup Azure Cosmos DB (one-time)
# - Create Cosmos DB account in Azure Portal
# - Create database: hr_migration
# - Create containers: reference_data, employees

# 4. Configure environment
cp .env.example .env
# Edit .env with your Cosmos DB credentials

# 5. Run migration!
python orchestration/run_all_migrations.py
```

---

## Prerequisites

### Required Software

| Software | Version | Purpose | Download |
|----------|---------|---------|----------|
| **Python** | 3.9+ | Runtime for framework | [python.org](https://www.python.org/downloads/) |
| **Java** | 8 or 11 | PySpark JDBC driver | [adoptium.net](https://adoptium.net/) |
| **Docker** | Latest | Oracle database (recommended) | [docker.com](https://docs.docker.com/get-docker/) |
| **Git** | Latest | Clone repository | [git-scm.com](https://git-scm.com/) |

### Required Access

- ✅ **Oracle Database**: READ access to HR schema (or Docker for local Oracle)
- ✅ **Azure Subscription**: For creating Cosmos DB account
- ✅ **Cosmos DB**: READ/WRITE access to migration database
- ✅ **Network**: Connectivity between execution environment and both databases

### System Requirements

**Minimum**:
- 4 GB RAM
- 2 CPU cores
- 10 GB disk space

**Recommended**:
- 8+ GB RAM
- 4+ CPU cores
- 20+ GB disk space (includes Oracle Docker image)

---

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd pyspark-migration
```

### 2. Create Virtual Environment

**Windows (PowerShell)**:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/macOS**:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import pyspark; print(f'PySpark {pyspark.__version__} installed')"
```

**Expected output**:
```
PySpark 3.5.0 installed
```

### 4. Verify Java Installation

PySpark requires Java 8 or 11:

```bash
java -version
```

**Expected output** (example):
```
openjdk version "11.0.20" 2023-07-18
OpenJDK Runtime Environment (build 11.0.20+8)
```

**If Java is not installed**:
- **Windows**: Download from [Adoptium](https://adoptium.net/) and install
- **Linux**: `sudo apt install openjdk-11-jdk`
- **macOS**: `brew install openjdk@11`

### 5. Download Oracle JDBC Driver

Required for connecting to Oracle database:

**Option 1: Manual Download** (Recommended for production)
1. Visit [Oracle JDBC Downloads](https://www.oracle.com/database/technologies/appdev/jdbc-downloads.html)
2. Download `ojdbc8.jar` (for Java 8) or `ojdbc11.jar` (for Java 11)
3. Place in `libs/` directory:
   ```bash
   mkdir -p libs
   mv ~/Downloads/ojdbc8.jar libs/
   ```

**Option 2: Maven Central**
```bash
# Download using curl (Linux/macOS)
curl -o libs/ojdbc8.jar https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc8/21.9.0.0/ojdbc8-21.9.0.0.jar

# Download using PowerShell (Windows)
Invoke-WebRequest -Uri "https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc8/21.9.0.0/ojdbc8-21.9.0.0.jar" -OutFile "libs\ojdbc8.jar"
```

**Verify**:
```bash
ls -lh libs/ojdbc8.jar
# Should show ~4-5 MB file
```

---

## Oracle Database Setup

You have two options for Oracle database: **Docker (recommended)** or **Manual installation**.

### Option 1: Docker Oracle (Recommended) ⭐

**Why Docker?**
- ✅ Quick setup (~5-10 minutes including download)
- ✅ No Oracle installation required
- ✅ HR schema pre-configured
- ✅ Isolated environment
- ✅ Easy cleanup

#### Automatic Setup

We provide automated scripts for both Windows and Linux/macOS:

**Windows (PowerShell)**:
```powershell
# Complete automatic setup
.\scripts\setup-oracle-docker.ps1

# This will:
# 1. Check Docker is installed
# 2. Pull Oracle image (~2.5GB, one-time download)
# 3. Start container
# 4. Wait for database ready (~1-2 minutes)
# 5. Verify HR schema (7 tables, 215 records)
```

**Linux/macOS (Bash)**:
```bash
# Make executable
chmod +x scripts/setup-oracle-docker.sh

# Complete automatic setup
./scripts/setup-oracle-docker.sh

# Same steps as Windows version
```

**What you'll see**:
```
🐳 Oracle Docker Setup Script
═══════════════════════════════════════════
✓ Checking Docker installation... OK
✓ Pulling Oracle image... OK (2.5GB downloaded)
✓ Starting container 'oracle-hr'... OK
✓ Waiting for database ready... OK (90 seconds)
✓ Verifying HR schema...
  - REGIONS: 4 rows ✓
  - COUNTRIES: 25 rows ✓
  - LOCATIONS: 23 rows ✓
  - DEPARTMENTS: 27 rows ✓
  - JOBS: 19 rows ✓
  - EMPLOYEES: 107 rows ✓
  - JOB_HISTORY: 10 rows ✓

🎉 Oracle setup complete!

Connection Info:
  Host: localhost
  Port: 1521
  Service: FREEPDB1
  User: hr
  Password: hr
  
JDBC URL: jdbc:oracle:thin:@//localhost:1521/FREEPDB1
```

#### Step-by-Step Setup (Optional)

If you prefer to run steps individually:

**Windows**:
```powershell
# Step 1: Pull image
.\scripts\setup-oracle-docker.ps1 -Step pull

# Step 2: Start container
.\scripts\setup-oracle-docker.ps1 -Step start

# Step 3: Wait for ready
.\scripts\setup-oracle-docker.ps1 -Step wait

# Step 4: Verify schema
.\scripts\setup-oracle-docker.ps1 -Step schema

# Check status anytime
.\scripts\setup-oracle-docker.ps1 -Step status
```

**Linux/macOS**:
```bash
./scripts/setup-oracle-docker.sh pull
./scripts/setup-oracle-docker.sh start
./scripts/setup-oracle-docker.sh wait
./scripts/setup-oracle-docker.sh schema
./scripts/setup-oracle-docker.sh status
```

#### Docker Configuration

**Default Settings**:
```yaml
Image: gvenzl/oracle-free:23-slim
Container Name: oracle-hr
Port Mapping: 1521:1521
SYS Password: OracleTest123
HR User: hr
HR Password: hr
Database: FREEPDB1
```

**Custom Configuration**:
```powershell
# Windows - custom port and passwords
$env:ORACLE_PORT=1522
$env:ORACLE_PASSWORD="MySecretPass123"
.\scripts\setup-oracle-docker.ps1

# Linux/macOS
export ORACLE_PORT=1522
export ORACLE_PASSWORD="MySecretPass123"
./scripts/setup-oracle-docker.sh
```

#### Container Management

**Check Status**:
```bash
docker ps | grep oracle-hr
```

**View Logs**:
```bash
docker logs oracle-hr
```

**Stop Container** (preserves data):
```bash
docker stop oracle-hr
```

**Start Stopped Container**:
```bash
docker start oracle-hr
```

**Connect to Database**:
```bash
# Using sqlplus inside container
docker exec -it oracle-hr sqlplus hr/hr@FREEPDB1

# Using external tool
# Host: localhost, Port: 1521, Service: FREEPDB1, User: hr, Pass: hr
```

**Cleanup** (removes everything):
```powershell
# Windows
.\scripts\setup-oracle-docker.ps1 -Step cleanup

# Linux/macOS
./scripts/setup-oracle-docker.sh cleanup

# Or manually
docker stop oracle-hr
docker rm oracle-hr
docker rmi gvenzl/oracle-free:23-slim
```

#### HR Schema Details

The Oracle container includes a pre-configured HR schema with sample data:

| Table | Description | Rows |
|-------|-------------|------|
| **REGIONS** | Geographic regions | 4 |
| **COUNTRIES** | Countries by region | 25 |
| **LOCATIONS** | Office locations | 23 |
| **DEPARTMENTS** | Company departments | 27 |
| **JOBS** | Job titles and salary ranges | 19 |
| **EMPLOYEES** | Employee records | 107 |
| **JOB_HISTORY** | Employee job change history | 10 |
| **Total** | | **215** |

**Relationships**:
```
REGIONS (1) → (M) COUNTRIES
COUNTRIES (1) → (M) LOCATIONS
LOCATIONS (1) → (M) DEPARTMENTS
DEPARTMENTS (1) → (M) EMPLOYEES
JOBS (1) → (M) EMPLOYEES
EMPLOYEES (1) → (M) JOB_HISTORY
EMPLOYEES → EMPLOYEES (manager self-reference)
```

### Option 2: Manual Oracle Installation

If you can't use Docker or have an existing Oracle instance:

**Requirements**:
- Oracle Database 11g or higher
- HR schema installed (sample schema included with Oracle)
- Network access from your environment

**Setup Steps**:
1. Install Oracle Database
2. Create user `hr` with password
3. Install HR schema using `@?/demo/schema/human_resources/hr_main.sql`
4. Grant permissions: `GRANT CONNECT, RESOURCE TO hr;`
5. Verify tables exist: `SELECT * FROM hr.employees;`

**Connection Info**:
- Note your host, port, service name
- Will be used in `.env` configuration

---

## Azure Cosmos DB Setup

### 1. Create Cosmos DB Account

**Via Azure Portal**:
1. Navigate to [Azure Portal](https://portal.azure.com)
2. Click "Create a resource" → "Azure Cosmos DB"
3. Select **API**: "Core (SQL)"
4. Configure:
   - **Subscription**: Your subscription
   - **Resource Group**: Create new or use existing
   - **Account Name**: `hr-migration-<yourname>` (globally unique)
   - **Location**: Choose region closest to you
   - **Capacity mode**: Provisioned throughput (or Serverless for testing)
5. Click "Review + create" → "Create"
6. Wait for deployment (~5 minutes)

**Via Azure CLI**:
```bash
# Login
az login

# Create resource group
az group create --name rg-hr-migration --location eastus

# Create Cosmos account
az cosmosdb create \
  --name hr-migration-<yourname> \
  --resource-group rg-hr-migration \
  --default-consistency-level Session \
  --locations regionName=eastus

# Get connection details
az cosmosdb keys list \
  --name hr-migration-<yourname> \
  --resource-group rg-hr-migration \
  --type connection-strings
```

### 2. Create Database

**Via Azure Portal**:
1. Open your Cosmos DB account
2. Click "Data Explorer" → "New Database"
3. Database ID: `hr_migration`
4. Throughput: Manual (start with 4000 RU/s for testing)
5. Click "OK"

**Via Azure CLI**:
```bash
az cosmosdb sql database create \
  --account-name hr-migration-<yourname> \
  --resource-group rg-hr-migration \
  --name hr_migration \
  --throughput 4000
```

### 3. Create Containers

You need two containers:

#### Container 1: reference_data

**Via Portal**:
1. Data Explorer → hr_migration → "New Container"
2. Configure:
   - **Container ID**: `reference_data`
   - **Partition key**: `/partitionKey`
   - **Throughput**: 4000 RU/s (manual) or shared with database
3. Click "OK"

**Via CLI**:
```bash
az cosmosdb sql container create \
  --account-name hr-migration-<yourname> \
  --resource-group rg-hr-migration \
  --database-name hr_migration \
  --name reference_data \
  --partition-key-path "/partitionKey" \
  --throughput 4000
```

#### Container 2: employees

**Via Portal**:
1. Data Explorer → hr_migration → "New Container"
2. Configure:
   - **Container ID**: `employees`
   - **Partition key**: `/partitionKey`
   - **Throughput**: 10000 RU/s (for employee denormalization)
3. Click "OK"

**Via CLI**:
```bash
az cosmosdb sql container create \
  --account-name hr-migration-<yourname> \
  --resource-group rg-hr-migration \
  --database-name hr_migration \
  --name employees \
  --partition-key-path "/partitionKey" \
  --throughput 10000
```

### 4. Get Connection Details

**Via Portal**:
1. Cosmos account → "Keys"
2. Copy:
   - **URI**: `https://<account>.documents.azure.com:443/`
   - **PRIMARY KEY**: Long base64 string

**Via CLI**:
```bash
# Get endpoint
az cosmosdb show \
  --name hr-migration-<yourname> \
  --resource-group rg-hr-migration \
  --query documentEndpoint -o tsv

# Get primary key
az cosmosdb keys list \
  --name hr-migration-<yourname> \
  --resource-group rg-hr-migration \
  --query primaryMasterKey -o tsv
```

### Cost Optimization Tips

**For Testing/Development**:
- Use **Serverless** capacity mode (pay per request)
- Or use **Provisioned** with minimum RU/s (400 RU/s per container)
- Scale up only during migration

**For Production**:
- Use **Autoscale** throughput (scales between min/max)
- Start with 1000-4000 RU/s autoscale for reference_data
- Start with 4000-10000 RU/s autoscale for employees
- Scale down after migration completes

---

## Configuration

### 1. Create Environment File

Copy the example file:

```bash
cp .env.example .env
```

### 2. Edit Configuration

Open `.env` in your editor and configure:

#### Oracle Configuration

If using **Docker Oracle** (from our scripts):
```bash
# Oracle Database Connection
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE=FREEPDB1
ORACLE_USER=hr
ORACLE_PASSWORD=hr
```

If using **Manual Oracle** installation:
```bash
# Oracle Database Connection
ORACLE_HOST=your-oracle-host.example.com
ORACLE_PORT=1521
ORACLE_SERVICE=ORCL
ORACLE_USER=hr
ORACLE_PASSWORD=your-hr-password
```

#### Cosmos DB Configuration

Replace with your values from Azure setup:

```bash
# Azure Cosmos DB Connection
COSMOS_ENDPOINT=https://hr-migration-yourname.documents.azure.com:443/
COSMOS_KEY=your-primary-key-goes-here-very-long-base64-string==
COSMOS_DATABASE=hr_migration

# Container names (should match what you created)
COSMOS_CONTAINER_REFERENCE=reference_data
COSMOS_CONTAINER_EMPLOYEES=employees

# Partition keys (must match container configuration)
COSMOS_PARTITION_KEY_PATH=/partitionKey
```

#### Optional Settings

```bash
# Spark Configuration
SPARK_DRIVER_MEMORY=4g
SPARK_EXECUTOR_MEMORY=4g

# Migration Settings
BATCH_SIZE=1000
ENABLE_CHECKPOINTS=true
DRY_RUN=false

# Logging
LOG_LEVEL=INFO
LOG_FILE=migration.log
```

### 3. Validate Configuration

```python
# Test Oracle connection
python -c "
from config.connections import get_oracle_config
config = get_oracle_config()
print(f'Oracle: {config.host}:{config.port}/{config.service} as {config.user}')
"

# Test Cosmos connection
python -c "
from config.connections import get_cosmos_config
config = get_cosmos_config()
print(f'Cosmos: {config.endpoint} → {config.database}')
"
```

---

## Running Your First Migration

### 1. Pre-Flight Checks

Run validation to ensure everything is configured:

```bash
python orchestration/run_all_migrations.py --validate-only
```

**Expected output**:
```
Pre-flight Checks
═════════════════
✓ Oracle connection validated
✓ Cosmos DB connection validated
✓ Container 'reference_data' exists
✓ Container 'employees' exists
✓ JDBC driver found: libs/ojdbc8.jar
✓ All configurations valid

Ready for migration!
```

### 2. Dry Run (Recommended)

Test the migration without actually writing to Cosmos DB:

```bash
python orchestration/run_all_migrations.py --dry-run
```

**This will**:
- ✅ Extract data from Oracle
- ✅ Transform and denormalize
- ✅ Validate data quality
- ❌ NOT load to Cosmos DB (simulated)

**Expected output**:
```
DRY RUN MODE - No data will be loaded
════════════════════════════════════

Phase 1-2: Reference Data Migration
───────────────────────────────────
✓ Extracted 4 regions
✓ Extracted 25 countries
✓ Extracted 23 locations
✓ Extracted 19 jobs
✓ Extracted 27 departments
✓ Transformed 98 reference documents
✓ Validated 98 documents (100% passed)
⊗ Would load 98 documents (DRY RUN)

Phase 3-4: Employee Migration
──────────────────────────────
✓ Extracted 107 employees
✓ Denormalized with 6-way join
✓ Embedded manager details
✓ Aggregated job history
✓ Validated 107 documents (100% passed)
⊗ Would load 107 employee documents (DRY RUN)
⊗ Would update 27 department references (DRY RUN)

Summary
───────
Total Records: 232
Would migrate: 232 documents
Duration: 2m 15s

✓ Dry run successful!
```

### 3. Execute Migration

When you're ready, run the real migration:

```bash
python orchestration/run_all_migrations.py
```

**Expected output**:
```
Oracle HR → Azure Cosmos DB Migration
══════════════════════════════════════

Phase 1-2: Reference Data Migration
───────────────────────────────────
[10:00:00] Extracting reference tables...
[10:00:02] ✓ Regions: 4 records
[10:00:03] ✓ Countries: 25 records
[10:00:04] ✓ Locations: 23 records
[10:00:05] ✓ Jobs: 19 records
[10:00:06] ✓ Departments: 27 records

[10:00:07] Transforming to Cosmos documents...
[10:00:09] ✓ 98 documents prepared

[10:00:10] Validating data quality...
[10:00:12] ✓ Field validation: 100% passed
[10:00:13] ✓ Referential integrity: OK
[10:00:14] ✓ Business rules: OK

[10:00:15] Loading to Cosmos DB (reference_data)...
[10:00:45] ✓ Loaded 98 documents (30 seconds)

✓ Phase 1-2 complete!

Phase 3-4: Employee Migration
──────────────────────────────
[10:00:46] Extracting employee data...
[10:01:00] ✓ Employees: 107 records
[10:01:15] ✓ Departments: 27 records
[10:01:20] ✓ Jobs: 19 records
[10:01:25] ✓ Locations: 23 records
[10:01:30] ✓ Countries: 25 records
[10:01:35] ✓ Regions: 4 records
[10:01:40] ✓ Job History: 10 records

[10:01:45] Performing 6-way denormalization...
[10:02:00] ✓ 107 employee documents created

[10:02:01] Validating data quality...
[10:02:15] ✓ Field validation: 100% passed
[10:02:20] ✓ Referential integrity: OK
[10:02:25] ✓ Business rules: OK

[10:02:26] Loading to Cosmos DB (employees)...
[10:03:00] ✓ Loaded 107 employee documents (34 seconds)

[10:03:01] Resolving circular manager references...
[10:03:15] ✓ Updated 27 departments with manager links

✓ Phase 3-4 complete!

Final Summary
═════════════
Total Records Migrated: 232
  - Reference Data: 98 documents
  - Employees: 107 documents
  - Department Updates: 27 updates

Duration: 3m 30s
Throughput: 1.1 records/second

RU Consumption:
  - Reference Data: ~5,000 RUs
  - Employees: ~25,000 RUs
  - Updates: ~2,700 RUs
  - Total: ~32,700 RUs

✅ Migration completed successfully!
```

### 4. Monitor Progress

The migration creates a log file:

```bash
# Tail the log in another terminal
tail -f migration.log
```

---

## Verification

### 1. Check Record Counts

**Oracle** (source):
```sql
-- Connect to Oracle
sqlplus hr/hr@localhost:1521/FREEPDB1

-- Count records
SELECT 'REGIONS' AS table_name, COUNT(*) FROM regions
UNION ALL SELECT 'COUNTRIES', COUNT(*) FROM countries
UNION ALL SELECT 'LOCATIONS', COUNT(*) FROM locations
UNION ALL SELECT 'DEPARTMENTS', COUNT(*) FROM departments
UNION ALL SELECT 'JOBS', COUNT(*) FROM jobs
UNION ALL SELECT 'EMPLOYEES', COUNT(*) FROM employees
UNION ALL SELECT 'JOB_HISTORY', COUNT(*) FROM job_history;

-- Expected: 215 total records
```

**Cosmos DB** (target):
```python
# Run verification script
python scripts/verify_migration.py

# Or manually via Azure Portal:
# 1. Open Cosmos account → Data Explorer
# 2. hr_migration → reference_data → Items
#    Should see 98 documents
# 3. hr_migration → employees → Items
#    Should see 107 documents
```

### 2. Spot Check Data Quality

**Check a sample employee**:
```python
from azure.cosmos import CosmosClient
from config.connections import get_cosmos_config

config = get_cosmos_config()
client = CosmosClient(config.endpoint, config.key)
database = client.get_database_client("hr_migration")
container = database.get_container_client("employees")

# Get employee 100 (Steven King - CEO)
item = container.read_item(item="emp_100", partition_key="dept_90_0")

print(f"Name: {item['first_name']} {item['last_name']}")
print(f"Email: {item['email']}")
print(f"Department: {item['department']['department_name']}")
print(f"Job: {item['job']['job_title']}")
print(f"Location: {item['location']['city']}, {item['location']['country']['country_name']}")
```

**Expected output**:
```
Name: Steven King
Email: SKING
Department: Executive
Job: President
Location: Seattle, United States of America
```

### 3. Validate Denormalization

Check that nested structures exist:

```python
# Verify nested department
assert 'department' in item
assert 'department_id' in item['department']
assert 'department_name' in item['department']

# Verify nested job
assert 'job' in item
assert 'job_title' in item['job']

# Verify nested location with country and region
assert 'location' in item
assert 'country' in item['location']
assert 'region' in item['location']['country']

print("✓ Denormalization validated!")
```

### 4. Check Migration Metrics

```bash
# View metrics from last migration
cat checkpoints/full_migration_checkpoint.json
```

**Example**:
```json
{
  "started_at": "2025-10-23T10:00:00Z",
  "completed_at": "2025-10-23T10:03:30Z",
  "total_duration_seconds": 210,
  "phase_1_2_completed": true,
  "phase_3_4_completed": true,
  "records_migrated": {
    "reference_data": 98,
    "employees": 107,
    "department_updates": 27
  },
  "ru_consumption": {
    "reference_data": 4900,
    "employees": 24850,
    "updates": 2700,
    "total": 32450
  },
  "success_rate": 100.0
}
```

---

## Troubleshooting

### Common Issues

#### Issue: Python not found
**Error**: `python: command not found`

**Solution**:
- Windows: Install from [python.org](https://www.python.org/downloads/), ensure "Add to PATH" is checked
- Linux: `sudo apt install python3 python3-pip python3-venv`
- macOS: `brew install python@3.9`

---

#### Issue: Java not found
**Error**: `JAVA_HOME is not set`

**Solution**:
```bash
# Check Java installation
java -version

# If not installed:
# Windows: Download from Adoptium.net
# Linux: sudo apt install openjdk-11-jdk
# macOS: brew install openjdk@11

# Set JAVA_HOME
# Windows: setx JAVA_HOME "C:\Program Files\Java\jdk-11"
# Linux/macOS: export JAVA_HOME=/usr/lib/jvm/java-11-openjdk
```

---

#### Issue: Docker not running
**Error**: `Cannot connect to the Docker daemon`

**Solution**:
- Windows/macOS: Start Docker Desktop
- Linux: `sudo systemctl start docker`
- Verify: `docker ps`

---

#### Issue: Oracle container won't start
**Error**: `Container oracle-hr exited with status 1`

**Solution**:
```bash
# Check logs
docker logs oracle-hr

# Common causes:
# 1. Port 1521 already in use
docker ps -a | grep 1521  # Check what's using port
docker stop <conflicting-container>

# 2. Insufficient resources
# Ensure Docker has at least 2GB RAM allocated

# 3. Corrupted container
docker rm oracle-hr
./scripts/setup-oracle-docker.sh  # Start fresh
```

---

#### Issue: Oracle connection refused
**Error**: `Connection refused: localhost:1521`

**Solution**:
```bash
# Check container is running
docker ps | grep oracle-hr

# Check health status
docker inspect oracle-hr --format='{{.State.Health.Status}}'
# Should show: healthy

# Wait for healthy status
./scripts/setup-oracle-docker.sh wait

# If still failing, restart container
docker restart oracle-hr
```

---

#### Issue: JDBC driver not found
**Error**: `java.lang.ClassNotFoundException: oracle.jdbc.driver.OracleDriver`

**Solution**:
```bash
# Download JDBC driver
mkdir -p libs
cd libs

# Option 1: Maven Central
curl -o ojdbc8.jar https://repo1.maven.org/maven2/com/oracle/database/jdbc/ojdbc8/21.9.0.0/ojdbc8-21.9.0.0.jar

# Option 2: Manual download from Oracle.com
# Place ojdbc8.jar in libs/ directory

# Verify
ls -lh libs/ojdbc8.jar
```

---

#### Issue: Cosmos DB authentication failed
**Error**: `Unauthorized: The input authorization token can't serve the request`

**Solution**:
- Verify `COSMOS_KEY` in `.env` is the **Primary Key** (not connection string)
- Ensure no extra spaces or quotes around the key
- Copy the key again from Azure Portal → Cosmos account → Keys
- Check key hasn't been regenerated

---

#### Issue: Cosmos DB container not found
**Error**: `Resource Not Found: The specified container does not exist`

**Solution**:
```bash
# Verify containers exist in Azure Portal
# Or create via CLI:

az cosmosdb sql container create \
  --account-name hr-migration-yourname \
  --resource-group rg-hr-migration \
  --database-name hr_migration \
  --name reference_data \
  --partition-key-path "/partitionKey" \
  --throughput 4000

az cosmosdb sql container create \
  --account-name hr-migration-yourname \
  --resource-group rg-hr-migration \
  --database-name hr_migration \
  --name employees \
  --partition-key-path "/partitionKey" \
  --throughput 10000
```

---

#### Issue: Throttling (429 errors)
**Error**: `Request rate is large: ActivityId=...`

**Solution**:
- **Option 1**: Reduce batch size in `.env`: `BATCH_SIZE=500`
- **Option 2**: Increase container RU/s in Azure Portal
- **Option 3**: Enable autoscale for containers
- **Option 4**: Wait and retry (framework does this automatically)

---

#### Issue: Out of memory
**Error**: `OutOfMemoryError: Java heap space`

**Solution**:
```bash
# Increase Spark memory in .env
SPARK_DRIVER_MEMORY=8g
SPARK_EXECUTOR_MEMORY=8g

# Or run with explicit config
python orchestration/run_all_migrations.py \
  --spark-driver-memory 8g \
  --spark-executor-memory 8g
```

---

### Getting Help

**Check Logs**:
```bash
# View full migration log
cat migration.log

# View last 50 lines
tail -50 migration.log

# Search for errors
grep -i error migration.log
```

**Enable Debug Logging**:
```bash
# In .env file
LOG_LEVEL=DEBUG

# Run migration
python orchestration/run_all_migrations.py
```

**Validate Configuration**:
```bash
# Run pre-flight checks
python orchestration/run_all_migrations.py --validate-only
```

---

## Next Steps

Now that your environment is set up and you've run your first migration:

1. **Review the data** in Azure Cosmos DB Data Explorer
2. **Check the Operations Guide** (`docs/OPERATIONS_GUIDE.md`) for:
   - Extending the framework with custom transformers
   - Production deployment best practices
   - Monitoring and observability
   - Performance tuning
3. **Customize the migration** for your specific needs:
   - Modify transformation logic in `transformers/`
   - Add custom validation rules in `validators/`
   - Adjust partition key strategy in `config/transformation_config.py`

---

**Congratulations! You've successfully set up and run your first Oracle to Cosmos DB migration! 🎉**

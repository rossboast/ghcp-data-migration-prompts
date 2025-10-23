# Setup Guide

Complete guide to setting up the PySpark migration framework for Oracle HR to Azure Cosmos DB migration.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Oracle JDBC Driver](#oracle-jdbc-driver)
4. [Azure Cosmos DB Configuration](#azure-cosmos-db-configuration)
5. [Configuration Files](#configuration-files)
6. [Verification](#verification)

## Prerequisites

### Required Software

- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **Java 8 or 11** - Required for PySpark JDBC (Oracle connector)
- **Git** - For cloning the repository
- **Oracle Database** - Source database (11g or higher)
- **Azure Subscription** - For Cosmos DB

### Required Access

- Oracle database credentials with READ access to HR schema
- Azure Cosmos DB account with READ/WRITE access
- Network connectivity between execution environment and both databases

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd pyspark-migration
```

### 2. Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -c "from pyspark.sql import SparkSession; print('PySpark OK')"
python -c "import structlog; print('Logging OK')"
```

## Oracle JDBC Driver

PySpark requires Oracle JDBC driver to connect to Oracle databases.

### Download Driver

1. Go to [Oracle JDBC Downloads](https://www.oracle.com/database/technologies/appdev/jdbc-downloads.html)
2. Download **ojdbc8.jar** (for Oracle 12c+) or **ojdbc11.jar** (for Oracle 21c+)
3. Accept the license agreement

### Install Driver

**Option 1: Project Directory (Recommended)**
```bash
# Create jars directory
mkdir -p jars

# Copy driver
cp /path/to/ojdbc8.jar jars/
```

**Option 2: System-wide Installation**
```bash
# Linux/Mac
sudo cp ojdbc8.jar /usr/share/java/

# Windows
# Copy to C:\Program Files\Java\jdk-11\jre\lib\ext\
```

### Configure Spark to Use Driver

Update `.env` file:
```bash
SPARK_JDBC_DRIVER_PATH=./jars/ojdbc8.jar
```

Or set in your Spark configuration:
```python
spark = SparkSession.builder \
    .config("spark.jars", "./jars/ojdbc8.jar") \
    .getOrCreate()
```

## Azure Cosmos DB Configuration

### 1. Create Cosmos DB Account

**Using Azure Portal:**
1. Navigate to [Azure Portal](https://portal.azure.com)
2. Create new resource → Databases → Azure Cosmos DB
3. Select **Azure Cosmos DB for NoSQL**
4. Configure:
   - Resource group: `migration-rg`
   - Account name: `hr-migration-cosmos`
   - Location: Your preferred region
   - Capacity mode: **Provisioned throughput** (for predictable costs)

**Using Azure CLI:**
```bash
# Login to Azure
az login

# Create resource group
az group create --name migration-rg --location eastus

# Create Cosmos DB account
az cosmosdb create \
  --name hr-migration-cosmos \
  --resource-group migration-rg \
  --locations regionName=eastus failoverPriority=0 \
  --default-consistency-level Session
```

### 2. Create Database

```bash
az cosmosdb sql database create \
  --account-name hr-migration-cosmos \
  --resource-group migration-rg \
  --name hr_migration
```

### 3. Create Containers

**Reference Data Container:**
```bash
az cosmosdb sql container create \
  --account-name hr-migration-cosmos \
  --resource-group migration-rg \
  --database-name hr_migration \
  --name reference_data \
  --partition-key-path "/partitionKey" \
  --throughput 400
```

**Employees Container:**
```bash
az cosmosdb sql container create \
  --account-name hr-migration-cosmos \
  --resource-group migration-rg \
  --database-name hr_migration \
  --name employees \
  --partition-key-path "/partitionKey" \
  --throughput 1000
```

### 4. Get Connection Details

**Using Azure Portal:**
1. Navigate to your Cosmos DB account
2. Settings → Keys
3. Copy:
   - URI (endpoint)
   - PRIMARY KEY

**Using Azure CLI:**
```bash
# Get endpoint
az cosmosdb show \
  --name hr-migration-cosmos \
  --resource-group migration-rg \
  --query documentEndpoint -o tsv

# Get primary key
az cosmosdb keys list \
  --name hr-migration-cosmos \
  --resource-group migration-rg \
  --query primaryMasterKey -o tsv
```

## Configuration Files

### 1. Create .env File

Copy the example environment file:
```bash
cp .env.example .env
```

### 2. Configure Oracle Connection

Edit `.env` and set Oracle connection details:

```bash
# Oracle Database Configuration
ORACLE_HOST=your-oracle-host.database.com
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=ORCLPDB1
ORACLE_USER=hr
ORACLE_PASSWORD=your-password

# Alternative: Use connection string
# ORACLE_CONNECTION_STRING=jdbc:oracle:thin:@//host:port/service
```

### 3. Configure Cosmos DB Connection

Add Cosmos DB configuration to `.env`:

```bash
# Azure Cosmos DB Configuration
COSMOS_ENDPOINT=https://hr-migration-cosmos.documents.azure.com:443/
COSMOS_KEY=your-primary-key-here
COSMOS_DATABASE=hr_migration

# Container names
COSMOS_REFERENCE_CONTAINER=reference_data
COSMOS_EMPLOYEE_CONTAINER=employees
```

### 4. Configure Spark Settings

Adjust Spark configuration based on your environment:

```bash
# Spark Configuration
SPARK_MASTER=local[*]
SPARK_DRIVER_MEMORY=4g
SPARK_EXECUTOR_MEMORY=4g
SPARK_EXECUTOR_CORES=2

# JDBC Driver
SPARK_JDBC_DRIVER_PATH=./jars/ojdbc8.jar
```

### Example .env File

```bash
# Oracle Configuration
ORACLE_HOST=oracledb.example.com
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=ORCLPDB1
ORACLE_USER=hr
ORACLE_PASSWORD=MySecurePassword123!

# Cosmos DB Configuration
COSMOS_ENDPOINT=https://hr-migration-cosmos.documents.azure.com:443/
COSMOS_KEY=AbCdEfGh1234567890...
COSMOS_DATABASE=hr_migration
COSMOS_REFERENCE_CONTAINER=reference_data
COSMOS_EMPLOYEE_CONTAINER=employees

# Spark Configuration
SPARK_MASTER=local[4]
SPARK_DRIVER_MEMORY=4g
SPARK_EXECUTOR_MEMORY=4g
SPARK_JDBC_DRIVER_PATH=./jars/ojdbc8.jar

# Migration Settings
LOG_LEVEL=INFO
BATCH_SIZE=1000
```

## Verification

### 1. Test Oracle Connection

```bash
python -c "
from config.connections import OracleConnectionConfig
from extractors.oracle_extractor import OracleExtractor

config = OracleConnectionConfig()
extractor = OracleExtractor(config)
extractor.validate_source_connection()
print('✓ Oracle connection successful')
"
```

### 2. Test Cosmos DB Connection

```bash
python -c "
from config.connections import CosmosDBConnectionConfig
from loaders.cosmos_loader import CosmosLoader

config = CosmosDBConnectionConfig()
loader = CosmosLoader(config, 'reference_data')
loader.validate_target_connection()
print('✓ Cosmos DB connection successful')
"
```

### 3. Test End-to-End

```bash
# Run pre-flight checks
python orchestration/run_all_migrations.py --pre-flight-only
```

Expected output:
```
================================================================================
PRE-FLIGHT VALIDATION CHECKS
================================================================================
1. Testing Oracle connection...
   ✓ Oracle connection OK
2. Testing Cosmos DB connection...
   ✓ Cosmos DB connection OK
3. Checking Cosmos containers...
   ✓ Containers exist: reference_data, employees
4. Checking source data availability...
   ✓ Source data available: 107 employees
================================================================================
PRE-FLIGHT CHECK SUMMARY
================================================================================
Passed: 4
Failed: 0
================================================================================

✅ Pre-flight checks PASSED
```

## Troubleshooting

### Issue: Oracle JDBC Connection Failed

**Error:** `java.sql.SQLException: No suitable driver found`

**Solution:**
1. Verify JDBC driver path in `.env`
2. Check driver file exists: `ls jars/ojdbc8.jar`
3. Ensure Java is installed: `java -version`

### Issue: Cosmos DB Authentication Failed

**Error:** `Unauthorized: The input authorization token can't serve the request`

**Solution:**
1. Verify `COSMOS_KEY` is the PRIMARY KEY (not secondary)
2. Check for extra spaces or newlines in the key
3. Ensure key hasn't been regenerated in Azure Portal

### Issue: PySpark Memory Error

**Error:** `java.lang.OutOfMemoryError: Java heap space`

**Solution:**
Increase Spark memory in `.env`:
```bash
SPARK_DRIVER_MEMORY=8g
SPARK_EXECUTOR_MEMORY=8g
```

### Issue: Permission Denied on Oracle

**Error:** `ORA-01031: insufficient privileges`

**Solution:**
Grant required permissions:
```sql
GRANT SELECT ON hr.employees TO your_user;
GRANT SELECT ON hr.departments TO your_user;
-- Repeat for all tables
```

## Next Steps

1. Review the [Developer Guide](developer-guide.md) to understand the architecture
2. Run a dry-run migration: `python orchestration/run_all_migrations.py --dry-run`
3. Execute the migration: `python orchestration/run_all_migrations.py`
4. Monitor using the [Deployment Guide](deployment-guide.md)

## Security Best Practices

1. **Never commit `.env` file** - Add to `.gitignore`
2. **Use Azure Key Vault** - Store secrets in Key Vault for production
3. **Rotate credentials** - Regularly rotate Cosmos DB keys
4. **Limit network access** - Use Azure Private Link for Cosmos DB
5. **Use managed identities** - Avoid storing credentials when running in Azure

## Additional Resources

- [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/)
- [Azure Cosmos DB Documentation](https://docs.microsoft.com/en-us/azure/cosmos-db/)
- [Oracle JDBC Driver Documentation](https://docs.oracle.com/en/database/oracle/oracle-database/21/jjdbc/)

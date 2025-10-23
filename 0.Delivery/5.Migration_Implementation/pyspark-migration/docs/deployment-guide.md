# Deployment Guide

Production deployment guide for the PySpark migration framework.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Environment Setup](#environment-setup)
3. [Monitoring and Observability](#monitoring-and-observability)
4. [Performance Tuning](#performance-tuning)
5. [Scaling Strategies](#scaling-strategies)
6. [Backup and Rollback](#backup-and-rollback)
7. [Security Hardening](#security-hardening)
8. [Operational Procedures](#operational-procedures)

## Pre-Deployment Checklist

### ✅ Code Quality

- [ ] All unit tests pass: `pytest tests/ -v`
- [ ] Integration tests complete successfully
- [ ] Code reviewed and approved
- [ ] No hardcoded credentials
- [ ] Error handling verified

### ✅ Configuration

- [ ] Production `.env` file configured
- [ ] Oracle credentials validated
- [ ] Cosmos DB connection tested
- [ ] JDBC driver installed
- [ ] Spark configuration tuned for environment

### ✅ Infrastructure

- [ ] Cosmos DB containers created with appropriate RUs
- [ ] Cosmos DB indexes configured
- [ ] Network connectivity verified
- [ ] Firewall rules configured
- [ ] Sufficient compute resources allocated

### ✅ Data Validation

- [ ] Source data quality assessed
- [ ] Sample migration tested
- [ ] Validation rules reviewed
- [ ] Data reconciliation plan defined
- [ ] Rollback procedure documented

### ✅ Monitoring

- [ ] Logging configured
- [ ] Metrics collection enabled
- [ ] Alerting rules defined
- [ ] Dashboards created
- [ ] On-call rotation established

## Environment Setup

### Production Environment

**Recommended Specifications:**

```yaml
Compute:
  - CPU: 8 cores minimum (16+ recommended)
  - Memory: 32GB minimum (64GB+ recommended)
  - Storage: 100GB for logs and checkpoints

Spark Configuration:
  spark.driver.memory: 16g
  spark.executor.memory: 16g
  spark.executor.cores: 4
  spark.sql.shuffle.partitions: 200
  spark.default.parallelism: 100
```

### Azure VM Deployment

**Using Standard_D16s_v3 (16 vCPU, 64 GB RAM):**

```bash
# Create resource group
az group create --name migration-prod-rg --location eastus

# Create VM
az vm create \
  --resource-group migration-prod-rg \
  --name migration-vm-prod \
  --image UbuntuLTS \
  --size Standard_D16s_v3 \
  --admin-username azureuser \
  --generate-ssh-keys

# Install dependencies
ssh azureuser@<vm-ip>
sudo apt update
sudo apt install -y python3.9 python3-pip openjdk-11-jdk

# Clone and setup
git clone <repository-url>
cd pyspark-migration
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Azure Databricks Deployment

**Recommended Cluster Configuration:**

```python
{
  "cluster_name": "migration-production",
  "spark_version": "11.3.x-scala2.12",
  "node_type_id": "Standard_DS4_v2",
  "driver_node_type_id": "Standard_DS4_v2",
  "num_workers": 4,
  "autoscale": {
    "min_workers": 2,
    "max_workers": 8
  },
  "spark_conf": {
    "spark.sql.shuffle.partitions": "200",
    "spark.default.parallelism": "100"
  },
  "azure_attributes": {
    "availability": "ON_DEMAND_AZURE"
  }
}
```

**Install libraries:**
```bash
# On Databricks cluster
%pip install python-dotenv structlog azure-cosmos
```

### Docker Deployment

**Dockerfile:**

```dockerfile
FROM apache/spark-py:v3.5.0

# Install dependencies
USER root
RUN pip install --no-cache-dir \
    python-dotenv \
    structlog \
    azure-cosmos

# Copy application
COPY . /app
WORKDIR /app

# Copy JDBC driver
COPY jars/ojdbc8.jar /opt/spark/jars/

# Set environment
ENV PYSPARK_PYTHON=python3
ENV SPARK_HOME=/opt/spark

# Run migration
CMD ["python", "orchestration/run_all_migrations.py"]
```

**Build and run:**
```bash
docker build -t migration-framework:latest .

docker run -d \
  --name migration-prod \
  --env-file .env.prod \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/checkpoints:/app/checkpoints \
  migration-framework:latest
```

## Monitoring and Observability

### Structured Logging

All components use structured logging (JSON format):

```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "level": "INFO",
  "logger": "employee_migration",
  "message": "Phase 3 completed",
  "context": {
    "phase": "phase_3",
    "duration_seconds": 245.6,
    "records_migrated": 107,
    "validation_passed": true
  }
}
```

### Metrics Collection

Framework tracks these metrics automatically:

```python
{
  "component": "cosmos_loader",
  "metrics": {
    "records_loaded": 107,
    "batches_processed": 1,
    "ru_consumed": 1070,
    "duration_seconds": 12.3,
    "errors": 0,
    "retries": 2
  }
}
```

### Azure Monitor Integration

**Send logs to Azure Log Analytics:**

```python
from azure.monitor.opentelemetry import configure_azure_monitor

configure_azure_monitor(
    connection_string="InstrumentationKey=<your-key>"
)

# Logs automatically sent to Azure Monitor
```

**Query logs in Log Analytics:**

```kusto
traces
| where cloud_RoleName == "migration-framework"
| where timestamp > ago(1h)
| where severityLevel >= 3  // Error and above
| project timestamp, message, customDimensions
| order by timestamp desc
```

### Application Insights

**Track custom metrics:**

```python
from applicationinsights import TelemetryClient

tc = TelemetryClient('<instrumentation-key>')

tc.track_metric('records_migrated', 107)
tc.track_metric('migration_duration_seconds', 245.6)
tc.track_event('migration_completed', {
    'phase': 'phase_3',
    'success': True
})
```

### Alerting Rules

**Azure Monitor Alerts:**

```yaml
Alert 1: Migration Failure
  Condition: traces | where message contains "failed" and severityLevel >= 3
  Threshold: 1 occurrence
  Action: Send email + SMS to on-call

Alert 2: High Error Rate
  Condition: customMetrics | where name == "errors" | summarize sum(value)
  Threshold: > 10 errors in 5 minutes
  Action: Create incident

Alert 3: Slow Performance
  Condition: customMetrics | where name == "duration_seconds" > 600
  Threshold: 1 occurrence
  Action: Send notification

Alert 4: Cosmos DB Throttling
  Condition: CosmosDBRequests | where StatusCode == 429
  Threshold: > 50 requests in 1 minute
  Action: Auto-scale RUs + notify
```

### Dashboards

**Sample Grafana Dashboard:**

```json
{
  "dashboard": {
    "title": "Migration Monitoring",
    "panels": [
      {
        "title": "Records Migrated",
        "type": "graph",
        "targets": [
          {
            "query": "sum(rate(records_migrated[5m]))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          {
            "query": "sum(rate(errors[5m]))"
          }
        ]
      },
      {
        "title": "Cosmos RU Consumption",
        "type": "graph",
        "targets": [
          {
            "query": "avg(cosmos_ru_consumed)"
          }
        ]
      },
      {
        "title": "Processing Duration",
        "type": "heatmap",
        "targets": [
          {
            "query": "histogram_quantile(0.95, duration_seconds)"
          }
        ]
      }
    ]
  }
}
```

## Performance Tuning

### Spark Configuration

**Memory Tuning:**

```bash
# For large datasets (>1M records)
export SPARK_DRIVER_MEMORY=32g
export SPARK_EXECUTOR_MEMORY=32g
export SPARK_EXECUTOR_CORES=8

# For medium datasets (100K-1M records)
export SPARK_DRIVER_MEMORY=16g
export SPARK_EXECUTOR_MEMORY=16g
export SPARK_EXECUTOR_CORES=4

# For small datasets (<100K records)
export SPARK_DRIVER_MEMORY=8g
export SPARK_EXECUTOR_MEMORY=8g
export SPARK_EXECUTOR_CORES=2
```

**Parallelism:**

```python
# Set based on number of cores
spark.conf.set("spark.default.parallelism", num_cores * 2)
spark.conf.set("spark.sql.shuffle.partitions", num_cores * 4)

# Example for 16 cores
spark.conf.set("spark.default.parallelism", 32)
spark.conf.set("spark.sql.shuffle.partitions", 64)
```

**Partitioning Strategy:**

```python
# Repartition large DataFrames before joins
employees_df = employees_df.repartition(50, "employee_id")
departments_df = departments_df.repartition(10, "department_id")

# Use broadcast for small reference tables
from pyspark.sql.functions import broadcast
result = large_df.join(broadcast(small_df), "key")
```

### Cosmos DB Optimization

**Provisioned Throughput:**

```bash
# Calculate required RUs
Records to migrate: 100,000
RU per document: ~10
Total RUs needed: 1,000,000
Target duration: 10 minutes (600 seconds)
Required RU/s: 1,000,000 / 600 = 1,667 RU/s

# Provision with buffer
az cosmosdb sql container throughput update \
  --account-name hr-migration-cosmos \
  --database-name hr_migration \
  --name employees \
  --throughput 2000
```

**Bulk Operations:**

Framework uses bulk mode by default:
```python
cosmos_config = {
    "spark.cosmos.write.bulk.enabled": "true",
    "spark.cosmos.write.point.maxConcurrency": "10",
    "spark.cosmos.write.bulk.maxPendingOperations": "1000"
}
```

**Indexing Policy:**

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    {
      "path": "/employee_id/?",
      "indexes": [{"kind": "Range", "dataType": "Number"}]
    },
    {
      "path": "/department_id/?",
      "indexes": [{"kind": "Range", "dataType": "Number"}]
    },
    {
      "path": "/email/?",
      "indexes": [{"kind": "Range", "dataType": "String"}]
    }
  ],
  "excludedPaths": [
    {
      "path": "/job_history/*"
    }
  ]
}
```

### Batch Size Tuning

**Adjust based on document size:**

```python
# Small documents (<1KB) - Use larger batches
loader = CosmosLoader(config, container, batch_size=2000)

# Medium documents (1-5KB) - Use medium batches
loader = CosmosLoader(config, container, batch_size=1000)

# Large documents (>5KB) - Use smaller batches
loader = CosmosLoader(config, container, batch_size=500)
```

## Scaling Strategies

### Horizontal Scaling

**Spark Cluster:**

```python
# Azure Databricks autoscaling
cluster_config = {
    "autoscale": {
        "min_workers": 2,
        "max_workers": 20
    },
    "autotermination_minutes": 30
}
```

**Partitioned Processing:**

```python
# Process by date ranges in parallel
date_ranges = [
    ("2020-01-01", "2020-12-31"),
    ("2021-01-01", "2021-12-31"),
    ("2022-01-01", "2022-12-31")
]

for start_date, end_date in date_ranges:
    query = f"""
        SELECT * FROM employees
        WHERE hire_date BETWEEN '{start_date}' AND '{end_date}'
    """
    df = extractor.extract(query=query)
    # Process...
```

### Cosmos DB Scaling

**Auto-scale:**

```bash
# Enable autoscale (scales between 10% and 100% of max)
az cosmosdb sql container throughput migrate \
  --account-name hr-migration-cosmos \
  --database-name hr_migration \
  --name employees \
  --throughput-type autoscale \
  --max-throughput 10000
```

**Manual scaling during migration:**

```python
# Scale up before migration
cosmos_client.replace_throughput(10000)

# Run migration
migration.run_all()

# Scale down after migration
cosmos_client.replace_throughput(400)
```

## Backup and Rollback

### Pre-Migration Backup

**Cosmos DB:**

```bash
# Enable point-in-time restore
az cosmosdb update \
  --name hr-migration-cosmos \
  --resource-group migration-rg \
  --enable-analytical-storage true \
  --backup-policy-type Continuous

# Export before migration
az cosmosdb sql container export \
  --account-name hr-migration-cosmos \
  --database-name hr_migration \
  --name employees \
  --output-path ./backups/employees_$(date +%Y%m%d).json
```

**Oracle:**

```sql
-- Export to data pump
expdp hr/password \
  directory=BACKUP_DIR \
  dumpfile=hr_backup_$(date +%Y%m%d).dmp \
  logfile=hr_backup.log \
  schemas=hr
```

### Checkpoint Management

Framework automatically creates checkpoints:

```json
{
  "started_at": "2024-01-15T10:00:00Z",
  "completed_phases": ["phase_1", "phase_2"],
  "phase_details": {
    "phase_1": {
      "completed_at": "2024-01-15T10:15:00Z",
      "records_migrated": 98
    }
  },
  "last_updated": "2024-01-15T10:15:00Z"
}
```

**Resume after failure:**

```bash
# Migration resumes from checkpoint automatically
python orchestration/run_all_migrations.py

# Force restart from beginning
python orchestration/run_all_migrations.py --force
```

### Rollback Procedures

**Cosmos DB Point-in-Time Restore:**

```bash
# Restore to timestamp before migration
az cosmosdb sql database restore \
  --account-name hr-migration-cosmos \
  --resource-group migration-rg \
  --name hr_migration \
  --restore-timestamp "2024-01-15T10:00:00Z"
```

**Delete and Re-create:**

```bash
# Delete all documents
python -c "
from loaders.cosmos_loader import CosmosLoader
from config.connections import CosmosDBConnectionConfig

loader = CosmosLoader(CosmosDBConnectionConfig(), 'employees')
loader.delete_all_records(confirm=True)
"

# Re-run migration
python orchestration/run_all_migrations.py --force
```

## Security Hardening

### Credential Management

**Azure Key Vault:**

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(
    vault_url="https://migration-keyvault.vault.azure.net/",
    credential=credential
)

# Retrieve secrets
oracle_password = client.get_secret("oracle-password").value
cosmos_key = client.get_secret("cosmos-primary-key").value
```

**Environment Variables:**

```bash
# Never commit .env file
echo ".env" >> .gitignore

# Use environment-specific files
.env.dev
.env.staging
.env.production
```

### Network Security

**Azure Private Link:**

```bash
# Create private endpoint for Cosmos DB
az network private-endpoint create \
  --name cosmos-private-endpoint \
  --resource-group migration-rg \
  --vnet-name migration-vnet \
  --subnet default \
  --private-connection-resource-id <cosmos-resource-id> \
  --group-id Sql \
  --connection-name cosmos-connection
```

**Firewall Rules:**

```bash
# Allow specific IPs only
az cosmosdb update \
  --name hr-migration-cosmos \
  --resource-group migration-rg \
  --ip-range-filter "1.2.3.4,5.6.7.8"
```

### Encryption

**Cosmos DB:**
- Data encrypted at rest by default
- Use customer-managed keys for additional control

**In-Transit:**
- All connections use TLS 1.2+
- Oracle JDBC uses SSL: `jdbc:oracle:thin:@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCPS)...))`

## Operational Procedures

### Pre-Migration Checklist

```bash
# 1. Verify connections
python orchestration/run_all_migrations.py --pre-flight-only

# 2. Run validation on sample
python orchestration/run_all_migrations.py --dry-run

# 3. Check resource availability
az cosmosdb show --name hr-migration-cosmos --query "{RUs: properties.capacity}"

# 4. Review checkpoint status
cat full_migration_checkpoint.json

# 5. Notify stakeholders
# Send "Migration Starting" email
```

### During Migration

```bash
# Monitor logs
tail -f logs/migration_$(date +%Y%m%d).log | jq .

# Check progress
watch -n 30 'cat full_migration_checkpoint.json | jq .completed_phases'

# Monitor Cosmos RU usage
az monitor metrics list \
  --resource <cosmos-resource-id> \
  --metric "TotalRequestUnits" \
  --interval PT1M

# Check for errors
grep "ERROR" logs/*.log
```

### Post-Migration

```bash
# 1. Validate migration
python orchestration/run_all_migrations.py --validate-only

# 2. Generate report
python orchestration/run_all_migrations.py --report

# 3. Run data quality checks
python scripts/data_quality_check.py

# 4. Compare record counts
python scripts/reconciliation.py

# 5. Archive logs and checkpoints
tar -czf migration_$(date +%Y%m%d).tar.gz logs/ checkpoints/
az storage blob upload \
  --account-name migrationlogs \
  --container-name archives \
  --file migration_$(date +%Y%m%d).tar.gz
```

### Troubleshooting Common Issues

**Issue 1: High Cosmos DB Throttling (429 errors)**

```bash
# Check current RU consumption
az cosmosdb sql container throughput show \
  --account-name hr-migration-cosmos \
  --database-name hr_migration \
  --name employees

# Scale up temporarily
az cosmosdb sql container throughput update \
  --account-name hr-migration-cosmos \
  --database-name hr_migration \
  --name employees \
  --throughput 5000

# Restart migration (will resume from checkpoint)
python orchestration/run_all_migrations.py
```

**Issue 2: Spark Out of Memory**

```bash
# Increase memory
export SPARK_DRIVER_MEMORY=32g
export SPARK_EXECUTOR_MEMORY=32g

# Reduce batch size
# Edit .env
BATCH_SIZE=500

# Restart
python orchestration/run_all_migrations.py
```

**Issue 3: Oracle Connection Timeout**

```bash
# Check connectivity
telnet oracle-host 1521

# Test connection
python -c "
from extractors.oracle_extractor import OracleExtractor
from config.connections import OracleConnectionConfig
extractor = OracleExtractor(OracleConnectionConfig())
extractor.validate_source_connection()
"
```

## Maintenance

### Regular Tasks

**Weekly:**
- Review error logs
- Check Cosmos DB RU utilization
- Verify backup integrity

**Monthly:**
- Rotate credentials
- Update dependencies: `pip list --outdated`
- Review and archive old logs

**Quarterly:**
- Performance review
- Cost optimization
- Security audit

## Additional Resources

- [Azure Cosmos DB Best Practices](https://docs.microsoft.com/en-us/azure/cosmos-db/sql/best-practice-dotnet)
- [PySpark Performance Tuning](https://spark.apache.org/docs/latest/sql-performance-tuning.html)
- [Azure Monitor Documentation](https://docs.microsoft.com/en-us/azure/azure-monitor/)

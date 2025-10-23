# Cosmos DB Loader - Complete Documentation

## Overview

The **CosmosLoader** is a concrete implementation of the `BaseLoader` abstract class, designed to load data into Azure Cosmos DB containers using the PySpark Cosmos connector. It provides production-grade features including batch processing, automatic retry with exponential backoff for throttling, RU consumption tracking, and comprehensive error handling.

## Key Features

### 1. **Batch Processing**
- Configurable batch sizes (default: 1,000 records)
- Automatic batching handled by base class
- Progress tracking per batch
- Metrics collection for each batch

### 2. **Retry Logic**
- Automatic retry on throttling (429 errors)
- Exponential backoff with configurable parameters
- Default: 5 attempts, 2-second initial delay, 2x backoff
- Inherited from `@retry` decorator

### 3. **RU Tracking**
- Estimates RU consumption per batch
- Tracks total RUs in metrics
- Helpful for cost optimization

### 4. **Upsert Support**
- Insert or update existing documents
- Uses Cosmos DB's ItemOverwrite strategy
- Based on document `id` field

### 5. **Connection Validation**
- Pre-flight connection checks
- Container existence validation
- Schema introspection

### 6. **Write Modes**
- **append**: Add new documents (ItemAppend)
- **overwrite**: Replace existing documents (ItemOverwrite)

## Architecture

```
CosmosLoader
    ↓ extends
BaseLoader (template method pattern)
    ↓ provides
- load_with_metrics()
- load_batches()
- Automatic metrics tracking
- Error handling and collection
```

## Installation Requirements

```txt
# From requirements.txt
azure-cosmos-spark==4.22.0
pyspark==3.5.0
python-dotenv==1.0.0
structlog==24.1.0
```

## Configuration

### Environment Variables (.env)

```bash
# Cosmos DB Configuration
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-primary-key-here
COSMOS_DATABASE=hr_migration
COSMOS_CONTAINER=employees
COSMOS_PARTITION_KEY=/partitionKey
COSMOS_THROUGHPUT=4000
```

### Connection Config

```python
from config import get_cosmos_config

config = get_cosmos_config()
# Returns CosmosDBConnectionConfig instance with:
# - endpoint
# - key
# - database
# - containers
# - partition_key_paths
# - throughput
```

## Usage Examples

### Example 1: Basic Loading

```python
from loaders import CosmosLoader
from config import get_cosmos_config
from pyspark.sql import SparkSession

# Initialize
config = get_cosmos_config()
loader = CosmosLoader(
    config,
    container="employees",
    batch_size=1000
)

# Load data
spark = SparkSession.builder.getOrCreate()
df = spark.read.json("employees.json")

loaded_count = loader.load_with_metrics(df)
print(f"Loaded {loaded_count} records")
```

### Example 2: With Connection Validation

```python
# Validate connection first
if loader.validate_target_connection():
    print("✅ Connection validated")
    
    # Load data
    result = loader.load(df, validate_connection=False)
    print(f"Loaded {result} records")
else:
    print("❌ Connection failed")
```

### Example 3: Upsert (Insert or Update)

```python
# Upsert records (updates existing, inserts new)
upserted = loader.upsert_records(df)
print(f"Upserted {upserted} records")

# Note: Cosmos DB uses 'id' field as the unique key
# Documents with matching 'id' will be replaced
```

### Example 4: Large Dataset with Batching

```python
# Load large dataset with smaller batches
loader = CosmosLoader(
    config,
    container="employees",
    batch_size=500  # Smaller batches for large docs
)

# Load 100,000 records in batches of 500
result = loader.load_with_metrics(large_df)

# Metrics will show batch-by-batch progress
print(loader.metrics.generate_report())
```

### Example 5: Error Handling

```python
from utils.error_handler import LoadError

try:
    loaded = loader.load(df)
    print(f"Success: {loaded} records")
    
except LoadError as e:
    print(f"Load failed: {e.message}")
    print(f"Context: {e.context}")
    
    # Check collected errors
    if loader.error_collector.has_errors():
        for error in loader.error_collector.get_errors():
            print(f"  - {error['message']}")
```

### Example 6: Container Statistics

```python
# Get container statistics
stats = loader.get_container_statistics()

print(f"Container: {stats['container']}")
print(f"Records: {stats['record_count']}")
print(f"Columns: {stats['columns']}")
```

### Example 7: Complete Pipeline

```python
from extractors import OracleExtractor
from transformers import DataTypeConverter, CommonTransformations
from loaders import CosmosLoader
from config import get_oracle_config, get_cosmos_config

# Extract
oracle_config = get_oracle_config()
extractor = OracleExtractor(oracle_config)
employees_df = extractor.extract_employees()

# Transform
employees_df = DataTypeConverter.convert_oracle_to_json_types(employees_df)
employees_df = CommonTransformations.add_document_id(
    employees_df,
    id_column="employee_id",
    prefix="emp_"
)
employees_df = CommonTransformations.add_partition_key(
    employees_df,
    key_formula="dept_{department_id}_{employee_id % 10}"
)
employees_df = CommonTransformations.add_metadata(
    employees_df,
    source="oracle_hr",
    entity_type="employee"
)

# Load
cosmos_config = get_cosmos_config()
loader = CosmosLoader(cosmos_config, container="employees")
loaded = loader.load_with_metrics(employees_df)

print(f"✅ Pipeline complete: {loaded} employees migrated")
```

## API Reference

### Constructor

```python
CosmosLoader(
    config: CosmosDBConnectionConfig,
    container: str,
    batch_size: int = 1000,
    write_mode: str = "append",
    logger: Optional[Any] = None,
    metrics: Optional[MetricsCollector] = None
)
```

**Parameters:**
- `config`: Cosmos DB connection configuration
- `container`: Target container name (must exist)
- `batch_size`: Records per batch (default: 1000)
- `write_mode`: "append" or "overwrite" (default: "append")
- `logger`: Optional logger instance
- `metrics`: Optional metrics collector

### Methods

#### validate_target_connection()

```python
def validate_target_connection(self) -> bool
```

Validates Cosmos DB connection and container existence.

**Returns:** `True` if connection is valid

**Raises:** `LoadError` if validation fails

---

#### prepare_data()

```python
def prepare_data(self, df: DataFrame) -> DataFrame
```

Prepares DataFrame for Cosmos DB loading. Validates required columns and ensures proper data types.

**Required Columns:**
- `id` (string): Document ID

**Parameters:**
- `df`: Input DataFrame

**Returns:** Prepared DataFrame

**Raises:** `LoadError` if required columns are missing

---

#### load_batch()

```python
def load_batch(
    self, 
    batch_df: DataFrame, 
    batch_number: int = 0
) -> int
```

Loads a single batch to Cosmos DB with retry logic.

**Parameters:**
- `batch_df`: DataFrame batch to load
- `batch_number`: Batch number for logging

**Returns:** Number of records loaded

**Raises:** `LoadError` if load fails after retries

**Note:** Automatically retries on throttling (429 errors) with exponential backoff.

---

#### load()

```python
def load(
    self,
    df: DataFrame,
    validate_connection: bool = True,
    **kwargs
) -> int
```

Loads DataFrame to Cosmos DB using batch processing.

**Parameters:**
- `df`: DataFrame to load
- `validate_connection`: Whether to validate connection first
- `**kwargs`: Additional arguments

**Returns:** Number of records loaded

**Raises:** `LoadError` if load fails

---

#### load_with_metrics()

```python
def load_with_metrics(self, df: DataFrame) -> int
```

Inherited from `BaseLoader`. Loads data with automatic metrics tracking.

**Parameters:**
- `df`: DataFrame to load

**Returns:** Number of records loaded

**Features:**
- Automatic timing
- Success/failure counting
- Metrics report generation

---

#### upsert_records()

```python
def upsert_records(
    self,
    df: DataFrame,
    key_columns: Optional[List[str]] = None
) -> int
```

Upserts records (insert or update based on `id` field).

**Parameters:**
- `df`: DataFrame to upsert
- `key_columns`: Not used (Cosmos uses `id` as key)

**Returns:** Number of records upserted

**Note:** Uses ItemOverwrite strategy internally.

---

#### get_container_statistics()

```python
def get_container_statistics(self) -> Dict[str, Any]
```

Retrieves statistics about the target container.

**Returns:** Dictionary with:
- `container`: Container name
- `database`: Database name
- `record_count`: Number of documents
- `columns`: Number of columns (if records exist)

---

#### delete_all_records()

```python
def delete_all_records(self, confirm: bool = False) -> bool
```

Deletes all records from container.

**⚠️ WARNING: This is destructive!**

**Parameters:**
- `confirm`: Must be `True` to execute

**Returns:** `True` if successful

---

#### target_exists()

```python
def target_exists(self) -> bool
```

Checks if target container exists.

**Returns:** `True` if container exists

## Data Requirements

### Required Columns

Your DataFrame must have:

1. **id** (string): Unique document identifier
   - Must be unique within partition
   - Will be cast to string if not already

### Recommended Columns

2. **partitionKey** (string): Partition key value
   - Should match your container's partition key path
   - Use `CommonTransformations.add_partition_key()` to generate

3. **metadata** (struct): Migration metadata
   - Use `CommonTransformations.add_metadata()` to add

### Example Document Structure

```json
{
    "id": "emp_100",
    "partitionKey": "dept_10_0",
    "employee_id": 100,
    "first_name": "Steven",
    "last_name": "King",
    "email": "SKING",
    "hire_date": "2003-06-17",
    "salary": 24000,
    "department": {
        "department_id": 10,
        "department_name": "Administration"
    },
    "metadata": {
        "source": "oracle_hr",
        "entityType": "employee",
        "migratedAt": "2024-01-15T10:30:00Z",
        "version": "1.0"
    }
}
```

## Configuration Details

### Cosmos Write Configuration

The loader sets these Spark configuration options:

```python
{
    "spark.cosmos.accountEndpoint": endpoint,
    "spark.cosmos.accountKey": key,
    "spark.cosmos.database": database,
    "spark.cosmos.container": container,
    "spark.cosmos.write.strategy": "ItemAppend" or "ItemOverwrite",
    "spark.cosmos.write.bulk.enabled": "true",
    "spark.cosmos.write.point.maxConcurrency": "10",
    "spark.cosmos.write.bulk.maxPendingOperations": "1000"
}
```

### Bulk Write Settings

- **bulk.enabled**: Enables bulk operations for better throughput
- **point.maxConcurrency**: Max concurrent point operations (10)
- **bulk.maxPendingOperations**: Max pending bulk operations (1000)

### Write Strategies

- **ItemAppend**: Insert only (fails on duplicate `id`)
- **ItemOverwrite**: Upsert (insert or replace)

## Performance Considerations

### Batch Size Tuning

**Small Documents (<1KB):**
```python
loader = CosmosLoader(config, container="...", batch_size=2000)
```

**Medium Documents (1-10KB):**
```python
loader = CosmosLoader(config, container="...", batch_size=1000)  # Default
```

**Large Documents (>10KB):**
```python
loader = CosmosLoader(config, container="...", batch_size=500)
```

### RU Consumption

Approximate RU costs:
- **1KB document**: ~5-10 RUs
- **10KB document**: ~50-100 RUs
- **Indexing overhead**: +20-50%

**Formula:**
```
Estimated RUs = (Document Size in KB) × 5-10 × Number of Documents
```

### Throttling Management

The loader automatically handles throttling:
1. Detects 429 (Rate Exceeded) errors
2. Applies exponential backoff (2s → 4s → 8s → 16s → 32s)
3. Retries up to 5 times
4. Logs throttling events for monitoring

**To reduce throttling:**
- Reduce batch size
- Increase container throughput (RU/s)
- Use burst capacity
- Spread writes over time

## Error Handling

### Exception Hierarchy

```
LoadError
    ↓
Exception raised by load operations
```

### Error Context

All errors include context:

```python
try:
    loader.load(df)
except LoadError as e:
    print(e.message)     # Human-readable message
    print(e.context)     # Dict with details
    print(e.timestamp)   # When error occurred
```

### Error Collection

The loader collects all errors:

```python
# After load attempt
if loader.error_collector.has_errors():
    errors = loader.error_collector.get_errors()
    for error in errors:
        print(f"Error: {error['message']}")
        print(f"Context: {error['context']}")
```

## Metrics and Monitoring

### Metrics Tracked

```python
loader.metrics.get_metrics()
# Returns:
{
    "records_processed": 10000,
    "records_failed": 50,
    "batches_processed": 10,
    "request_units_consumed": 100000,
    "load_duration_seconds": 45.2,
    "records_per_second": 221.2
}
```

### Metrics Report

```python
print(loader.metrics.generate_report())

# Output:
"""
Metrics Report - cosmos_loader
===============================
Records Processed: 10,000
Records Failed: 50
Batches Processed: 10
Request Units Consumed: 100,000
Load Duration: 45.20s
Records/Second: 221.24
Success Rate: 99.50%
"""
```

## Testing

### Unit Tests

```python
# tests/test_loaders.py
import pytest
from loaders import CosmosLoader
from config import CosmosDBConnectionConfig

def test_loader_initialization():
    config = CosmosDBConnectionConfig(
        endpoint="https://test.documents.azure.com:443/",
        key="test-key",
        database="test_db"
    )
    loader = CosmosLoader(config, container="test")
    assert loader.container == "test"
    assert loader.batch_size == 1000

def test_prepare_data():
    # Test data preparation
    loader = CosmosLoader(config, container="test")
    
    # Create test DataFrame
    data = [("id1", "key1", "value1")]
    df = spark.createDataFrame(data, ["id", "partitionKey", "data"])
    
    prepared = loader.prepare_data(df)
    
    # Verify id is string
    assert prepared.schema["id"].dataType == StringType()

def test_missing_id_column():
    loader = CosmosLoader(config, container="test")
    
    # DataFrame without 'id' column
    data = [("key1", "value1")]
    df = spark.createDataFrame(data, ["partitionKey", "data"])
    
    with pytest.raises(LoadError):
        loader.prepare_data(df)
```

### Integration Tests

```python
# tests/integration/test_cosmos_loading.py
def test_end_to_end_loading():
    # Setup
    config = get_cosmos_config()
    loader = CosmosLoader(config, container="test_integration")
    
    # Create test data
    data = [
        ("doc_1", "partition_a", "Test 1"),
        ("doc_2", "partition_b", "Test 2")
    ]
    df = spark.createDataFrame(
        data, 
        ["id", "partitionKey", "data"]
    )
    
    # Load
    loaded = loader.load_with_metrics(df)
    assert loaded == 2
    
    # Verify
    stats = loader.get_container_statistics()
    assert stats["record_count"] >= 2
    
    # Cleanup
    loader.delete_all_records(confirm=True)
```

## Troubleshooting

### Issue: Connection Fails

**Symptoms:**
```
LoadError: Failed to connect to Cosmos DB container
```

**Solutions:**
1. Check endpoint format: `https://...documents.azure.com:443/`
2. Verify key (primary or secondary)
3. Ensure database and container exist
4. Check firewall rules (allow your IP)
5. Verify network connectivity

---

### Issue: Throttling (429 Errors)

**Symptoms:**
```
Throttling detected, will retry with backoff
```

**Solutions:**
1. Reduce batch size: `batch_size=500`
2. Increase container RU/s
3. Use autoscale throughput
4. Spread writes over time
5. Check partition key distribution

---

### Issue: Missing Required Columns

**Symptoms:**
```
LoadError: Missing required columns for Cosmos DB: ['id']
```

**Solutions:**
1. Add `id` column:
   ```python
   df = CommonTransformations.add_document_id(
       df, 
       id_column="employee_id",
       prefix="emp_"
   )
   ```

2. Ensure `id` is string type

---

### Issue: Slow Performance

**Symptoms:**
- Low records/second
- High execution time

**Solutions:**
1. Increase batch size (if not throttling)
2. Use bulk operations (already enabled)
3. Check partition key distribution
4. Increase container throughput
5. Monitor RU consumption
6. Optimize document size

---

### Issue: Duplicate Documents

**Symptoms:**
- ItemAppend strategy fails with duplicate `id`

**Solutions:**
1. Use upsert mode:
   ```python
   loader = CosmosLoader(config, container="...", write_mode="overwrite")
   ```

2. Or use upsert method:
   ```python
   loader.upsert_records(df)
   ```

3. Ensure unique `id` values per partition

## Best Practices

### 1. Connection Validation

Always validate before large loads:

```python
if loader.validate_target_connection():
    loader.load(df, validate_connection=False)
```

### 2. Batch Size Selection

Choose based on document size:
- Small docs: 2000+
- Medium docs: 1000 (default)
- Large docs: 500-

### 3. Error Handling

Always wrap in try-except:

```python
try:
    loaded = loader.load_with_metrics(df)
except LoadError as e:
    logger.error("Load failed", error=str(e))
    # Handle or re-raise
```

### 4. Metrics Monitoring

Always review metrics:

```python
loaded = loader.load_with_metrics(df)
print(loader.metrics.generate_report())
```

### 5. Partition Key Strategy

Use meaningful partition keys:

```python
df = CommonTransformations.add_partition_key(
    df,
    key_formula="dept_{department_id}_{employee_id % 10}"
)
```

This creates ~270 partitions (27 depts × 10 buckets).

### 6. Document Preparation

Prepare documents before loading:

```python
# 1. Add ID
df = CommonTransformations.add_document_id(df, "employee_id", "emp_")

# 2. Add partition key
df = CommonTransformations.add_partition_key(
    df, "dept_{department_id}_{employee_id % 10}"
)

# 3. Add metadata
df = CommonTransformations.add_metadata(
    df, source="oracle_hr", entity_type="employee"
)

# 4. Load
loader.load_with_metrics(df)
```

## Code Statistics

- **File**: `loaders/cosmos_loader.py`
- **Lines**: ~550
- **Classes**: 1 (`CosmosLoader`)
- **Methods**: 10
  - `__init__()` - Initialize loader
  - `validate_target_connection()` - Connection validation
  - `prepare_data()` - Data preparation
  - `load_batch()` - Batch loading with retry
  - `load()` - Main load method
  - `upsert_records()` - Upsert mode
  - `get_container_statistics()` - Container stats
  - `delete_all_records()` - Delete all (dangerous!)
  - `target_exists()` - Container existence check
  - `__main__` block - Runnable example

## Next Steps

Now that the **Load** layer is complete, you can:

1. **Test the ETL Chain**: Extract → Transform → Load
2. **Build Reference Data Migration** (Task 14)
3. **Build Validators** (Tasks 10-12) in parallel
4. **Build Employee Transformer** (Task 9)
5. **Build Employee Migration** (Task 15)

### Recommended Next Task

**Task 14: Reference Data Migration Script**

Build `orchestration/migrate_reference_data.py` to implement the first end-to-end migration:
- Extract reference tables (regions, countries, locations, jobs)
- Transform using DataTypeConverter + CommonTransformations
- Load to Cosmos DB using CosmosLoader
- Add checkpoint/restart for fault tolerance

This will validate the entire ETL pipeline with simple transformations before tackling complex employee denormalization.

## Benefits of This Loader

✅ **Production-Ready**: Comprehensive error handling and retry logic  
✅ **Observable**: Detailed metrics and logging  
✅ **Scalable**: Batch processing for large datasets  
✅ **Cost-Aware**: RU consumption tracking  
✅ **Fault-Tolerant**: Automatic retry on throttling  
✅ **Flexible**: Supports append and upsert modes  
✅ **Testable**: Clean separation of concerns  
✅ **Documented**: Extensive inline documentation and examples  

---

**Ready to build end-to-end pipelines! 🚀**

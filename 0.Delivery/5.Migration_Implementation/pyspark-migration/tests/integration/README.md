# Integration Tests

This directory contains integration tests that require real database instances (Oracle and Cosmos DB). These tests validate the complete data pipeline with actual database connections.

## Prerequisites

### Oracle Database
- **Recommended**: Docker Oracle 23ai Free edition
- **Required**: HR schema installed
- **Connection**: Host, port, service name, credentials

### Cosmos DB
- **Options**: Azure Cosmos DB account or local emulator
- **Required**: Database and container created
- **Connection**: Endpoint, key, database name, container name

### Python Environment
```bash
pip install pytest pytest-mock pyspark azure-cosmos python-dotenv
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Enable integration tests
RUN_INTEGRATION_TESTS=true

# Oracle Configuration
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=FREEPDB1
ORACLE_USERNAME=hr
ORACLE_PASSWORD=your_password

# Cosmos DB Configuration
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your_key_here
COSMOS_DATABASE=migration_db
COSMOS_CONTAINER=hr_data
```

### Connection Configuration

The integration tests use the `get_oracle_config()` and `get_cosmos_config()` functions from `config/connections.py`. Ensure these are configured to read from environment variables.

## Running Tests

### Run All Integration Tests
```bash
pytest tests/integration/ -v
```

### Run Oracle Integration Tests Only
```bash
pytest tests/integration/test_oracle_integration.py -v -m oracle
```

### Run Cosmos DB Integration Tests Only
```bash
pytest tests/integration/test_cosmos_integration.py -v -m cosmos
```

### Skip Slow Tests
```bash
pytest tests/integration/ -v -m "not slow"
```

### Run with Coverage
```bash
pytest tests/integration/ -v --cov=extractors --cov=loaders --cov-report=html
```

## Test Organization

### conftest.py
- **Purpose**: Shared fixtures and configuration for integration tests
- **Fixtures**:
  - `skip_if_disabled`: Skip tests if `RUN_INTEGRATION_TESTS=false`
  - `spark_session`: Shared Spark session for all tests
  - `oracle_config`: Oracle connection configuration
  - `cosmos_config`: Cosmos DB connection configuration
  - `oracle_extractor`: Configured Oracle extractor instance
  - `cosmos_loader`: Configured Cosmos DB loader instance
  - `cleanup_cosmos_container`: Cleanup fixture for test data
- **Constants**: Expected counts and values from HR schema

### test_oracle_integration.py
Tests for OracleExtractor with real Oracle database:

#### Test Classes
1. **TestOracleConnectionIntegration** - Connection validation
2. **TestOracleExtractionIntegration** - Data extraction operations
3. **TestOracleBatchOperationsIntegration** - Batch extraction
4. **TestOracleUtilitiesIntegration** - Utility functions
5. **TestOracleDataQualityIntegration** - Data quality validation
6. **TestOracleMetricsIntegration** - Metrics collection
7. **TestOraclePerformanceIntegration** - Performance testing

#### Test Coverage
- ✅ Connection validation and properties
- ✅ Extract all regions, employees, departments
- ✅ Extract with WHERE clauses and filters
- ✅ Extract with column selection
- ✅ Batch extraction of multiple tables
- ✅ Row count utilities
- ✅ Data quality checks (nulls, foreign keys)
- ✅ Metrics collection and timing
- ✅ Performance benchmarks

### test_cosmos_integration.py
Tests for CosmosLoader with real Cosmos DB:

#### Test Classes
1. **TestCosmosConnectionIntegration** - Connection validation
2. **TestCosmosLoadOperationsIntegration** - Load operations
3. **TestCosmosBatchOperationsIntegration** - Batch loading
4. **TestCosmosValidationIntegration** - Validation rules
5. **TestCosmosRetryIntegration** - Retry and throttling
6. **TestCosmosMetricsIntegration** - Metrics collection
7. **TestCosmosDataIntegrityIntegration** - End-to-end validation
8. **TestCosmosPerformanceIntegration** - Performance testing

#### Test Coverage
- ✅ Connection validation and container existence
- ✅ Load in append mode
- ✅ Load in upsert mode (insert and update)
- ✅ Batch loading with repartitioning
- ✅ Validation of required columns (id, partitionKey)
- ✅ Retry logic for throttling (429 errors)
- ✅ Metrics collection and failure tracking
- ✅ End-to-end Oracle → Cosmos pipeline
- ✅ Performance benchmarks

## Test Markers

Tests are marked with pytest markers for selective execution:

- `@pytest.mark.integration` - All integration tests
- `@pytest.mark.oracle` - Tests requiring Oracle database
- `@pytest.mark.cosmos` - Tests requiring Cosmos DB
- `@pytest.mark.slow` - Long-running tests (> 5 seconds)

### Examples
```bash
# Run only fast integration tests
pytest tests/integration/ -v -m "integration and not slow"

# Run only Oracle tests
pytest tests/integration/ -v -m oracle

# Run only Cosmos tests
pytest tests/integration/ -v -m cosmos

# Run everything except slow tests
pytest tests/integration/ -v -m "not slow"
```

## Expected Test Data

The integration tests assume the **Oracle HR schema** is installed with standard data:

| Table | Expected Rows |
|-------|--------------|
| regions | 4 |
| countries | 25 |
| locations | 23 |
| departments | 27 |
| jobs | 19 |
| employees | 107 |
| job_history | 10 |

If your data differs, update the `EXPECTED_COUNTS` dictionary in `conftest.py`.

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      oracle:
        image: gvenzl/oracle-free:23-slim
        env:
          ORACLE_PASSWORD: TestPassword123
          APP_USER: hr
          APP_USER_PASSWORD: hr
        ports:
          - 1521:1521
        options: >-
          --health-cmd healthcheck.sh
          --health-interval 10s
          --health-timeout 5s
          --health-retries 10
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Wait for Oracle
        run: |
          for i in {1..30}; do
            if docker exec $(docker ps -q -f ancestor=gvenzl/oracle-free:23-slim) healthcheck.sh; then
              echo "Oracle is ready"
              break
            fi
            echo "Waiting for Oracle..."
            sleep 10
          done
      
      - name: Install HR schema
        run: |
          # Script to install HR schema
          docker exec $(docker ps -q -f ancestor=gvenzl/oracle-free:23-slim) \
            sqlplus hr/hr@//localhost:1521/FREEPDB1 @/opt/oracle/scripts/hr_main.sql
      
      - name: Run integration tests
        env:
          RUN_INTEGRATION_TESTS: true
          ORACLE_HOST: localhost
          ORACLE_PORT: 1521
          ORACLE_SERVICE_NAME: FREEPDB1
          ORACLE_USERNAME: hr
          ORACLE_PASSWORD: hr
          COSMOS_ENDPOINT: ${{ secrets.COSMOS_ENDPOINT }}
          COSMOS_KEY: ${{ secrets.COSMOS_KEY }}
          COSMOS_DATABASE: test_db
          COSMOS_CONTAINER: test_container
        run: |
          pytest tests/integration/ -v --cov --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests Are Skipped

**Problem**: All integration tests are skipped with message "Integration tests disabled"

**Solution**: Set environment variable:
```bash
export RUN_INTEGRATION_TESTS=true
```

### Oracle Connection Failed

**Problem**: `ORA-12541: TNS:no listener` or similar errors

**Solutions**:
1. Verify Oracle is running: `docker ps`
2. Check connection details in `.env`
3. Test connection with SQL*Plus:
   ```bash
   sqlplus hr/password@//localhost:1521/FREEPDB1
   ```

### Cosmos DB Connection Failed

**Problem**: `CosmosHttpResponseError: Unauthorized` or connection timeout

**Solutions**:
1. Verify endpoint and key in `.env`
2. Check Azure portal: Cosmos DB account → Keys
3. Verify database and container exist
4. Check firewall rules if using Azure Cosmos DB

### Missing HR Schema

**Problem**: Tests fail with "table or view does not exist"

**Solution**: Install Oracle HR sample schema:
```bash
# See docs/oracle-docker-setup.md for complete instructions
sqlplus hr/password@//localhost:1521/FREEPDB1 @?/demo/schema/human_resources/hr_main.sql
```

### Spark Session Errors

**Problem**: `java.lang.ClassNotFoundException: oracle.jdbc.driver.OracleDriver`

**Solution**: Ensure Oracle JDBC driver is in Spark classpath:
```python
spark = SparkSession.builder \
    .config("spark.jars", "path/to/ojdbc11.jar") \
    .getOrCreate()
```

### Performance Tests Timeout

**Problem**: Slow tests timeout or fail performance thresholds

**Solutions**:
1. Skip slow tests: `pytest -v -m "not slow"`
2. Adjust timeout thresholds in test code
3. Increase Cosmos DB RU provisioning for performance tests
4. Check network latency to Azure

## Performance Benchmarks

Expected performance on standard hardware (adjust for your environment):

### Oracle Extraction
- **Small tables** (< 100 rows): < 1 second
- **Medium tables** (100-10,000 rows): 1-5 seconds
- **Large tables** (> 10,000 rows): 5-30 seconds

### Cosmos DB Loading
- **Throughput**: 50-500 records/second (depends on RU provisioning)
- **Batch loading** (1,000 records): 2-20 seconds
- **Large batch** (10,000 records): 20-200 seconds

**Note**: Performance varies significantly based on:
- Hardware (CPU, RAM, disk I/O)
- Network latency to databases
- Cosmos DB provisioned RU/s
- Record size and complexity

## Best Practices

1. **Run integration tests separately** from unit tests
2. **Use fresh test data** for each test run
3. **Clean up after tests** to avoid container bloat
4. **Skip slow tests** during development
5. **Run full suite** before merging to main branch
6. **Monitor performance trends** over time
7. **Use test markers** to run specific test categories
8. **Document deviations** from expected data

## Contributing

When adding new integration tests:

1. Add appropriate markers (`@pytest.mark.integration`, `@pytest.mark.oracle`, etc.)
2. Use fixtures from `conftest.py` for consistency
3. Include cleanup logic to remove test data
4. Add performance expectations if testing performance
5. Document any special setup requirements
6. Update this README with new test coverage

## Related Documentation

- **Unit Tests**: `tests/README.md` - Mocked tests without databases
- **Oracle Setup**: `docs/oracle-docker-setup.md` - Docker Oracle installation
- **Cosmos Setup**: `docs/cosmos-setup.md` - Cosmos DB configuration
- **CI/CD**: `.github/workflows/tests.yml` - Automated test pipeline

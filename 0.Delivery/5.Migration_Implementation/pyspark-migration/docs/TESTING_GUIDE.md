# Testing Guide

Complete testing guide for the PySpark migration framework, covering unit tests, integration tests, and Docker Oracle setup.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Test Organization](#test-organization)
4. [Unit Tests](#unit-tests)
5. [Integration Tests](#integration-tests)
6. [Docker Oracle Integration](#docker-oracle-integration)
7. [Running Tests](#running-tests)
8. [CI/CD Integration](#cicd-integration)
9. [Test Coverage](#test-coverage)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The test suite includes:

| Type | Count | Runtime | Dependencies |
|------|-------|---------|-------------|
| **Unit Tests** (mocked) | 61 tests | < 5 sec | pytest, pytest-mock, PySpark |
| **Integration Tests** | 45 tests | 2-10 min | Oracle DB, Cosmos DB |
| **Total** | **106 tests** | **2-10 min** | Full stack |

**Key Features:**
- ✅ Fast mocked unit tests (< 1 second)
- ✅ Comprehensive integration tests with real databases
- ✅ **Automatic Docker Oracle setup** (zero manual configuration!)
- ✅ Smart test skipping when databases unavailable
- ✅ CI/CD ready with markers and parallel execution
- ✅ 80%+ code coverage

---

## Quick Start

### Unit Tests (No Setup Required)

```bash
# Install dependencies
pip install pytest pytest-mock pyspark

# Run all unit tests (fast)
pytest tests/ -v --ignore=tests/integration

# Run mocked tests only (< 1 second)
pytest tests/test_extractors.py tests/test_loaders.py -v
```

### Integration Tests with Docker Oracle (Automatic!)

```bash
# 1. Install Docker
# Windows: https://docs.docker.com/desktop/windows/install/
# macOS: https://docs.docker.com/desktop/mac/install/
# Linux: https://docs.docker.com/engine/install/

# 2. Enable Docker Oracle management
export USE_DOCKER_ORACLE=true
export RUN_INTEGRATION_TESTS=true

# 3. Run integration tests - Oracle automatically configured!
pytest tests/integration/ -v -m oracle

# First run: 3-7 minutes (pulls image ~2.5GB, starts container)
# Subsequent runs: 5-10 seconds (reuses container)
```

---

## Test Organization

```
tests/
├── README.md                       # Quick reference (points to this guide)
├── conftest.py                     # Shared fixtures for unit tests
├── test_transformers.py            # Unit: Data transformations (11 tests)
├── test_validators.py              # Unit: Validation logic (6 tests)
├── test_extractors.py              # Unit: Oracle extractor mocked (20 tests)
├── test_loaders.py                 # Unit: Cosmos loader mocked (24 tests)
└── integration/                    # Integration tests
    ├── conftest.py                 # Integration test fixtures
    ├── docker_oracle_manager.py    # Docker Oracle lifecycle manager
    ├── test_oracle_integration.py  # Real Oracle tests (21 tests)
    └── test_cosmos_integration.py  # Real Cosmos tests (24 tests)
```

---

## Unit Tests

### What's Tested

**Transformers** (`test_transformers.py` - 11 tests):
- Date/timestamp to ISO string conversion
- Decimal to number conversion
- Full DataFrame type conversion
- Partition key calculation
- Document ID generation
- Metadata addition
- Reference document creation

**Validators** (`test_validators.py` - 6 tests):
- Field-level validation (NOT_NULL, POSITIVE, EMAIL_FORMAT, DATE_RANGE, etc.)
- Record-level validation (referential integrity, cross-field constraints)
- Business rules (salary ranges, email uniqueness, self-manager detection)

**Extractors - Mocked** (`test_extractors.py` - 20 tests):
- Connection validation (success/failure scenarios)
- Basic extraction with filters and WHERE clauses
- Convenience methods (extract_regions, extract_employees, etc.)
- Batch operations (extract_all_tables)
- Utility methods (get_table_count, get_all_table_counts)
- Error handling (JDBC errors, empty results)
- Metrics collection

**Loaders - Mocked** (`test_loaders.py` - 24 tests):
- DataFrame validation (id, partitionKey columns)
- Load operations (append, upsert, empty DataFrame)
- Batch operations and repartitioning
- Retry logic for 429 throttling errors
- Cosmos DB configuration options
- Metrics collection and failure tracking
- Upsert operations (insert new, update existing)

### Running Unit Tests

```bash
# All unit tests (excluding integration)
pytest tests/ -v --ignore=tests/integration

# Mocked tests only (fastest - no PySpark needed)
pytest tests/test_extractors.py tests/test_loaders.py -v

# With PySpark (transformers + validators)
pytest tests/test_transformers.py tests/test_validators.py -v

# Specific test class
pytest tests/test_validators.py::TestFieldValidator -v

# Specific test
pytest tests/test_validators.py::TestFieldValidator::test_not_null_validation -v

# With coverage
pytest tests/ --ignore=tests/integration --cov=. --cov-report=html
```

---

## Integration Tests

### Prerequisites

**Required:**
- Oracle Database (or Docker - see next section)
- Azure Cosmos DB account
- Python dependencies: `pip install azure-cosmos python-dotenv`

**HR Schema Requirements:**
- 7 tables: REGIONS, COUNTRIES, LOCATIONS, DEPARTMENTS, JOBS, EMPLOYEES, JOB_HISTORY
- 215 total records (standard Oracle HR sample schema)

### Configuration

Create `.env` file in project root:

```bash
# Enable integration tests
RUN_INTEGRATION_TESTS=true

# Oracle (if using manual setup, not Docker)
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=FREEPDB1
ORACLE_USERNAME=hr
ORACLE_PASSWORD=hr

# Cosmos DB
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your_primary_key_here
COSMOS_DATABASE=test_migration_db
COSMOS_CONTAINER=test_hr_data
```

### What's Tested

**Oracle Integration** (`test_oracle_integration.py` - 21 tests):
- Connection validation and properties
- Data extraction with filters and WHERE clauses
- Batch operations (extract_all_tables)
- Utility methods (row counts, table lists)
- Data quality (null checks, foreign key integrity)
- Metrics collection during extraction
- Performance benchmarks

**Cosmos Integration** (`test_cosmos_integration.py` - 24 tests):
- Connection validation
- Load operations (append, upsert modes)
- Batch operations with repartitioning
- Required field validation (id, partitionKey)
- Retry logic for throttling (429 errors)
- Metrics collection during load
- End-to-end Oracle → Cosmos pipeline
- Performance benchmarks

### Running Integration Tests

```bash
# Setup environment
export RUN_INTEGRATION_TESTS=true

# Run all integration tests
pytest tests/integration/ -v

# Oracle tests only
pytest tests/integration/test_oracle_integration.py -v -m oracle

# Cosmos tests only
pytest tests/integration/test_cosmos_integration.py -v -m cosmos

# Skip slow tests (performance benchmarks)
pytest tests/integration/ -v -m "not slow"

# Parallel execution (faster)
pip install pytest-xdist
pytest tests/integration/ -v -n 4
```

---

## Docker Oracle Integration

### Overview

**Zero manual setup!** The framework automatically manages Oracle Docker containers for integration tests.

**Benefits:**
- ✅ No Oracle installation required
- ✅ Consistent environment across all developers
- ✅ Container reuse (fast subsequent runs)
- ✅ Isolated testing (no shared state)
- ✅ CI/CD ready
- ✅ Automatic HR schema verification

### Quick Start

```bash
# 1. Install Docker
# See: https://docs.docker.com/get-docker/

# 2. Enable Docker Oracle
export USE_DOCKER_ORACLE=true
export RUN_INTEGRATION_TESTS=true

# 3. Run tests (automatic Oracle setup!)
pytest tests/integration/ -v -m oracle
```

**What Happens:**

| Run | Duration | Actions |
|-----|----------|---------|
| **First** | 3-7 min | ✅ Pull image (~2.5GB) → Start container → Wait healthy → Verify schema |
| **Second+** | 5-10 sec | ✅ Detect existing container → Quick health check → Run tests |

### Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `USE_DOCKER_ORACLE` | `false` | Enable Docker Oracle management |
| `RUN_INTEGRATION_TESTS` | `false` | Enable integration tests |
| `ORACLE_AUTO_CLEANUP` | `false` | Remove container after tests |
| `ORACLE_DOCKER_IMAGE` | `gvenzl/oracle-free:23-slim` | Docker image |
| `ORACLE_CONTAINER_NAME` | `pytest-oracle-integration` | Container name |
| `ORACLE_PORT` | `1521` | Host port mapping |
| `ORACLE_PASSWORD` | `OraclePassword123` | SYS password |

### Custom Configuration Example

```bash
# Use custom port and container name
export USE_DOCKER_ORACLE=true
export RUN_INTEGRATION_TESTS=true
export ORACLE_PORT=1522
export ORACLE_CONTAINER_NAME=my-test-oracle
export ORACLE_AUTO_CLEANUP=true  # Remove after tests

pytest tests/integration/ -v -m oracle
```

### Container Management

```bash
# Check status
docker ps | grep pytest-oracle-integration

# View logs
docker logs pytest-oracle-integration

# Connect to database
docker exec -it pytest-oracle-integration sqlplus hr/hr@FREEPDB1

# Stop container (preserves data)
docker stop pytest-oracle-integration

# Start stopped container
docker start pytest-oracle-integration

# Remove container completely
docker stop pytest-oracle-integration
docker rm pytest-oracle-integration
```

### How It Works

**Architecture:**

```
pytest session starts
       ↓
docker_oracle fixture (session-scoped)
       ↓
DockerOracleManager.ensure_oracle_ready()
       ↓
┌──────────────────────────────────┐
│ 1. Check Docker installed        │
│ 2. Pull image (if needed)        │
│ 3. Create/start container        │
│ 4. Wait for healthy (max 180s)   │
│ 5. Verify HR schema (7 tables)   │
└──────────────────────────────────┘
       ↓
Return connection details
       ↓
oracle_config fixture uses Docker config
       ↓
Integration tests run
       ↓
Tests complete
       ↓
Container left running (fast reuse)
```

**DockerOracleManager Class:**

Located in `tests/integration/docker_oracle_manager.py` (~350 lines), this class handles:

- Docker CLI interaction (subprocess-based, no SDK dependency)
- Image pulling with progress monitoring
- Container lifecycle (create, start, stop, remove)
- Health check monitoring
- HR schema verification via SQL
- Connection detail generation
- Error handling with helpful messages

**Key Methods:**
```python
from tests.integration.docker_oracle_manager import DockerOracleManager

manager = DockerOracleManager()

# Check Docker available
if manager.is_docker_available():
    # Setup Oracle
    if manager.ensure_oracle_ready():
        conn = manager.get_connection_details()
        # conn = {
        #     "host": "localhost",
        #     "port": 1521,
        #     "service_name": "FREEPDB1",
        #     "username": "hr",
        #     "password": "hr",
        #     "jdbc_url": "jdbc:oracle:thin:@//localhost:1521/FREEPDB1"
        # }
```

### Manual Oracle Setup (Alternative)

If you prefer not to use Docker:

1. **Don't set** `USE_DOCKER_ORACLE` (or set to `false`)
2. **Configure** Oracle connection in `.env`:
   ```bash
   ORACLE_HOST=your-oracle-host
   ORACLE_PORT=1521
   ORACLE_SERVICE_NAME=ORCL
   ORACLE_USERNAME=hr
   ORACLE_PASSWORD=your_password
   ```
3. **Ensure** HR schema exists with 7 tables and 215 records
4. **Run** tests: `pytest tests/integration/ -v -m oracle`

---

## Running Tests

### Common Scenarios

#### Local Development (Fast Feedback)
```bash
# Run mocked tests only (< 1 second)
pytest tests/test_extractors.py tests/test_loaders.py -v
```

#### Pre-Commit (All Unit Tests)
```bash
# Run all unit tests (< 5 seconds)
pytest tests/ -v --ignore=tests/integration
```

#### Pre-Merge (Full Suite)
```bash
# Enable Docker Oracle
export USE_DOCKER_ORACLE=true
export RUN_INTEGRATION_TESTS=true

# Run everything including integration tests
pytest tests/ -v
```

#### CI/CD Pipeline
```bash
# Stage 1: Unit tests (always)
pytest tests/ -v --ignore=tests/integration --cov=. --cov-report=xml

# Stage 2: Integration tests (scheduled or manual)
export USE_DOCKER_ORACLE=true
export RUN_INTEGRATION_TESTS=true
pytest tests/integration/ -v --cov=extractors --cov=loaders --cov-report=xml
```

### Test Markers

Run tests by category:

```bash
# Integration tests only
pytest tests/ -v -m integration

# Oracle tests only
pytest tests/ -v -m oracle

# Cosmos tests only
pytest tests/ -v -m cosmos

# Slow tests only (performance benchmarks)
pytest tests/ -v -m slow

# Everything except slow tests
pytest tests/ -v -m "not slow"
```

**Available Markers:**
- `integration` - Integration tests (require real databases)
- `oracle` - Tests requiring Oracle database
- `cosmos` - Tests requiring Cosmos DB
- `slow` - Long-running tests (> 5 seconds)

### Debugging

```bash
# Run single test
pytest tests/test_extractors.py::TestOracleExtractorInitialization::test_initialization -v

# Show print statements
pytest tests/test_extractors.py -v -s

# Detailed output
pytest tests/test_extractors.py -vv

# Stop on first failure
pytest tests/ -v -x

# Run failed tests only (from last run)
pytest tests/ -v --lf

# Show slowest 10 tests
pytest tests/ -v --durations=10
```

### Parallel Execution

```bash
# Install plugin
pip install pytest-xdist

# Run with 4 workers
pytest tests/ -v -n 4

# Auto-detect CPU count
pytest tests/ -v -n auto
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install pytest pytest-mock pytest-cov pyspark
      
      - name: Run unit tests
        run: |
          pytest tests/ -v --ignore=tests/integration --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      # Docker-in-Docker for Oracle container
      docker:
        image: docker:20.10.16-dind
        options: --privileged
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install pytest pytest-mock azure-cosmos python-dotenv pyspark
      
      - name: Run integration tests with Docker Oracle
        env:
          USE_DOCKER_ORACLE: true
          RUN_INTEGRATION_TESTS: true
          COSMOS_ENDPOINT: ${{ secrets.COSMOS_ENDPOINT }}
          COSMOS_KEY: ${{ secrets.COSMOS_KEY }}
          COSMOS_DATABASE: test_db
          COSMOS_CONTAINER: test_container
        run: |
          pytest tests/integration/ -v --cov=extractors --cov=loaders --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Azure Pipelines Example

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

stages:
  - stage: UnitTests
    jobs:
      - job: RunUnitTests
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.9'
          
          - script: |
              pip install pytest pytest-mock pytest-cov pyspark
              pytest tests/ -v --ignore=tests/integration --cov=. --cov-report=xml
            displayName: 'Run Unit Tests'
          
          - task: PublishCodeCoverageResults@1
            inputs:
              codeCoverageTool: 'Cobertura'
              summaryFileLocation: 'coverage.xml'

  - stage: IntegrationTests
    dependsOn: UnitTests
    jobs:
      - job: RunIntegrationTests
        steps:
          - task: UsePythonVersion@0
            inputs:
              versionSpec: '3.9'
          
          - script: |
              pip install pytest pytest-mock azure-cosmos python-dotenv pyspark
            displayName: 'Install Dependencies'
          
          - script: |
              export USE_DOCKER_ORACLE=true
              export RUN_INTEGRATION_TESTS=true
              pytest tests/integration/ -v
            displayName: 'Run Integration Tests'
            env:
              COSMOS_ENDPOINT: $(COSMOS_ENDPOINT)
              COSMOS_KEY: $(COSMOS_KEY)
```

---

## Test Coverage

### Current Coverage

| Component | Unit Tests | Integration Tests | Total | Coverage |
|-----------|-----------|-------------------|-------|----------|
| Transformers | 11 | - | 11 | 90%+ |
| Validators | 6 | - | 6 | 85%+ |
| Extractors | 20 (mocked) | 21 (real) | 41 | 85%+ |
| Loaders | 24 (mocked) | 24 (real) | 48 | 80%+ |
| **Total** | **61** | **45** | **106** | **85%+** |

### Generate Coverage Reports

```bash
# HTML report
pytest tests/ --ignore=tests/integration --cov=. --cov-report=html
# Open htmlcov/index.html

# Terminal report with missing lines
pytest tests/ --ignore=tests/integration --cov=. --cov-report=term-missing

# XML report (for CI/CD)
pytest tests/ --ignore=tests/integration --cov=. --cov-report=xml

# Combined report (unit + integration)
pytest tests/ --cov=. --cov-report=html
```

### Coverage Goals

- **Minimum**: 80% for all components
- **Target**: 85%+ overall
- **Critical paths**: 95%+ (extractors, loaders, validators)

---

## Troubleshooting

### Common Issues

#### Issue: Integration tests skipped

**Symptom:** All integration tests show `SKIPPED`

**Solution:**
```bash
# Verify environment variable is set
echo $RUN_INTEGRATION_TESTS  # Should output: true

# Set it if not set
export RUN_INTEGRATION_TESTS=true

# Or use .env file
echo "RUN_INTEGRATION_TESTS=true" >> .env
```

---

#### Issue: Docker not found

**Symptom:** `Docker command not found` or `Docker daemon not running`

**Solution:**
```bash
# Check Docker installed
docker --version

# Check Docker running
docker ps

# Start Docker
# Windows/macOS: Start Docker Desktop
# Linux: sudo systemctl start docker
```

---

#### Issue: Oracle container won't start

**Symptom:** Container exits immediately or health checks fail

**Solution:**
```bash
# Check logs
docker logs pytest-oracle-integration

# Common causes:
# 1. Port 1521 already in use
docker ps -a | grep 1521
export ORACLE_PORT=1522  # Use different port

# 2. Insufficient resources (Docker needs 2GB+ RAM)
# Check Docker Desktop settings

# 3. Corrupted container
docker rm pytest-oracle-integration
pytest tests/integration/ -v -m oracle  # Recreate
```

---

#### Issue: Cosmos DB authentication failed

**Symptom:** `Unauthorized: The input authorization token can't serve the request`

**Solution:**
```bash
# Verify endpoint and key in .env
cat .env | grep COSMOS

# Ensure key is PRIMARY KEY (not connection string)
# Copy from Azure Portal → Cosmos account → Keys

# Check for extra spaces/quotes
# Should be: COSMOS_KEY=your_key_without_quotes
```

---

#### Issue: HR schema not found

**Symptom:** `Table or view does not exist: hr.employees`

**Solution:**
```bash
# For Docker Oracle: Wait for setup to complete
# Schema is created automatically in gvenzl/oracle-free:23-slim

# For manual Oracle: Install HR schema
sqlplus sys/password@ORCL as sysdba
@?/demo/schema/human_resources/hr_main.sql

# Verify schema exists
sqlplus hr/hr@FREEPDB1
SELECT table_name FROM user_tables;
# Should show: REGIONS, COUNTRIES, LOCATIONS, DEPARTMENTS, JOBS, EMPLOYEES, JOB_HISTORY
```

---

#### Issue: PySpark not found

**Symptom:** `ModuleNotFoundError: No module named 'pyspark'`

**Solution:**
```bash
# Install PySpark
pip install pyspark

# Or use requirements.txt
pip install -r requirements.txt

# Verify installation
python -c "import pyspark; print(pyspark.__version__)"
```

---

#### Issue: Tests very slow

**Symptom:** Unit tests taking > 10 seconds

**Solution:**
```bash
# Run mocked tests only (skip PySpark tests)
pytest tests/test_extractors.py tests/test_loaders.py -v

# Use parallel execution
pip install pytest-xdist
pytest tests/ -v -n auto

# Skip slow tests
pytest tests/ -v -m "not slow"

# Profile slow tests
pytest tests/ -v --durations=10
```

---

### Getting Help

**Check Test Logs:**
```bash
# Verbose output
pytest tests/ -vv

# Show print statements
pytest tests/ -v -s

# Full traceback
pytest tests/ -v --tb=long
```

**Enable Debug Logging:**
```python
# In test file
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Verify Configuration:**
```bash
# Check environment
env | grep -E '(ORACLE|COSMOS|RUN_INTEGRATION)'

# Validate connections
python -c "
from config.connections import get_oracle_config, get_cosmos_config
print('Oracle:', get_oracle_config())
print('Cosmos:', get_cosmos_config())
"
```

---

## Best Practices

### Development Workflow

1. **Frequent** - Run mocked tests (< 1 second)
   ```bash
   pytest tests/test_extractors.py tests/test_loaders.py -v
   ```

2. **Pre-commit** - Run all unit tests (< 5 seconds)
   ```bash
   pytest tests/ -v --ignore=tests/integration
   ```

3. **Pre-merge** - Run full suite including integration
   ```bash
   export USE_DOCKER_ORACLE=true
   export RUN_INTEGRATION_TESTS=true
   pytest tests/ -v
   ```

4. **CI/CD** - Unit tests always, integration tests on schedule

### Writing Tests

- **Keep unit tests fast** (< 0.1 seconds each)
- **Mock external dependencies** in unit tests
- **Use integration tests** for end-to-end validation
- **Mark slow tests** with `@pytest.mark.slow`
- **Clean up test data** in integration tests
- **Use descriptive test names** (`test_extract_with_invalid_table_name`)
- **Add docstrings** explaining what's being tested

### Test Isolation

- **Unit tests**: No shared state between tests
- **Integration tests**: Use unique container names per test
- **Fixtures**: Use appropriate scope (function vs session)
- **Cleanup**: Always clean up test data in teardown

---

## Performance Benchmarks

### Expected Performance

| Test Category | Count | Runtime | Notes |
|--------------|-------|---------|-------|
| Mocked tests | 44 | < 1 sec | Fastest feedback |
| All unit tests | 61 | < 5 sec | Pre-commit |
| Integration (cached) | 45 | 2-3 min | Container reused |
| Integration (cold) | 45 | 5-10 min | First run + image pull |
| **Full suite** | **106** | **2-10 min** | Depends on cache |

### Optimization Tips

- **Parallel execution**: Use `-n auto` for 2-4x speedup
- **Skip slow tests**: Use `-m "not slow"` during development
- **Container reuse**: Keep Docker Oracle running between test runs
- **Selective running**: Run only changed components
- **Cache dependencies**: Cache pip packages in CI/CD

---

## Related Documentation

- **[Getting Started Guide](GETTING_STARTED.md)** - Setup and first migration
- **[Operations Guide](OPERATIONS_GUIDE.md)** - Development and deployment
- **[Implementation Design](../implementation-design.md)** - Architecture details

---

**Need help?** Check the troubleshooting section or file an issue on GitHub.

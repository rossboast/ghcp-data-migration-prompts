# Test Suite# Test Suite Documentation



Complete test suite with 106 tests covering unit tests (mocked) and integration tests (real databases).Comprehensive test suite for the PySpark migration framework with both unit tests (mocked) and integration tests (real databases).



---## Test Organization



## Quick Start```

tests/

### Unit Tests (Fast, No Setup)├── README.md                       # This file

├── conftest.py                     # Shared fixtures for unit tests

```bash├── test_transformers.py            # Unit tests for transformers (11 tests)

# Install dependencies├── test_validators.py              # Unit tests for validators (6 tests)

pip install pytest pytest-mock pyspark├── test_extractors.py              # Mocked unit tests for extractors (20 tests)

├── test_loaders.py                 # Mocked unit tests for loaders (24 tests)

# Run all unit tests└── integration/                    # Integration tests with real databases

pytest tests/ -v --ignore=tests/integration    ├── README.md                   # Integration test documentation

    ├── conftest.py                 # Integration test fixtures

# Run mocked tests only (< 1 second)    ├── test_oracle_integration.py  # Oracle extractor integration tests

pytest tests/test_extractors.py tests/test_loaders.py -v    └── test_cosmos_integration.py  # Cosmos loader integration tests

``````



### Integration Tests with Docker Oracle## Test Categories



```bash### Unit Tests (Mocked) - No Database Required

# Enable Docker Oracle management- **test_transformers.py** - Data type conversion and transformations

export USE_DOCKER_ORACLE=true- **test_validators.py** - Field, record, and business rule validation

export RUN_INTEGRATION_TESTS=true- **test_extractors.py** - Oracle extractor with mocked SparkSession and JDBC

- **test_loaders.py** - Cosmos loader with mocked Cosmos SDK

# Run integration tests (Oracle automatically configured!)

pytest tests/integration/ -v -m oracle**Total**: 61 unit tests | **Runtime**: < 1 second | **Dependencies**: pytest, pytest-mock



# First run: 3-7 min | Subsequent runs: 5-10 sec### Integration Tests - Require Real Databases

```- **test_oracle_integration.py** - Real Oracle database extraction

- **test_cosmos_integration.py** - Real Cosmos DB loading

---

**Total**: 40+ integration tests | **Runtime**: 2-10 minutes | **Dependencies**: Oracle DB, Cosmos DB

## Test Statistics

## Quick Start

| Type | Count | Runtime | Dependencies |

|------|-------|---------|-------------|### Unit Tests (Fast, No Setup)

| **Unit Tests** (mocked) | 61 | < 5 sec | pytest, pytest-mock, PySpark |

| **Integration Tests** | 45 | 2-10 min | Oracle DB, Cosmos DB |```bash

| **Total** | **106** | **2-10 min** | Full stack |# Install dependencies

pip install pytest pytest-mock

---

# Run all unit tests

## Test Organizationpytest tests/ -v --ignore=tests/integration



```# Run mocked tests only (no PySpark needed for extractors/loaders)

tests/pytest tests/test_extractors.py tests/test_loaders.py -v

├── README.md                       # This file (quick reference)

├── conftest.py                     # Shared fixtures for unit tests# Run with coverage

├── test_transformers.py            # Data transformations (11 tests)pytest tests/ --ignore=tests/integration --cov=. --cov-report=html

├── test_validators.py              # Validation logic (6 tests)```

├── test_extractors.py              # Oracle extractor mocked (20 tests)

├── test_loaders.py                 # Cosmos loader mocked (24 tests)### Integration Tests (Requires Setup)

└── integration/                    # Integration tests

    ├── conftest.py                 # Integration test fixturesSee **[Integration Test README](integration/README.md)** for complete setup instructions.

    ├── docker_oracle_manager.py    # Docker Oracle lifecycle manager

    ├── test_oracle_integration.py  # Real Oracle tests (21 tests)```bash

    └── test_cosmos_integration.py  # Real Cosmos tests (24 tests)# Set environment variable

```export RUN_INTEGRATION_TESTS=true



---# Run all integration tests

pytest tests/integration/ -v

## Common Commands

# Run Oracle tests only

```bashpytest tests/integration/ -v -m oracle

# Run all unit tests (excluding integration)

pytest tests/ -v --ignore=tests/integration# Run Cosmos tests only

pytest tests/integration/ -v -m cosmos

# Run mocked tests only (fastest)```

pytest tests/test_extractors.py tests/test_loaders.py -v

## Test Coverage Summary

# Run with coverage

pytest tests/ --ignore=tests/integration --cov=. --cov-report=html| Component | Unit Tests | Integration Tests | Total | Status |

|-----------|-----------|-------------------|-------|--------|

# Run integration tests| Transformers | 11 | - | 11 | ✅ Complete |

export USE_DOCKER_ORACLE=true| Validators | 6 | - | 6 | ✅ Complete |

export RUN_INTEGRATION_TESTS=true| Extractors | 20 (mocked) | 21 (real DB) | 41 | ✅ Complete |

pytest tests/integration/ -v| Loaders | 24 (mocked) | 24 (real DB) | 48 | ✅ Complete |

| **Total** | **61** | **45** | **106** | ✅ Complete |

# Run by marker

pytest tests/ -v -m oracle      # Oracle tests only## Running Tests

pytest tests/ -v -m cosmos      # Cosmos tests only

pytest tests/ -v -m "not slow"  # Skip slow tests### Install Test Dependencies



# Debugging```bash

pytest tests/test_extractors.py::TestOracleExtractorInitialization::test_initialization -v# Unit tests only

pytest tests/ -v -s            # Show print statementspip install pytest pytest-mock

pytest tests/ -v -x            # Stop on first failure

pytest tests/ -v --lf          # Run failed tests only# Unit tests + PySpark (for transformers/validators)

```pip install pytest pytest-mock pyspark



---# Integration tests (includes everything)

pip install pytest pytest-mock pyspark azure-cosmos python-dotenv

## Docker Oracle Integration```



**Zero manual Oracle setup!** The framework automatically manages Oracle Docker containers for integration tests.### Run All Unit Tests



```bash```bash

# Enable Docker Oracle# Run all unit tests (excluding integration)

export USE_DOCKER_ORACLE=truepytest tests/ -v --ignore=tests/integration

export RUN_INTEGRATION_TESTS=true

# Run with coverage

# Run tests (Oracle setup automatic!)pytest tests/ --ignore=tests/integration --cov=. --cov-report=html

pytest tests/integration/ -v -m oracle

```# Run specific test file

pytest tests/test_transformers.py -v

**What happens:**

- **First run**: Pulls Oracle image (~2.5GB), starts container, waits for healthy (3-7 min)# Run specific test class

- **Subsequent runs**: Reuses existing container (5-10 sec)pytest tests/test_validators.py::TestFieldValidator -v



**Container management:**# Run specific test

```bashpytest tests/test_validators.py::TestFieldValidator::test_not_null_validation -v

# Check status```

docker ps | grep pytest-oracle-integration

### Run Mocked Tests (No Database Dependencies)

# View logs

docker logs pytest-oracle-integration```bash

# Run only mocked extractor and loader tests

# Stop container (preserves data)pytest tests/test_extractors.py tests/test_loaders.py -v

docker stop pytest-oracle-integration

# These tests use unittest.mock and require no external dependencies

# Remove container# Perfect for local development and CI/CD

docker rm pytest-oracle-integration```

```

## Test Coverage Details

---

### Transformers (test_transformers.py)

## Configuration- ✅ Date/timestamp to ISO string conversion

- ✅ Decimal to number conversion

### Unit Tests (No Configuration)- ✅ Full DataFrame type conversion

- ✅ Partition key calculation

Unit tests use mocking and require no database configuration.- ✅ Document ID generation

- ✅ Metadata addition

### Integration Tests- ✅ Reference document creation



Create `.env` file in project root:### Validators (test_validators.py)

- ✅ Field-level validation (NOT_NULL, POSITIVE, EMAIL_FORMAT, DATE_RANGE, etc.)

```bash- ✅ Multiple validation rules per field

# Enable integration tests- ✅ Record-level validation (referential integrity, cross-field constraints)

RUN_INTEGRATION_TESTS=true- ✅ Business rules (salary ranges, email uniqueness, self-manager detection)



# Docker Oracle (automatic setup)### Extractors - Mocked (test_extractors.py)

USE_DOCKER_ORACLE=true- ✅ Initialization and configuration

- ✅ Connection validation (success/failure)

# Manual Oracle (if not using Docker)- ✅ Basic extraction with filters and WHERE clauses

ORACLE_HOST=localhost- ✅ Convenience methods (extract_regions, extract_employees, etc.)

ORACLE_PORT=1521- ✅ Batch operations (extract_all_tables)

ORACLE_SERVICE_NAME=FREEPDB1- ✅ Utility methods (get_table_count, get_all_table_counts)

ORACLE_USERNAME=hr- ✅ Error handling (JDBC errors, empty results)

ORACLE_PASSWORD=hr- ✅ Metrics collection



# Cosmos DB (required)### Loaders - Mocked (test_loaders.py)

COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/- ✅ Initialization with various configurations

COSMOS_KEY=your_primary_key- ✅ DataFrame validation (id, partitionKey columns)

COSMOS_DATABASE=test_db- ✅ Load operations (append, upsert, empty DataFrame)

COSMOS_CONTAINER=test_container- ✅ Batch operations and repartitioning

```- ✅ Retry logic for 429 throttling errors

- ✅ Cosmos DB configuration options

---- ✅ Metrics collection and failure tracking

- ✅ Error handling (invalid endpoint, connection errors)

## Test Coverage- ✅ Upsert operations (insert new, update existing)



| Component | Unit Tests | Integration Tests | Total | Coverage |### Integration Tests

|-----------|-----------|-------------------|-------|----------|See **[Integration Test README](integration/README.md)** for complete coverage details.

| Transformers | 11 | - | 11 | 90%+ |

| Validators | 6 | - | 6 | 85%+ |## Integration Tests Overview

| Extractors | 20 (mocked) | 21 (real) | 41 | 85%+ |

| Loaders | 24 (mocked) | 24 (real) | 48 | 80%+ |For full end-to-end testing with actual Oracle and Cosmos DB, see the dedicated integration test directory.

| **Total** | **61** | **45** | **106** | **85%+** |

---

---

## 🐳 Automatic Docker Oracle Setup

## Comprehensive Documentation

Integration tests can now automatically manage Oracle Docker containers, eliminating manual setup!

For complete testing documentation, including:

- Detailed test coverage### Quick Start with Docker

- CI/CD integration examples

- Troubleshooting guide```bash

- Docker Oracle architecture# 1. Install Docker (if not already installed)

- Performance benchmarks# Windows: https://docs.docker.com/desktop/windows/install/

- Best practices# macOS: https://docs.docker.com/desktop/mac/install/

# Linux: https://docs.docker.com/engine/install/

**See:** [**Testing Guide (docs/TESTING_GUIDE.md)**](../docs/TESTING_GUIDE.md)

# 2. Enable Docker Oracle management

---export USE_DOCKER_ORACLE=true

export RUN_INTEGRATION_TESTS=true

## Development Workflow

# 3. Run integration tests - Oracle automatically configured!

```bashpytest tests/integration/ -v -m oracle

# 1. Frequent - Run mocked tests (< 1 second)

pytest tests/test_extractors.py tests/test_loaders.py -v# First run: 3-7 minutes (pulls image, starts container, waits for ready)

# Subsequent runs: 5-10 seconds (reuses existing container)

# 2. Pre-commit - Run all unit tests (< 5 seconds)```

pytest tests/ -v --ignore=tests/integration

### Configuration Options

# 3. Pre-merge - Run full suite including integration

export USE_DOCKER_ORACLE=true| Environment Variable | Default | Description |

export RUN_INTEGRATION_TESTS=true|---------------------|---------|-------------|

pytest tests/ -v| `USE_DOCKER_ORACLE` | `false` | Enable automatic Docker Oracle management |

```| `RUN_INTEGRATION_TESTS` | `false` | Enable integration tests |

| `ORACLE_AUTO_CLEANUP` | `false` | Remove container after tests (default: keep running) |

---| `ORACLE_DOCKER_IMAGE` | `gvenzl/oracle-free:23-slim` | Oracle Docker image to use |

| `ORACLE_CONTAINER_NAME` | `pytest-oracle-integration` | Container name |

## Troubleshooting| `ORACLE_PORT` | `1521` | Host port mapping |

| `ORACLE_PASSWORD` | `OraclePassword123` | SYS/SYSTEM password |

### Integration tests skipped?

### Usage Examples

```bash

# Verify environment variable#### Automatic Mode (Recommended)

echo $RUN_INTEGRATION_TESTS  # Should output: true

```bash

# Set if not set# Windows PowerShell

export RUN_INTEGRATION_TESTS=true$env:USE_DOCKER_ORACLE="true"

```$env:RUN_INTEGRATION_TESTS="true"

pytest tests/integration/ -v -m oracle

### Docker not found?

# Linux/macOS

```bashexport USE_DOCKER_ORACLE=true

# Check Dockerexport RUN_INTEGRATION_TESTS=true

docker --versionpytest tests/integration/ -v -m oracle

docker ps```



# Install Docker: https://docs.docker.com/get-docker/#### Manual Mode (Existing Oracle Instance)

```

```bash

### PySpark not found?# Don't set USE_DOCKER_ORACLE (or set to false)

export RUN_INTEGRATION_TESTS=true

```bash

# Install PySpark# Configure connection in .env

pip install pyspark# ORACLE_HOST=localhost

# ORACLE_PORT=1521

# Verify# ORACLE_SERVICE=FREEPDB1

python -c "import pyspark; print(pyspark.__version__)"# ORACLE_USER=hr

```# ORACLE_PASSWORD=hr



### Need more help?pytest tests/integration/ -v -m oracle

```

See the [**Testing Guide**](../docs/TESTING_GUIDE.md) for comprehensive troubleshooting.

### How It Works

---

1. **First Test Run**:

## Related Documentation   - ✅ Checks if Docker is installed

   - ✅ Pulls Oracle Docker image (~2.5GB, one-time download)

- **[Getting Started Guide](../docs/GETTING_STARTED.md)** - Setup and first migration   - ✅ Starts container with health checks enabled

- **[Testing Guide](../docs/TESTING_GUIDE.md)** - Complete testing documentation ⭐   - ✅ Waits for healthy status (30-90 seconds)

- **[Operations Guide](../docs/OPERATIONS_GUIDE.md)** - Development and deployment   - ✅ Verifies HR schema exists (7 tables)

- **[Implementation Design](../implementation-design.md)** - Architecture details   - ✅ Runs integration tests

   - ✅ **Leaves container running** for next time

2. **Subsequent Test Runs**:
   - ✅ Detects existing container (instant)
   - ✅ Verifies it's running and healthy (~5-10 seconds)
   - ✅ Runs integration tests immediately

3. **Cleanup**:
   - Default: Container left running for fast reruns
   - Optional: Set `ORACLE_AUTO_CLEANUP=true` to remove after tests

### Container Management

```bash
# Check container status
docker ps -a | grep pytest-oracle

# View container logs
docker logs pytest-oracle-integration

# Stop container (keep data)
docker stop pytest-oracle-integration

# Start stopped container
docker start pytest-oracle-integration

# Remove container completely
docker rm -f pytest-oracle-integration

# Remove image (reclaim disk space)
docker rmi gvenzl/oracle-free:23-slim
```

### Performance Comparison

| Scenario | Time | Notes |
|----------|------|-------|
| **First run (image not pulled)** | 3-7 min | One-time download (~2.5GB) |
| **First run (image exists)** | 30-90 sec | Container startup + health checks |
| **Subsequent runs** | 5-10 sec | Container reuse, just verification |
| **Manual setup** | 10-30 min | Download, install, configure Oracle |

### Troubleshooting

#### "Docker not installed"
```bash
# Install Docker and ensure it's running
docker --version
docker ps
```

#### "Container failed health checks"
```bash
# View container logs for errors
docker logs pytest-oracle-integration

# Check container health status
docker inspect pytest-oracle-integration --format='{{.State.Health.Status}}'

# Restart container
docker restart pytest-oracle-integration
```

#### "HR schema not found"
```bash
# Connect to container and verify schema
docker exec -it pytest-oracle-integration sqlplus hr/hr@FREEPDB1

SQL> SELECT table_name FROM user_tables;
# Should show: REGIONS, COUNTRIES, LOCATIONS, DEPARTMENTS, JOBS, EMPLOYEES, JOB_HISTORY
```

#### "Port 1521 already in use"
```bash
# Use different port
export ORACLE_PORT=1522
pytest tests/integration/ -v -m oracle
```

#### "Container exists but won't start"
```bash
# Remove and recreate
docker rm -f pytest-oracle-integration
pytest tests/integration/ -v -m oracle
```

### CI/CD Integration

Docker Oracle can be used in CI/CD pipelines with Docker-in-Docker:

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      docker:
        image: docker:dind
        options: --privileged
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-mock
      
      - name: Run integration tests with Docker Oracle
        env:
          USE_DOCKER_ORACLE: true
          RUN_INTEGRATION_TESTS: true
          ORACLE_AUTO_CLEANUP: true  # Clean up in CI
        run: |
          pytest tests/integration/ -v -m oracle --tb=short
```

### Benefits

✅ **Zero Manual Setup** - No Oracle installation required  
✅ **Fast Reruns** - Container reuse makes subsequent runs instant  
✅ **Consistent Environment** - Same Oracle version for all developers  
✅ **Isolated Testing** - Dedicated container per developer  
✅ **CI/CD Ready** - Works in automated pipelines  
✅ **Easy Cleanup** - `docker rm` removes everything  

---

## Writing New Tests

### Example Test Structure

```python
import pytest
from pyspark.sql import SparkSession

@pytest.fixture(scope="module")
def spark():
    """Create Spark session for testing."""
    spark = SparkSession.builder \
        .appName("TestMyComponent") \
        .master("local[*]") \
        .getOrCreate()
    yield spark
    spark.stop()

class TestMyComponent:
    """Test MyComponent functionality."""
    
    def test_my_feature(self, spark):
        """Test specific feature."""
        # Arrange
        data = [(1, "test")]
        df = spark.createDataFrame(data, ["id", "value"])
        
        # Act
        result = my_component.process(df)
        
        # Assert
        assert result.count() == 1
```

## Best Practices

1. **Use fixtures** - Share Spark sessions across tests for performance
2. **Test edge cases** - NULL values, empty DataFrames, invalid data
3. **Verify error handling** - Ensure exceptions are raised correctly
4. **Check data types** - Validate schema transformations
5. **Test validation logic** - Ensure rules catch violations

## CI/CD Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# .github/workflows/test.yml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: pytest tests/ -v --cov=. --cov-report=xml
```

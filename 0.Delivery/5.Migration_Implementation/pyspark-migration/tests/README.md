# Unit Tests

Comprehensive test suite for the PySpark migration framework.

## Test Structure

- `test_transformers.py` - Tests for data type conversion and common transformations
- `test_validators.py` - Tests for field, record, and business rule validation

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-cov
```

### Run All Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_transformers.py -v

# Run specific test class
pytest tests/test_validators.py::TestFieldValidator -v

# Run specific test
pytest tests/test_validators.py::TestFieldValidator::test_not_null_validation -v
```

## Test Coverage

The test suite covers:

### Transformers
- ✅ Date/timestamp to ISO string conversion
- ✅ Decimal to number conversion
- ✅ Full DataFrame type conversion
- ✅ Partition key calculation
- ✅ Document ID generation
- ✅ Metadata addition
- ✅ Reference document creation

### Validators
- ✅ Field-level validation (NOT_NULL, POSITIVE, EMAIL_FORMAT, DATE_RANGE, etc.)
- ✅ Multiple validation rules per field
- ✅ Record-level validation (referential integrity, cross-field constraints)
- ✅ Business rules (salary ranges, email uniqueness, self-manager detection)

## Integration Tests

For full end-to-end testing with actual Oracle and Cosmos DB:

1. Set up test environment variables in `.env.test`
2. Create test Oracle schema with sample data
3. Create test Cosmos DB database
4. Run integration tests:

```bash
pytest tests/integration/ -v
```

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

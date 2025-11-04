# PySpark Migration Framework

Production-grade framework for migrating Oracle HR database to Azure Cosmos DB using Apache Spark.

## 🚀 Features

- **Complete ETL Pipeline**: Extract → Transform → Validate → Load
- **Complex Denormalization**: 6-way joins with nested document structures
- **3-Tier Validation**: Field-level, Record-level, Business rules
- **Checkpoint/Restart**: Resume from failures automatically
- **Production-Ready**: Retry logic, metrics, structured logging, error handling
- **Scalable**: Process millions of records with distributed computing
- **Observable**: Comprehensive logging and metrics collection

## 📋 Quick Start

### Prerequisites

- **Python 3.9-3.12** (3.11 recommended)
- **Java 8 or 11** (for PySpark) - or Java 17 for newer features
- **Conda/Miniconda** (recommended for Windows)
- Oracle JDBC driver (ojdbc8.jar)
- Azure Cosmos DB account

> **💡 Platform-Specific Setup Guides:**
> - **Windows**: Follow instructions below
> - **Linux/WSL**: See [docs/LINUX_SETUP.md](docs/LINUX_SETUP.md) - ✅ **No Hadoop/winutils issues!**

### Installation

#### Option 1: Conda (Recommended for Windows)

```powershell
# Create conda environment
conda env create -f environment.yml

# Activate environment
conda activate pyspark-migration

# Configure environment
Copy-Item .env.example .env
# Edit .env with your credentials
```

See [CONDA_SETUP.md](CONDA_SETUP.md) for detailed instructions.

#### Option 2: pip with venv (Windows)

```powershell
# Requires Python 3.9-3.12 (NOT 3.13)
python -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt

# Configure environment
Copy-Item .env.example .env
# Edit .env with your credentials
```

**Note:** On Windows with Python 3.13, use conda to avoid compilation issues.

#### Option 3: pip with venv (Linux/WSL)

```bash
# Requires Python 3.11+
python3.11 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

# Use Linux-specific environment config
cp .env.linux .env
# Edit .env with your credentials
```

See [docs/LINUX_SETUP.md](docs/LINUX_SETUP.md) for complete Linux/WSL setup guide.

### Basic Usage

```bash
# Run pre-flight checks
python orchestration/run_all_migrations.py --pre-flight-only

# Dry run (no actual loading)
python orchestration/run_all_migrations.py --dry-run

# Execute complete migration
python orchestration/run_all_migrations.py

# Validate migration
python orchestration/run_all_migrations.py --validate-only
```

## 📖 Documentation

Comprehensive documentation available in the `docs/` directory:

- **[Setup Guide](docs/setup-guide.md)** - Environment setup, JDBC driver, Cosmos DB configuration
- **[Developer Guide](docs/developer-guide.md)** - Architecture, extending framework, best practices
- **[Deployment Guide](docs/deployment-guide.md)** - Production deployment, monitoring, scaling

## 🏗️ Architecture

### Layered Design

```
Orchestration Layer
   ↓
Extract → Transform → Validate → Load
   ↓         ↓          ↓         ↓
Oracle   DataTypes  Validators  Cosmos DB
```

### Components

**Extractors**
- `OracleExtractor` - Extract data from Oracle via JDBC

**Transformers**
- `DataTypeConverter` - Oracle → JSON type conversion
- `CommonTransformations` - Reusable transformation utilities
- `EmployeeTransformer` - Complex denormalization with 6-way joins

**Validators**
- `FieldValidator` - Field-level validation (11 rule types)
- `RecordValidator` - Referential integrity, cross-field validation
- `BusinessRuleValidator` - Domain-specific business rules

**Loaders**
- `CosmosLoader` - Load to Azure Cosmos DB with retry logic

**Orchestration**
- `migrate_reference_data.py` - Phase 1-2 (reference data)
- `migrate_employees.py` - Phase 3-4 (employee data)
- `run_all_migrations.py` - Complete end-to-end migration

## 📊 Migration Phases

### Phase 1-2: Reference Data
- Regions, Countries, Locations, Jobs
- Departments (with NULL manager_id)
- ~98 records
- Single container with entity type discrimination

### Phase 3-4: Employee Data
- 107 employees with full denormalization
- 6-way join: employees → departments → jobs → locations → countries → regions
- Manager details (self-join)
- Job history aggregation
- Resolve circular department.manager_id references

## 🔧 Configuration

### Environment Variables

```bash
# Oracle Database
ORACLE_HOST=oracle-host.database.com
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=ORCLPDB1
ORACLE_USER=hr
ORACLE_PASSWORD=<password>

# Azure Cosmos DB
COSMOS_ENDPOINT=https://<account>.documents.azure.com:443/
COSMOS_KEY=<primary-key>
COSMOS_DATABASE=hr_migration
COSMOS_REFERENCE_CONTAINER=reference_data
COSMOS_EMPLOYEE_CONTAINER=employees

# Spark Configuration
SPARK_MASTER=local[*]
SPARK_DRIVER_MEMORY=4g
SPARK_EXECUTOR_MEMORY=4g
SPARK_JDBC_DRIVER_PATH=./jars/ojdbc8.jar
```

### Batch Size Tuning

```python
# Small documents (<1KB)
loader = CosmosLoader(config, container, batch_size=2000)

# Medium documents (1-5KB)
loader = CosmosLoader(config, container, batch_size=1000)

# Large documents (>5KB)
loader = CosmosLoader(config, container, batch_size=500)
```

## ✅ Validation

### Field-Level Rules

- NOT_NULL, POSITIVE, NON_NEGATIVE
- EMAIL_FORMAT, PHONE_FORMAT
- DATE_RANGE, SALARY_RANGE
- LENGTH_MIN, LENGTH_MAX, PATTERN

### Record-Level Checks

- Referential integrity (FK validation)
- Cross-field constraints (date ranges, salary ranges)
- Required field combinations

### Business Rules

- Salary within job min/max ranges
- Manager hierarchy (no circular references)
- Email uniqueness
- Job history consistency (no overlaps)
- Department-location validity

## 📈 Monitoring

### Structured Logging

All components emit JSON-formatted logs:

```json
{
  "timestamp": "2024-01-15T10:30:45Z",
  "level": "INFO",
  "logger": "employee_migration",
  "message": "Phase 3 completed",
  "context": {
    "records_migrated": 107,
    "duration_seconds": 245.6,
    "validation_passed": true
  }
}
```

### Metrics Collection

Automatic tracking of:
- Records processed
- Errors and retries
- Duration and throughput
- RU consumption (Cosmos DB)
- Validation results

## 🧪 Testing

### Unit Tests

```bash
# Run all unit tests (67 tests)
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_transformers.py -v
```

**Expected Results:** 67 tests passing in ~5-10 minutes

### Integration Tests

Integration tests use Docker Oracle container for end-to-end testing.

**Windows:**
```powershell
# Using helper script
.\run-integration-tests.ps1

# Or manually
$env:USE_DOCKER_ORACLE = "true"
pytest tests/integration/ -v
```

**Linux/WSL:**
```bash
# Using helper script
chmod +x run-integration-tests.sh
./run-integration-tests.sh

# Or manually
export USE_DOCKER_ORACLE=true
pytest tests/integration/ -v
```

**Expected Results:** 19 tests passing in ~2-5 minutes (first run), ~30-60 seconds (subsequent runs)

**Note:** Integration tests on Windows require [HADOOP_HOME setup](docs/LINUX_SETUP.md#advantages-of-linuxwsl). Consider using Linux/WSL for easier setup.

## 🎯 Use Cases

### Scenario 1: Initial Migration

```bash
# Complete migration with all phases
python orchestration/run_all_migrations.py
```

### Scenario 2: Resume After Failure

```bash
# Automatically resumes from checkpoint
python orchestration/run_all_migrations.py
```

### Scenario 3: Re-run Specific Phase

```bash
# Re-migrate employees only
python orchestration/migrate_employees.py --phase 3 --force
```

### Scenario 4: Validation Only

```bash
# Validate without migrating
python orchestration/run_all_migrations.py --validate-only
```

## 🔄 Checkpoint/Restart

Framework automatically saves checkpoints:

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

**Benefits:**
- Resume from failures automatically
- Skip already-completed phases
- Track progress across runs
- Idempotent execution

## 📦 Project Structure

```
pyspark-migration/
├── config/                    # Configuration management
│   ├── connections.py         # Database connection configs
│   ├── schema_definitions.py  # Schema definitions
│   └── transformation_config.py
├── extractors/                # Data extraction
│   └── oracle_extractor.py
├── transformers/              # Data transformation
│   ├── data_type_converter.py
│   ├── common_transformations.py
│   └── employee_transformer.py
├── validators/                # Data validation
│   ├── field_validator.py
│   ├── record_validator.py
│   └── business_rule_validator.py
├── loaders/                   # Data loading
│   └── cosmos_loader.py
├── orchestration/             # Migration orchestration
│   ├── migrate_reference_data.py
│   ├── migrate_employees.py
│   └── run_all_migrations.py
├── utils/                     # Utilities
│   ├── logging_config.py
│   ├── error_handler.py
│   ├── spark_session.py
│   └── metrics.py
├── tests/                     # Unit tests
│   ├── test_transformers.py
│   └── test_validators.py
├── docs/                      # Documentation
│   ├── setup-guide.md
│   ├── developer-guide.md
│   └── deployment-guide.md
└── requirements.txt
```

## 🚨 Error Handling

### Automatic Retry

Cosmos DB loader automatically retries on throttling (429 errors):

```python
@retry(
    max_attempts=5,
    initial_delay=2.0,
    backoff_multiplier=2.0
)
def load_batch(self, batch_df, batch_number):
    # Automatic exponential backoff: 2s → 4s → 8s → 16s → 32s
    pass
```

### Graceful Degradation

- Validation warnings don't stop migration
- Partial failures logged and tracked
- Checkpoint saved after each phase

## 🔐 Security

### Credential Management

- Never commit `.env` files
- Use Azure Key Vault for production
- Rotate credentials regularly

### Network Security

- Azure Private Link for Cosmos DB
- Firewall rules on Oracle and Cosmos
- TLS 1.2+ for all connections

### Data Encryption

- At-rest: Cosmos DB encrypted by default
- In-transit: TLS encryption on all connections
- Customer-managed keys supported

## 📊 Performance

### Typical Performance

| Dataset Size | Duration | Throughput |
|-------------|----------|------------|
| 100 records | 30-60s | 2 rec/s |
| 1K records | 2-5 min | 5 rec/s |
| 10K records | 10-20 min | 10 rec/s |
| 100K records | 1-2 hours | 20 rec/s |

### Optimization Tips

1. **Increase Spark memory** for large datasets
2. **Scale Cosmos RUs** during migration
3. **Use larger batches** for small documents
4. **Partition DataFrames** for parallel processing
5. **Cache reference data** used in multiple joins

## 🤝 Contributing

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run linters
flake8 .
black .

# Run tests
pytest tests/ -v --cov=.
```

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for all public methods
- Include unit tests for new features

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

- Apache Spark team
- Azure Cosmos DB team
- Oracle database documentation
- Python community

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check documentation in `docs/`
- Review troubleshooting section in [Deployment Guide](docs/deployment-guide.md)

---

**Built with ❤️ using PySpark, Azure Cosmos DB, and Python**

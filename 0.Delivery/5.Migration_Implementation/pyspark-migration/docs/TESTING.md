# Quick Reference: Running Tests

## Platform Commands

### Windows (PowerShell)

```powershell
# Setup
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Unit Tests (67 tests, ~5-10 min)
pytest tests/unit/ -v

# Integration Tests (19 tests, ~2-5 min first run)
.\run-integration-tests.ps1

# Specific test
pytest tests/unit/test_validators.py::TestFieldValidator -v
```

### Linux/WSL (Bash)

```bash
# Setup
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.linux .env

# Unit Tests (67 tests, ~5-10 min)
pytest tests/unit/ -v

# Integration Tests (19 tests, ~2-5 min first run)
chmod +x run-integration-tests.sh
./run-integration-tests.sh

# Specific test
pytest tests/unit/test_validators.py::TestFieldValidator -v
```

## Test Structure

```
tests/
├── unit/                      # 67 unit tests (no Spark/Docker needed)
│   ├── test_extractors.py    # 24 tests - Oracle JDBC extraction
│   ├── test_loaders.py        # 22 tests - Cosmos DB loading
│   ├── test_transformers.py   # 11 tests - Data transformation
│   └── test_validators.py     # 10 tests - Validation rules
│
└── integration/               # 19 integration tests (Docker Oracle)
    ├── conftest.py            # Test fixtures, Docker setup
    ├── docker_oracle_manager.py  # Automated container management
    └── test_oracle_integration.py  # End-to-end tests
```

## Docker Oracle Management

### Check Container Status
```bash
docker ps -a | grep oracle-test
```

### View Logs
```bash
docker logs oracle-test
```

### Stop Container
```bash
docker stop oracle-test
```

### Remove Container
```bash
docker rm -f oracle-test
```

### Manual Container Start
```bash
docker run -d \
  --name oracle-test \
  -p 1521:1521 \
  -e ORACLE_PASSWORD=oracle \
  -e APP_USER=hr \
  -e APP_USER_PASSWORD=hr \
  gvenzl/oracle-free:23-slim-faststart
```

## Common Test Patterns

### Run Specific Test Class
```bash
pytest tests/unit/test_validators.py::TestFieldValidator -v
```

### Run Specific Test Method
```bash
pytest tests/unit/test_validators.py::TestFieldValidator::test_validate_not_null -v
```

### Run Tests with Pattern
```bash
pytest tests/unit/ -k "validator" -v
```

### Stop on First Failure
```bash
pytest tests/unit/ -x
```

### Show Local Variables on Failure
```bash
pytest tests/unit/ -l
```

### Verbose Output with Print Statements
```bash
pytest tests/unit/ -v -s
```

### Coverage Report
```bash
pytest tests/unit/ --cov=. --cov-report=html
open htmlcov/index.html  # View in browser
```

## Environment Variables

### Unit Tests
No environment variables required - uses mocks

### Integration Tests (Windows)
```powershell
$env:USE_DOCKER_ORACLE = "true"
$env:ORACLE_CONTAINER_NAME = "oracle-test"
$env:HADOOP_HOME = "C:\hadoop"  # Required for Spark on Windows
```

### Integration Tests (Linux/WSL)
```bash
export USE_DOCKER_ORACLE=true
export ORACLE_CONTAINER_NAME=oracle-test
# No HADOOP_HOME needed on Linux!
```

## Troubleshooting

### Unit Tests Failing
- Ensure virtual environment is activated
- Check Python version (3.11 recommended)
- Verify all dependencies installed: `pip list`
- Java 17 must be available: `java -version`

### Integration Tests Skipping
- Docker must be running
- Set `USE_DOCKER_ORACLE=true`
- Check Docker is accessible: `docker ps`

### Integration Tests Hanging
- Check Docker container status: `docker ps -a`
- View container logs: `docker logs oracle-test`
- Ensure port 1521 is not in use

### Windows: Spark HADOOP_HOME Error
```
FileNotFoundException: HADOOP_HOME and hadoop.home.dir are unset
```
**Solution 1:** Set HADOOP_HOME in PowerShell script (already done in run-integration-tests.ps1)
**Solution 2:** Use WSL/Linux (no Hadoop needed) - See [docs/LINUX_SETUP.md](LINUX_SETUP.md)

### Import Errors
```
ModuleNotFoundError: No module named 'extractors'
```
**Solution:** Check tests/integration/conftest.py has correct sys.path setup

### Docker Permission Denied (Linux)
```
permission denied while trying to connect to the Docker daemon
```
**Solution:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

## Performance Tips

### Keep Docker Container Running
Don't set `ORACLE_AUTO_CLEANUP=true` - container reuse speeds up tests from 2-5 min to 30-60 sec

### Run Tests in Parallel
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run with 4 workers
pytest tests/unit/ -n 4
```

### Use Local Filesystem (WSL)
Clone project to WSL filesystem (`~/projects/`) instead of Windows (`/mnt/c/...`) for better performance

### Increase WSL Memory
Edit `C:\Users\<username>\.wslconfig`:
```ini
[wsl2]
memory=8GB
processors=4
```

## Test Results Summary

| Test Suite | Count | Duration (1st run) | Duration (cached) |
|------------|-------|-------------------|-------------------|
| **Unit Tests** | 67 | ~5-10 minutes | ~5-10 minutes |
| - Extractors | 24 | - | - |
| - Loaders | 22 | - | - |
| - Transformers | 11 | - | - |
| - Validators | 10 | - | - |
| **Integration Tests** | 19 | ~2-5 minutes | ~30-60 seconds |

**Total:** 86 tests covering extraction, transformation, validation, and loading

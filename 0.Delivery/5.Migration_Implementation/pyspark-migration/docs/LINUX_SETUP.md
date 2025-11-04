# Linux/WSL Setup Guide

This guide covers setting up the PySpark migration framework on Linux or Windows Subsystem for Linux (WSL).

## Prerequisites

### 1. Linux/WSL Environment

**For WSL (Windows users):**
```bash
# Install WSL2 (PowerShell as Administrator)
wsl --install

# Or install specific distribution
wsl --install -d Ubuntu-22.04

# Start WSL
wsl
```

### 2. System Dependencies

```bash
# Update package list
sudo apt update

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip

# Install Java (required for PySpark)
sudo apt install openjdk-17-jdk

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
# Or run: newgrp docker
```

### 3. Verify Installation

```bash
# Check Python version
python3.11 --version  # Should show 3.11.x

# Check Java version
java -version  # Should show OpenJDK 17.x

# Check Docker
docker --version
docker ps  # Should not show permission errors
```

## Project Setup

### 1. Navigate to Project Directory

```bash
# If using WSL, access Windows files via /mnt/c
cd /mnt/c/Users/rossboast/projects/ghcp-data-migration-prompts/0.Delivery/5.Migration_Implementation/pyspark-migration

# Or if project is in Linux filesystem
cd ~/projects/pyspark-migration
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Python Dependencies

```bash
# Install requirements
pip install -r requirements.txt

# Verify PySpark installation
python -c "import pyspark; print(f'PySpark {pyspark.__version__} installed')"
```

### 4. Configure Environment

```bash
# Copy Linux environment template
cp .env.linux .env

# Edit if needed (optional)
nano .env
```

## Running Tests

### Unit Tests

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_validators.py -v

# Run with coverage
pytest tests/unit/ --cov=. --cov-report=html
```

### Integration Tests

**Option 1: Using the helper script (recommended)**
```bash
# Make script executable
chmod +x run-integration-tests.sh

# Run integration tests
./run-integration-tests.sh
```

**Option 2: Manual execution**
```bash
# Set environment variables
export USE_DOCKER_ORACLE=true
export ORACLE_CONTAINER_NAME=oracle-test

# Run tests
pytest tests/integration/ -v

# Or run specific test
pytest tests/integration/test_oracle_integration.py::TestOracleConnectionIntegration -v
```

### Expected Test Results

**Unit Tests:**
```
67 passed in ~5-10 minutes
```

**Integration Tests (first run):**
```
19 passed in ~2-5 minutes
(Includes Docker image download and container startup)
```

**Integration Tests (subsequent runs):**
```
19 passed in ~30-60 seconds
(Container reused, much faster)
```

## Docker Oracle Management

### Container Lifecycle

```bash
# Check container status
docker ps -a | grep oracle-test

# View container logs
docker logs oracle-test

# Start stopped container
docker start oracle-test

# Stop container
docker stop oracle-test

# Remove container (will be recreated on next test run)
docker rm -f oracle-test
```

### Troubleshooting Docker

**Permission denied:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker
```

**Container won't start:**
```bash
# Check port 1521 is not in use
sudo netstat -tulpn | grep 1521

# Remove and recreate container
docker rm -f oracle-test
./run-integration-tests.sh
```

**Image pull fails:**
```bash
# Check Docker Hub connectivity
docker pull hello-world

# Pull Oracle image manually
docker pull gvenzl/oracle-free:23-slim-faststart
```

## Advantages of Linux/WSL

### 1. No Hadoop/Winutils Issues
- Spark works natively on Linux
- No need to download winutils.exe
- No HADOOP_HOME configuration required

### 2. Better Performance
- Native Docker support (no VM overhead)
- Faster file I/O
- Better resource utilization

### 3. Production Parity
- Same environment as production deployments
- Identical behavior to CI/CD pipelines
- No Windows-specific quirks

### 4. Easier Setup
- Simple package installation via apt
- No PATH configuration issues
- Standard Unix tools available

## WSL-Specific Tips

### Accessing Windows Files

```bash
# Windows drives are mounted under /mnt
cd /mnt/c/Users/username/projects

# Copy files from Windows to WSL
cp /mnt/c/Users/username/file.txt ~/

# Edit Windows files from WSL
code /mnt/c/Users/username/project/file.py
```

### File Permissions

```bash
# Make scripts executable
chmod +x *.sh

# Fix line endings if file was created in Windows
dos2unix run-integration-tests.sh
```

### Memory Configuration

```bash
# Create/edit .wslconfig in Windows user directory
# C:\Users\username\.wslconfig

[wsl2]
memory=8GB
processors=4
swap=2GB
```

### VS Code Integration

```bash
# Install VS Code WSL extension
code --install-extension ms-vscode-remote.remote-wsl

# Open project in VS Code from WSL
cd project-directory
code .
```

## Common Issues and Solutions

### Issue: "Python not found"
```bash
# Install Python 3.11
sudo apt install python3.11 python3.11-venv

# Create symlink if needed
sudo ln -s /usr/bin/python3.11 /usr/bin/python
```

### Issue: "java: command not found"
```bash
# Install OpenJDK 17
sudo apt install openjdk-17-jdk

# Verify installation
java -version
```

### Issue: Docker commands fail
```bash
# Start Docker service
sudo service docker start

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Issue: Tests hang during Spark initialization
```bash
# Check available memory
free -h

# Reduce Spark memory if needed (edit pytest.ini)
spark.driver.memory=2g
spark.executor.memory=2g
```

### Issue: Port 1521 already in use
```bash
# Find process using port
sudo netstat -tulpn | grep 1521

# Kill the process or stop conflicting container
docker stop oracle-test
```

## Performance Optimization

### 1. Keep Containers Running
```bash
# Don't set ORACLE_AUTO_CLEANUP=true
export ORACLE_AUTO_CLEANUP=false
```

### 2. Use Local File System
```bash
# Clone project to WSL filesystem (not /mnt/c)
cd ~
git clone <repo-url>
cd pyspark-migration
```

### 3. Increase WSL Resources
Edit `C:\Users\username\.wslconfig`:
```ini
[wsl2]
memory=8GB
processors=4
```

### 4. Enable BuildKit for Docker
```bash
export DOCKER_BUILDKIT=1
```

## Next Steps

1. ✅ Run unit tests to verify setup
2. ✅ Run integration tests with Docker Oracle
3. ✅ Check test coverage
4. 🔄 Set up CI/CD pipeline (GitHub Actions)
5. 🔄 Configure production Cosmos DB connection

## Resources

- [WSL Documentation](https://docs.microsoft.com/en-us/windows/wsl/)
- [Docker on Linux](https://docs.docker.com/engine/install/)
- [PySpark Documentation](https://spark.apache.org/docs/latest/api/python/)
- [Oracle Docker Images](https://github.com/gvenzl/oci-oracle-free)
- [pytest Documentation](https://docs.pytest.org/)

## Support

For issues specific to this project:
1. Check test output for detailed error messages
2. Verify Docker container logs: `docker logs oracle-test`
3. Ensure all prerequisites are installed and up to date
4. Try running in a clean virtual environment

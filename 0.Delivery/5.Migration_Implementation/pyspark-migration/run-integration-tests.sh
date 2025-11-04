#!/bin/bash
# Run Integration Tests with Docker Oracle (Linux/WSL)
# This script automatically manages the Oracle container

echo "🧪 Oracle Integration Tests with Docker"
echo "========================================"

# Check Docker is running
echo ""
echo "📦 Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "   Install Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! docker ps &> /dev/null; then
    echo "❌ Docker is not running or not accessible!"
    echo "   Start Docker daemon or add user to docker group:"
    echo "   sudo usermod -aG docker $USER"
    exit 1
fi

DOCKER_VERSION=$(docker --version)
echo "✅ Docker is available: $DOCKER_VERSION"

# Set environment for Docker Oracle
echo ""
echo "🔧 Configuring environment..."
export USE_DOCKER_ORACLE=true
export ORACLE_AUTO_CLEANUP=false  # Keep container for faster re-runs
export ORACLE_DOCKER_IMAGE=gvenzl/oracle-free:23-slim-faststart
export ORACLE_CONTAINER_NAME=oracle-test
export ORACLE_PORT=1521

echo "✅ Environment configured:"
echo "   USE_DOCKER_ORACLE = true"
echo "   Container: $ORACLE_CONTAINER_NAME"
echo "   Port: $ORACLE_PORT"
echo "   Image: $ORACLE_DOCKER_IMAGE"

# Check/Activate virtual environment
echo ""
echo "🐍 Checking Python environment..."
if [ -d ".venv-wsl" ]; then
    echo "✅ Activating WSL virtual environment (.venv-wsl)"
    source .venv-wsl/bin/activate
elif [ -d ".venv" ]; then
    echo "⚠️  Found .venv (Windows). Using .venv-wsl instead for WSL."
    echo "   Run ./wsl-setup.sh to create .venv-wsl"
    exit 1
else
    echo "❌ No virtual environment found!"
    echo "   Run ./wsl-setup.sh to set up environment"
    exit 1
fi

# Check if container already exists
echo ""
EXISTING_CONTAINER=$(docker ps -a --filter "name=$ORACLE_CONTAINER_NAME" --format "{{.Names}}")
if [ ! -z "$EXISTING_CONTAINER" ]; then
    echo "📦 Container '$ORACLE_CONTAINER_NAME' already exists"
    CONTAINER_STATE=$(docker ps --filter "name=$ORACLE_CONTAINER_NAME" --format "{{.State}}")
    if [ "$CONTAINER_STATE" = "running" ]; then
        echo "✅ Container is running"
    else
        echo "⚠️  Container is stopped, starting..."
        docker start $ORACLE_CONTAINER_NAME
    fi
else
    echo "📦 Container will be created automatically by pytest"
    echo "   First run will take 1-2 minutes (image download + startup)"
    echo "   Subsequent runs will be much faster (~30 seconds)"
fi

# Run integration tests
echo ""
echo "🧪 Running integration tests..."
echo "========================================"
pytest tests/integration/ -v

# Show results
echo ""
echo "========================================"
if [ $? -eq 0 ]; then
    echo "✅ Integration tests completed successfully!"
else
    echo "❌ Integration tests failed"
    echo "   Check logs above for details"
fi

# Show container status
echo ""
echo "📊 Post-test container status:"
docker ps -a --filter "name=$ORACLE_CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "💡 Container is still running for faster re-runs"
echo "   To stop: docker stop $ORACLE_CONTAINER_NAME"
echo "   To remove: docker rm -f $ORACLE_CONTAINER_NAME"

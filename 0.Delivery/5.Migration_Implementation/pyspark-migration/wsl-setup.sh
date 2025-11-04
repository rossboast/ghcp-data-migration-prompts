#!/bin/bash
# Quick start script for WSL integration test setup
# Run this from WSL terminal

echo "🚀 WSL Integration Test Quick Start"
echo "===================================="

# Navigate to project
PROJECT_PATH="/mnt/c/Users/rossboast/projects/ghcp-data-migration-prompts/0.Delivery/5.Migration_Implementation/pyspark-migration"

echo ""
echo "📂 Navigating to project..."
cd "$PROJECT_PATH" || {
    echo "❌ Could not find project directory"
    echo "   Expected: $PROJECT_PATH"
    exit 1
}
echo "✅ Current directory: $(pwd)"

# Check Python
echo ""
echo "🐍 Checking Python..."
if command -v python3.11 &> /dev/null; then
    PYTHON_VERSION=$(python3.11 --version)
    echo "✅ $PYTHON_VERSION"
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION"
    PYTHON_CMD="python3"
else
    echo "❌ Python not found!"
    echo "   Install: sudo apt install python3.11"
    exit 1
fi

# Check Java
echo ""
echo "☕ Checking Java..."
if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1)
    echo "✅ $JAVA_VERSION"
else
    echo "⚠️  Java not found (required for PySpark)"
    echo "   Install: sudo apt install openjdk-17-jdk"
    echo "   Continuing anyway..."
fi

# Check Docker
echo ""
echo "🐳 Checking Docker..."
if command -v docker &> /dev/null; then
    if docker ps &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        echo "✅ $DOCKER_VERSION"
    else
        echo "⚠️  Docker not accessible"
        echo "   Fix: sudo usermod -aG docker $USER"
        echo "   Then logout and login again"
    fi
else
    echo "❌ Docker not found!"
    echo "   Install: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    exit 1
fi

# Check/Create virtual environment
echo ""
echo "🔧 Setting up virtual environment..."
if [ ! -d ".venv-wsl" ]; then
    echo "Creating new WSL virtual environment (.venv-wsl)..."
    echo "   (Your Windows .venv will not be touched)"
    $PYTHON_CMD -m venv .venv-wsl
    echo "✅ WSL virtual environment created"
else
    echo "✅ WSL virtual environment exists"
fi

# Activate and install dependencies
echo ""
echo "📦 Activating environment and checking dependencies..."
source .venv-wsl/bin/activate

if ! python -c "import pyspark" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -q --upgrade pip
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
else
    echo "✅ Dependencies already installed"
fi

# Setup environment config
echo ""
echo "⚙️  Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "Creating .env from Linux template..."
    cp .env.linux .env
    echo "✅ .env created"
else
    echo "✅ .env exists"
fi

# Make script executable
echo ""
echo "🔐 Making integration test script executable..."
chmod +x run-integration-tests.sh
echo "✅ Script is executable"

# Summary
echo ""
echo "===================================="
echo "✅ Setup complete! You can now run:"
echo ""
echo "  # Run all integration tests"
echo "  ./run-integration-tests.sh"
echo ""
echo "  # Or manually:"
echo "  source .venv-wsl/bin/activate"
echo "  export USE_DOCKER_ORACLE=true"
echo "  pytest tests/integration/ -v"
echo ""
echo "  # Or run a single test:"
echo "  pytest tests/integration/test_oracle_integration.py::TestOracleConnectionIntegration::test_connection_validation -v"
echo ""
echo "===================================="

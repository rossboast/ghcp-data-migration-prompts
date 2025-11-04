# Run Integration Tests with Docker Oracle
# This script automatically manages the Oracle container

Write-Host "🧪 Oracle Integration Tests with Docker" -ForegroundColor Cyan
Write-Host "=" * 60

# Check Docker is running
Write-Host "`n📦 Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker is available: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running or not installed!" -ForegroundColor Red
    Write-Host "   Please start Docker Desktop and try again." -ForegroundColor Yellow
    exit 1
}

# Set environment for Docker Oracle
Write-Host "`n🔧 Configuring environment..." -ForegroundColor Yellow
$env:USE_DOCKER_ORACLE = "true"
$env:ORACLE_AUTO_CLEANUP = "false"  # Keep container for faster re-runs
$env:ORACLE_DOCKER_IMAGE = "gvenzl/oracle-free:23-slim-faststart"
$env:ORACLE_CONTAINER_NAME = "oracle-test"  # Use existing container
$env:ORACLE_PORT = "1521"

# Fix for Windows/Spark HADOOP_HOME issue
$env:HADOOP_HOME = "C:\hadoop"  # Dummy path to avoid Spark errors on Windows
if (-not (Test-Path $env:HADOOP_HOME)) {
    New-Item -ItemType Directory -Path $env:HADOOP_HOME -Force | Out-Null
}

Write-Host "✅ Environment configured:" -ForegroundColor Green
Write-Host "   USE_DOCKER_ORACLE = true"
Write-Host "   Container: $env:ORACLE_CONTAINER_NAME"
Write-Host "   Port: $env:ORACLE_PORT"
Write-Host "   Image: $env:ORACLE_DOCKER_IMAGE"

# Check if container already exists
$existingContainer = docker ps -a --filter "name=$env:ORACLE_CONTAINER_NAME" --format "{{.Names}}"
if ($existingContainer) {
    Write-Host "`n📦 Container '$env:ORACLE_CONTAINER_NAME' already exists" -ForegroundColor Cyan
    $containerState = docker ps --filter "name=$env:ORACLE_CONTAINER_NAME" --format "{{.State}}"
    if ($containerState -eq "running") {
        Write-Host "✅ Container is running" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Container is stopped, starting..." -ForegroundColor Yellow
        docker start $env:ORACLE_CONTAINER_NAME
        Write-Host "✅ Container started" -ForegroundColor Green
    }
} else {
    Write-Host "`n📦 Container will be created automatically by pytest" -ForegroundColor Cyan
    Write-Host "   First run will take 1-2 minutes (image download + startup)" -ForegroundColor Yellow
    Write-Host "   Subsequent runs will be much faster (~30 seconds)" -ForegroundColor Yellow
}

# Run pytest
Write-Host "`n🧪 Running integration tests..." -ForegroundColor Yellow
Write-Host "=" * 60
pytest tests/integration/test_oracle_integration.py -v $args

$exitCode = $LASTEXITCODE

# Show container status
Write-Host "`n📊 Post-test container status:" -ForegroundColor Cyan
$containerStatus = docker ps --filter "name=$env:ORACLE_CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
if ($containerStatus) {
    Write-Host $containerStatus
    Write-Host "`n💡 Container is still running for faster re-runs" -ForegroundColor Yellow
    Write-Host "   To stop: docker stop $env:ORACLE_CONTAINER_NAME" -ForegroundColor Yellow
    Write-Host "   To remove: docker rm -f $env:ORACLE_CONTAINER_NAME" -ForegroundColor Yellow
} else {
    Write-Host "   No container running" -ForegroundColor Gray
}

Write-Host ""
exit $exitCode

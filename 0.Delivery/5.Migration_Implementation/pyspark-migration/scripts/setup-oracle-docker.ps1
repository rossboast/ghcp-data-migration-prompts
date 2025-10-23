<#
.SYNOPSIS
    Automated Oracle Docker setup script for Windows

.DESCRIPTION
    Sets up Oracle Database 23ai Free using Docker with HR schema for integration testing.
    Can run all steps automatically or individual steps for troubleshooting.

.PARAMETER Step
    Specific step to run: pull, start, wait, schema, test, all, cleanup
    Default: all

.PARAMETER ContainerName
    Name for the Oracle container
    Default: oracle23ai

.PARAMETER Password
    Password for ORACLE_PASSWORD (SYS/SYSTEM)
    Default: OracleTest123

.PARAMETER AppUser
    Application user to create (HR schema owner)
    Default: hr

.PARAMETER AppPassword
    Password for application user
    Default: hr

.PARAMETER Port
    Port to expose Oracle listener
    Default: 1521

.EXAMPLE
    .\setup-oracle-docker.ps1
    Runs all setup steps automatically

.EXAMPLE
    .\setup-oracle-docker.ps1 -Step pull
    Only pulls the Docker image

.EXAMPLE
    .\setup-oracle-docker.ps1 -Step cleanup
    Removes Oracle container and volume

.NOTES
    Author: Migration Framework Team
    Requires: Docker Desktop for Windows
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('pull', 'start', 'wait', 'schema', 'test', 'all', 'cleanup', 'status')]
    [string]$Step = 'all',
    
    [Parameter(Mandatory=$false)]
    [string]$ContainerName = 'oracle23ai',
    
    [Parameter(Mandatory=$false)]
    [string]$Password = 'OracleTest123',
    
    [Parameter(Mandatory=$false)]
    [string]$AppUser = 'hr',
    
    [Parameter(Mandatory=$false)]
    [string]$AppPassword = 'hr',
    
    [Parameter(Mandatory=$false)]
    [int]$Port = 1521
)

# Configuration
$ImageName = 'gvenzl/oracle-free:23-slim'
$ServiceName = 'FREEPDB1'

# Colors for output
$ColorSuccess = 'Green'
$ColorError = 'Red'
$ColorInfo = 'Cyan'
$ColorWarning = 'Yellow'

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor $ColorInfo
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $ColorSuccess
}

function Write-Failure {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $ColorError
}

function Write-Warning-Message {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $ColorWarning
}

function Test-Docker {
    Write-Step "Checking Docker installation..."
    
    try {
        $dockerVersion = docker --version
        Write-Success "Docker is installed: $dockerVersion"
        return $true
    }
    catch {
        Write-Failure "Docker is not installed or not running"
        Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -ForegroundColor $ColorWarning
        return $false
    }
}

function Pull-OracleImage {
    Write-Step "Pulling Oracle Docker image..."
    Write-Host "This may take several minutes (image is ~2.5GB)" -ForegroundColor $ColorWarning
    
    docker pull $ImageName
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Oracle image pulled successfully"
        return $true
    }
    else {
        Write-Failure "Failed to pull Oracle image"
        return $false
    }
}

function Start-OracleContainer {
    Write-Step "Starting Oracle container..."
    
    # Check if container already exists
    $existingContainer = docker ps -a --filter "name=$ContainerName" --format "{{.Names}}"
    
    if ($existingContainer -eq $ContainerName) {
        Write-Warning-Message "Container '$ContainerName' already exists"
        
        # Check if running
        $runningContainer = docker ps --filter "name=$ContainerName" --format "{{.Names}}"
        
        if ($runningContainer -eq $ContainerName) {
            Write-Host "Container is already running" -ForegroundColor $ColorInfo
            return $true
        }
        else {
            Write-Host "Starting existing container..." -ForegroundColor $ColorInfo
            docker start $ContainerName
            
            if ($LASTEXITCODE -eq 0) {
                Write-Success "Container started"
                return $true
            }
            else {
                Write-Failure "Failed to start container"
                return $false
            }
        }
    }
    
    # Create new container
    Write-Host "Creating new Oracle container..." -ForegroundColor $ColorInfo
    
    docker run -d `
        --name $ContainerName `
        -p "${Port}:1521" `
        -e ORACLE_PASSWORD=$Password `
        -e APP_USER=$AppUser `
        -e APP_USER_PASSWORD=$AppPassword `
        --health-cmd="healthcheck.sh" `
        --health-interval=30s `
        --health-timeout=10s `
        --health-retries=5 `
        $ImageName
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Oracle container started successfully"
        Write-Host "Container name: $ContainerName" -ForegroundColor $ColorInfo
        Write-Host "Port: $Port" -ForegroundColor $ColorInfo
        return $true
    }
    else {
        Write-Failure "Failed to start Oracle container"
        return $false
    }
}

function Wait-OracleReady {
    Write-Step "Waiting for Oracle to be ready..."
    Write-Host "This typically takes 1-2 minutes" -ForegroundColor $ColorWarning
    
    $maxAttempts = 30
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        $attempt++
        
        # Check if container is still running
        $running = docker ps --filter "name=$ContainerName" --format "{{.Names}}"
        if ($running -ne $ContainerName) {
            Write-Failure "Container stopped unexpectedly"
            Write-Host "Check logs with: docker logs $ContainerName" -ForegroundColor $ColorWarning
            return $false
        }
        
        # Check health status
        $healthStatus = docker inspect --format='{{.State.Health.Status}}' $ContainerName 2>$null
        
        if ($healthStatus -eq 'healthy') {
            Write-Success "Oracle is ready!"
            return $true
        }
        
        Write-Host "Waiting... ($attempt/$maxAttempts) Status: $healthStatus" -ForegroundColor $ColorInfo
        Start-Sleep -Seconds 10
    }
    
    Write-Failure "Oracle did not become ready within timeout"
    Write-Host "Check logs with: docker logs $ContainerName" -ForegroundColor $ColorWarning
    return $false
}

function Test-HRSchema {
    Write-Step "Verifying HR schema..."
    
    # Test connection
    Write-Host "Testing connection..." -ForegroundColor $ColorInfo
    $connectionTest = docker exec -i $ContainerName sqlplus -S $AppUser/$AppPassword@//localhost:1521/$ServiceName '<<<' "SELECT 'Connected' as status FROM dual; EXIT;"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "Could not connect to database"
        return $false
    }
    
    Write-Success "Connection successful"
    
    # Check for HR tables
    Write-Host "Checking for HR tables..." -ForegroundColor $ColorInfo
    
    $tableCheck = @"
SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF
SELECT table_name FROM user_tables ORDER BY table_name;
EXIT;
"@
    
    $tables = $tableCheck | docker exec -i $ContainerName sqlplus -S $AppUser/$AppPassword@//localhost:1521/$ServiceName
    
    $expectedTables = @('COUNTRIES', 'DEPARTMENTS', 'EMPLOYEES', 'JOBS', 'JOB_HISTORY', 'LOCATIONS', 'REGIONS')
    $foundTables = $tables -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
    
    $missingTables = $expectedTables | Where-Object { $foundTables -notcontains $_ }
    
    if ($missingTables.Count -eq 0) {
        Write-Success "All HR tables found"
        
        # Show row counts
        Write-Host "`nRow counts:" -ForegroundColor $ColorInfo
        
        $countQuery = @"
SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF
SELECT 'REGIONS: ' || COUNT(*) FROM regions;
SELECT 'COUNTRIES: ' || COUNT(*) FROM countries;
SELECT 'LOCATIONS: ' || COUNT(*) FROM locations;
SELECT 'DEPARTMENTS: ' || COUNT(*) FROM departments;
SELECT 'JOBS: ' || COUNT(*) FROM jobs;
SELECT 'EMPLOYEES: ' || COUNT(*) FROM employees;
SELECT 'JOB_HISTORY: ' || COUNT(*) FROM job_history;
EXIT;
"@
        
        $counts = $countQuery | docker exec -i $ContainerName sqlplus -S $AppUser/$AppPassword@//localhost:1521/$ServiceName
        $counts -split "`n" | ForEach-Object {
            if ($_ -ne '') {
                Write-Host "  $_" -ForegroundColor $ColorSuccess
            }
        }
        
        return $true
    }
    else {
        Write-Warning-Message "HR schema tables not found: $($missingTables -join ', ')"
        Write-Host "HR schema may need to be installed manually" -ForegroundColor $ColorWarning
        return $false
    }
}

function Show-Status {
    Write-Step "Oracle Container Status"
    
    $container = docker ps -a --filter "name=$ContainerName" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    if ($container) {
        Write-Host $container -ForegroundColor $ColorInfo
        
        $healthStatus = docker inspect --format='{{.State.Health.Status}}' $ContainerName 2>$null
        if ($healthStatus) {
            Write-Host "`nHealth Status: $healthStatus" -ForegroundColor $(if ($healthStatus -eq 'healthy') { $ColorSuccess } else { $ColorWarning })
        }
    }
    else {
        Write-Warning-Message "Container '$ContainerName' not found"
    }
}

function Remove-OracleContainer {
    Write-Step "Cleaning up Oracle container..."
    
    $existingContainer = docker ps -a --filter "name=$ContainerName" --format "{{.Names}}"
    
    if ($existingContainer -eq $ContainerName) {
        Write-Host "Stopping container..." -ForegroundColor $ColorInfo
        docker stop $ContainerName | Out-Null
        
        Write-Host "Removing container..." -ForegroundColor $ColorInfo
        docker rm -v $ContainerName | Out-Null
        
        Write-Success "Container removed"
    }
    else {
        Write-Host "Container '$ContainerName' not found" -ForegroundColor $ColorInfo
    }
    
    # Check for volumes
    $volumes = docker volume ls --filter "name=oracle" --format "{{.Name}}"
    if ($volumes) {
        Write-Host "`nOracle volumes found:" -ForegroundColor $ColorInfo
        $volumes | ForEach-Object { Write-Host "  $_" -ForegroundColor $ColorWarning }
        
        $removeVolumes = Read-Host "`nRemove volumes? (y/n)"
        if ($removeVolumes -eq 'y') {
            $volumes | ForEach-Object {
                docker volume rm $_
                Write-Success "Removed volume: $_"
            }
        }
    }
}

function Show-ConnectionInfo {
    Write-Host "`n" -NoNewline
    Write-Host "=" * 70 -ForegroundColor $ColorSuccess
    Write-Host "Oracle Database Connection Information" -ForegroundColor $ColorSuccess
    Write-Host "=" * 70 -ForegroundColor $ColorSuccess
    Write-Host ""
    Write-Host "JDBC URL:      " -NoNewline -ForegroundColor $ColorInfo
    Write-Host "jdbc:oracle:thin:@//localhost:${Port}/${ServiceName}"
    Write-Host "Username:      " -NoNewline -ForegroundColor $ColorInfo
    Write-Host $AppUser
    Write-Host "Password:      " -NoNewline -ForegroundColor $ColorInfo
    Write-Host $AppPassword
    Write-Host "Service Name:  " -NoNewline -ForegroundColor $ColorInfo
    Write-Host $ServiceName
    Write-Host ""
    Write-Host "SQL*Plus:      " -NoNewline -ForegroundColor $ColorInfo
    Write-Host "docker exec -it $ContainerName sqlplus $AppUser/$AppPassword@//localhost:1521/$ServiceName"
    Write-Host ""
    Write-Host ".env Configuration:" -ForegroundColor $ColorInfo
    Write-Host "ORACLE_HOST=localhost"
    Write-Host "ORACLE_PORT=$Port"
    Write-Host "ORACLE_SERVICE_NAME=$ServiceName"
    Write-Host "ORACLE_USERNAME=$AppUser"
    Write-Host "ORACLE_PASSWORD=$AppPassword"
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor $ColorInfo
    Write-Host "1. Update your .env file with the above configuration"
    Write-Host "2. Set environment variable: `$env:RUN_INTEGRATION_TESTS='true'"
    Write-Host "3. Run integration tests: pytest tests/integration/ -v -m oracle"
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor $ColorSuccess
}

# Main execution
Write-Host "`n" -NoNewline
Write-Host "=" * 70 -ForegroundColor $ColorSuccess
Write-Host "Oracle Docker Setup for Integration Testing" -ForegroundColor $ColorSuccess
Write-Host "=" * 70 -ForegroundColor $ColorSuccess

# Check Docker first
if (-not (Test-Docker)) {
    exit 1
}

# Execute requested step(s)
switch ($Step) {
    'pull' {
        if (Pull-OracleImage) {
            Write-Host "`nImage pulled successfully!" -ForegroundColor $ColorSuccess
            Write-Host "Next step: .\setup-oracle-docker.ps1 -Step start" -ForegroundColor $ColorInfo
        }
    }
    
    'start' {
        if (Start-OracleContainer) {
            Write-Host "`nContainer started successfully!" -ForegroundColor $ColorSuccess
            Write-Host "Next step: .\setup-oracle-docker.ps1 -Step wait" -ForegroundColor $ColorInfo
        }
    }
    
    'wait' {
        if (Wait-OracleReady) {
            Write-Host "`nOracle is ready!" -ForegroundColor $ColorSuccess
            Write-Host "Next step: .\setup-oracle-docker.ps1 -Step schema" -ForegroundColor $ColorInfo
        }
    }
    
    'schema' {
        if (Test-HRSchema) {
            Write-Host "`nHR schema verified!" -ForegroundColor $ColorSuccess
            Show-ConnectionInfo
        }
    }
    
    'test' {
        if (Test-HRSchema) {
            Write-Host "`nTests passed!" -ForegroundColor $ColorSuccess
        }
    }
    
    'status' {
        Show-Status
    }
    
    'cleanup' {
        Remove-OracleContainer
    }
    
    'all' {
        $success = $true
        
        if (-not (Pull-OracleImage)) { $success = $false }
        if ($success -and -not (Start-OracleContainer)) { $success = $false }
        if ($success -and -not (Wait-OracleReady)) { $success = $false }
        if ($success -and -not (Test-HRSchema)) { $success = $false }
        
        if ($success) {
            Write-Host "`n" -NoNewline
            Write-Host "=" * 70 -ForegroundColor $ColorSuccess
            Write-Host "Setup Complete!" -ForegroundColor $ColorSuccess
            Write-Host "=" * 70 -ForegroundColor $ColorSuccess
            Show-ConnectionInfo
        }
        else {
            Write-Host "`n" -NoNewline
            Write-Failure "Setup failed. Check error messages above."
            Write-Host "For troubleshooting, see: docs/oracle-docker-setup.md" -ForegroundColor $ColorWarning
        }
    }
}

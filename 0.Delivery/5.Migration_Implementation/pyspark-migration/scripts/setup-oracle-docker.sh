#!/bin/bash

################################################################################
# Oracle Docker Setup Script for Linux/macOS
#
# Sets up Oracle Database 23ai Free using Docker with HR schema for integration
# testing. Can run all steps automatically or individual steps for troubleshooting.
#
# Usage:
#   ./setup-oracle-docker.sh [step]
#
# Steps:
#   pull    - Pull Oracle Docker image
#   start   - Start Oracle container
#   wait    - Wait for Oracle to be ready
#   schema  - Verify HR schema
#   test    - Test connection and schema
#   status  - Show container status
#   cleanup - Remove container and volumes
#   all     - Run all steps (default)
#
# Example:
#   ./setup-oracle-docker.sh           # Run all steps
#   ./setup-oracle-docker.sh pull      # Only pull image
#   ./setup-oracle-docker.sh cleanup   # Remove container
################################################################################

# Configuration
CONTAINER_NAME="${ORACLE_CONTAINER_NAME:-oracle23ai}"
IMAGE_NAME="gvenzl/oracle-free:23-slim"
ORACLE_PASSWORD="${ORACLE_PASSWORD:-OracleTest123}"
APP_USER="${APP_USER:-hr}"
APP_PASSWORD="${APP_PASSWORD:-hr}"
PORT="${ORACLE_PORT:-1521}"
SERVICE_NAME="FREEPDB1"

# Colors
COLOR_SUCCESS='\033[0;32m'
COLOR_ERROR='\033[0;31m'
COLOR_INFO='\033[0;36m'
COLOR_WARNING='\033[0;33m'
COLOR_RESET='\033[0m'

# Functions
print_step() {
    echo -e "\n${COLOR_INFO}==> $1${COLOR_RESET}"
}

print_success() {
    echo -e "${COLOR_SUCCESS}✓ $1${COLOR_RESET}"
}

print_error() {
    echo -e "${COLOR_ERROR}✗ $1${COLOR_RESET}"
}

print_warning() {
    echo -e "${COLOR_WARNING}⚠ $1${COLOR_RESET}"
}

print_header() {
    echo ""
    echo "======================================================================"
    echo "$1"
    echo "======================================================================"
}

check_docker() {
    print_step "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "Please install Docker from: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    if ! docker ps &> /dev/null; then
        print_error "Docker is not running or you don't have permission"
        echo "Try: sudo usermod -aG docker $USER && newgrp docker"
        return 1
    fi
    
    local docker_version=$(docker --version)
    print_success "Docker is installed: $docker_version"
    return 0
}

pull_image() {
    print_step "Pulling Oracle Docker image..."
    print_warning "This may take several minutes (image is ~2.5GB)"
    
    if docker pull "$IMAGE_NAME"; then
        print_success "Oracle image pulled successfully"
        return 0
    else
        print_error "Failed to pull Oracle image"
        return 1
    fi
}

start_container() {
    print_step "Starting Oracle container..."
    
    # Check if container already exists
    if docker ps -a --filter "name=$CONTAINER_NAME" --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
        print_warning "Container '$CONTAINER_NAME' already exists"
        
        # Check if running
        if docker ps --filter "name=$CONTAINER_NAME" --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
            echo "Container is already running"
            return 0
        else
            echo "Starting existing container..."
            if docker start "$CONTAINER_NAME"; then
                print_success "Container started"
                return 0
            else
                print_error "Failed to start container"
                return 1
            fi
        fi
    fi
    
    # Create new container
    echo "Creating new Oracle container..."
    
    if docker run -d \
        --name "$CONTAINER_NAME" \
        -p "${PORT}:1521" \
        -e "ORACLE_PASSWORD=$ORACLE_PASSWORD" \
        -e "APP_USER=$APP_USER" \
        -e "APP_USER_PASSWORD=$APP_PASSWORD" \
        --health-cmd="healthcheck.sh" \
        --health-interval=30s \
        --health-timeout=10s \
        --health-retries=5 \
        "$IMAGE_NAME"; then
        
        print_success "Oracle container started successfully"
        echo "Container name: $CONTAINER_NAME"
        echo "Port: $PORT"
        return 0
    else
        print_error "Failed to start Oracle container"
        return 1
    fi
}

wait_oracle_ready() {
    print_step "Waiting for Oracle to be ready..."
    print_warning "This typically takes 1-2 minutes"
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        
        # Check if container is still running
        if ! docker ps --filter "name=$CONTAINER_NAME" --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
            print_error "Container stopped unexpectedly"
            echo "Check logs with: docker logs $CONTAINER_NAME"
            return 1
        fi
        
        # Check health status
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null)
        
        if [ "$health_status" = "healthy" ]; then
            print_success "Oracle is ready!"
            return 0
        fi
        
        echo "Waiting... ($attempt/$max_attempts) Status: $health_status"
        sleep 10
    done
    
    print_error "Oracle did not become ready within timeout"
    echo "Check logs with: docker logs $CONTAINER_NAME"
    return 1
}

test_hr_schema() {
    print_step "Verifying HR schema..."
    
    # Test connection
    echo "Testing connection..."
    if ! docker exec -i "$CONTAINER_NAME" sqlplus -S "$APP_USER/$APP_PASSWORD@//localhost:1521/$SERVICE_NAME" <<< "SELECT 'Connected' as status FROM dual; EXIT;" &> /dev/null; then
        print_error "Could not connect to database"
        return 1
    fi
    
    print_success "Connection successful"
    
    # Check for HR tables
    echo "Checking for HR tables..."
    
    local tables=$(docker exec -i "$CONTAINER_NAME" sqlplus -S "$APP_USER/$APP_PASSWORD@//localhost:1521/$SERVICE_NAME" <<EOF
SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF
SELECT table_name FROM user_tables ORDER BY table_name;
EXIT;
EOF
)
    
    local expected_tables=("COUNTRIES" "DEPARTMENTS" "EMPLOYEES" "JOBS" "JOB_HISTORY" "LOCATIONS" "REGIONS")
    local missing_tables=()
    
    for table in "${expected_tables[@]}"; do
        if ! echo "$tables" | grep -q "^$table$"; then
            missing_tables+=("$table")
        fi
    done
    
    if [ ${#missing_tables[@]} -eq 0 ]; then
        print_success "All HR tables found"
        
        # Show row counts
        echo -e "\n${COLOR_INFO}Row counts:${COLOR_RESET}"
        
        local counts=$(docker exec -i "$CONTAINER_NAME" sqlplus -S "$APP_USER/$APP_PASSWORD@//localhost:1521/$SERVICE_NAME" <<EOF
SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF
SELECT 'REGIONS: ' || COUNT(*) FROM regions;
SELECT 'COUNTRIES: ' || COUNT(*) FROM countries;
SELECT 'LOCATIONS: ' || COUNT(*) FROM locations;
SELECT 'DEPARTMENTS: ' || COUNT(*) FROM departments;
SELECT 'JOBS: ' || COUNT(*) FROM jobs;
SELECT 'EMPLOYEES: ' || COUNT(*) FROM employees;
SELECT 'JOB_HISTORY: ' || COUNT(*) FROM job_history;
EXIT;
EOF
)
        
        echo "$counts" | while read -r line; do
            [ -n "$line" ] && echo -e "  ${COLOR_SUCCESS}$line${COLOR_RESET}"
        done
        
        return 0
    else
        print_warning "HR schema tables not found: ${missing_tables[*]}"
        echo "HR schema may need to be installed manually"
        return 1
    fi
}

show_status() {
    print_step "Oracle Container Status"
    
    if docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "$CONTAINER_NAME"; then
        docker ps -a --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME" 2>/dev/null)
        if [ -n "$health_status" ]; then
            if [ "$health_status" = "healthy" ]; then
                echo -e "\nHealth Status: ${COLOR_SUCCESS}$health_status${COLOR_RESET}"
            else
                echo -e "\nHealth Status: ${COLOR_WARNING}$health_status${COLOR_RESET}"
            fi
        fi
    else
        print_warning "Container '$CONTAINER_NAME' not found"
    fi
}

cleanup() {
    print_step "Cleaning up Oracle container..."
    
    if docker ps -a --filter "name=$CONTAINER_NAME" --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
        echo "Stopping container..."
        docker stop "$CONTAINER_NAME" &> /dev/null
        
        echo "Removing container..."
        docker rm -v "$CONTAINER_NAME" &> /dev/null
        
        print_success "Container removed"
    else
        echo "Container '$CONTAINER_NAME' not found"
    fi
    
    # Check for volumes
    local volumes=$(docker volume ls --filter "name=oracle" --format "{{.Name}}")
    if [ -n "$volumes" ]; then
        echo -e "\n${COLOR_INFO}Oracle volumes found:${COLOR_RESET}"
        echo "$volumes" | while read -r volume; do
            echo -e "  ${COLOR_WARNING}$volume${COLOR_RESET}"
        done
        
        read -p "Remove volumes? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "$volumes" | while read -r volume; do
                docker volume rm "$volume" &> /dev/null
                print_success "Removed volume: $volume"
            done
        fi
    fi
}

show_connection_info() {
    echo ""
    echo "======================================================================"
    echo -e "${COLOR_SUCCESS}Oracle Database Connection Information${COLOR_RESET}"
    echo "======================================================================"
    echo ""
    echo -e "${COLOR_INFO}JDBC URL:${COLOR_RESET}      jdbc:oracle:thin:@//localhost:${PORT}/${SERVICE_NAME}"
    echo -e "${COLOR_INFO}Username:${COLOR_RESET}      $APP_USER"
    echo -e "${COLOR_INFO}Password:${COLOR_RESET}      $APP_PASSWORD"
    echo -e "${COLOR_INFO}Service Name:${COLOR_RESET}  $SERVICE_NAME"
    echo ""
    echo -e "${COLOR_INFO}SQL*Plus:${COLOR_RESET}      docker exec -it $CONTAINER_NAME sqlplus $APP_USER/$APP_PASSWORD@//localhost:1521/$SERVICE_NAME"
    echo ""
    echo -e "${COLOR_INFO}.env Configuration:${COLOR_RESET}"
    echo "ORACLE_HOST=localhost"
    echo "ORACLE_PORT=$PORT"
    echo "ORACLE_SERVICE_NAME=$SERVICE_NAME"
    echo "ORACLE_USERNAME=$APP_USER"
    echo "ORACLE_PASSWORD=$APP_PASSWORD"
    echo ""
    echo -e "${COLOR_INFO}Next Steps:${COLOR_RESET}"
    echo "1. Update your .env file with the above configuration"
    echo "2. Set environment variable: export RUN_INTEGRATION_TESTS=true"
    echo "3. Run integration tests: pytest tests/integration/ -v -m oracle"
    echo ""
    echo "======================================================================"
}

# Main execution
print_header "Oracle Docker Setup for Integration Testing"

# Check Docker first
if ! check_docker; then
    exit 1
fi

# Get step from command line argument
STEP="${1:-all}"

# Execute requested step(s)
case "$STEP" in
    pull)
        if pull_image; then
            echo -e "\n${COLOR_SUCCESS}Image pulled successfully!${COLOR_RESET}"
            echo "Next step: ./setup-oracle-docker.sh start"
        fi
        ;;
    
    start)
        if start_container; then
            echo -e "\n${COLOR_SUCCESS}Container started successfully!${COLOR_RESET}"
            echo "Next step: ./setup-oracle-docker.sh wait"
        fi
        ;;
    
    wait)
        if wait_oracle_ready; then
            echo -e "\n${COLOR_SUCCESS}Oracle is ready!${COLOR_RESET}"
            echo "Next step: ./setup-oracle-docker.sh schema"
        fi
        ;;
    
    schema)
        if test_hr_schema; then
            echo -e "\n${COLOR_SUCCESS}HR schema verified!${COLOR_RESET}"
            show_connection_info
        fi
        ;;
    
    test)
        if test_hr_schema; then
            echo -e "\n${COLOR_SUCCESS}Tests passed!${COLOR_RESET}"
        fi
        ;;
    
    status)
        show_status
        ;;
    
    cleanup)
        cleanup
        ;;
    
    all)
        success=true
        
        pull_image || success=false
        [ "$success" = true ] && start_container || success=false
        [ "$success" = true ] && wait_oracle_ready || success=false
        [ "$success" = true ] && test_hr_schema || success=false
        
        if [ "$success" = true ]; then
            echo ""
            echo "======================================================================"
            echo -e "${COLOR_SUCCESS}Setup Complete!${COLOR_RESET}"
            echo "======================================================================"
            show_connection_info
        else
            echo ""
            print_error "Setup failed. Check error messages above."
            echo "For troubleshooting, see: docs/oracle-docker-setup.md"
        fi
        ;;
    
    *)
        echo "Usage: $0 [step]"
        echo ""
        echo "Steps:"
        echo "  pull    - Pull Oracle Docker image"
        echo "  start   - Start Oracle container"
        echo "  wait    - Wait for Oracle to be ready"
        echo "  schema  - Verify HR schema"
        echo "  test    - Test connection and schema"
        echo "  status  - Show container status"
        echo "  cleanup - Remove container and volumes"
        echo "  all     - Run all steps (default)"
        echo ""
        echo "Example:"
        echo "  $0           # Run all steps"
        echo "  $0 pull      # Only pull image"
        echo "  $0 cleanup   # Remove container"
        exit 1
        ;;
esac

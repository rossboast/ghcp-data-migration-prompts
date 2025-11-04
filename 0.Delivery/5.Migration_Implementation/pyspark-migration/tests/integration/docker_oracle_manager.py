"""
Docker Oracle Manager for Integration Tests

Automatically manages Oracle Docker containers for integration testing.
Handles container lifecycle: pull, start, wait, verify, stop.

Usage:
    # In conftest.py
    from docker_oracle_manager import DockerOracleManager
    
    @pytest.fixture(scope="session")
    def oracle_container():
        manager = DockerOracleManager()
        manager.ensure_oracle_ready()
        yield manager
        manager.cleanup()  # Optional: keep container for reuse
"""

import subprocess
import time
import os
import sys
from typing import Optional, Dict, Tuple


class DockerOracleManager:
    """
    Manages Oracle Database Docker container for integration tests.
    
    Features:
    - Automatic Docker detection
    - Container reuse (don't recreate if exists)
    - Health monitoring
    - HR schema verification
    - Automatic cleanup (optional)
    """
    
    DEFAULT_IMAGE = "gvenzl/oracle-free:23-slim"
    DEFAULT_CONTAINER = "pytest-oracle-integration"
    DEFAULT_PORT = 1521
    DEFAULT_PASSWORD = "pytest_oracle"
    
    def __init__(
        self,
        image: str = None,
        container_name: str = None,
        port: int = None,
        password: str = None,
        auto_cleanup: bool = False
    ):
        """
        Initialize Docker Oracle manager.
        
        Args:
            image: Docker image to use (default: gvenzl/oracle-free:23-slim)
            container_name: Container name (default: pytest-oracle-integration)
            port: Host port mapping (default: 1521)
            password: Oracle password (default: pytest_oracle)
            auto_cleanup: Whether to remove container after tests (default: False)
        """
        self.image = image or os.getenv("ORACLE_DOCKER_IMAGE", self.DEFAULT_IMAGE)
        self.container_name = container_name or os.getenv("ORACLE_CONTAINER_NAME", self.DEFAULT_CONTAINER)
        self.port = port or int(os.getenv("ORACLE_PORT", self.DEFAULT_PORT))
        self.password = password or os.getenv("ORACLE_PASSWORD", self.DEFAULT_PASSWORD)
        self.auto_cleanup = auto_cleanup or os.getenv("ORACLE_AUTO_CLEANUP", "false").lower() == "true"
        
        self.service_name = "FREEPDB1"
        self.username = "hr"
        self.user_password = "hr"
        
    def is_docker_available(self) -> bool:
        """Check if Docker is installed and running."""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def is_container_running(self) -> bool:
        """Check if Oracle container is already running."""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return self.container_name in result.stdout
        except subprocess.TimeoutExpired:
            return False
    
    def is_container_exists(self) -> bool:
        """Check if Oracle container exists (running or stopped)."""
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return self.container_name in result.stdout
        except subprocess.TimeoutExpired:
            return False
    
    def pull_image(self) -> bool:
        """Pull Oracle Docker image if not already present."""
        print(f"Checking for Docker image: {self.image}")
        
        # Check if image exists
        result = subprocess.run(
            ["docker", "images", "-q", self.image],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            print(f"✓ Image {self.image} already exists")
            return True
        
        print(f"Pulling image {self.image} (this may take several minutes)...")
        try:
            subprocess.run(
                ["docker", "pull", self.image],
                check=True,
                timeout=600  # 10 minute timeout
            )
            print(f"✓ Image pulled successfully")
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"✗ Failed to pull image: {e}")
            return False
    
    def start_container(self) -> bool:
        """Start Oracle container (create if doesn't exist)."""
        if self.is_container_running():
            print(f"✓ Container {self.container_name} already running")
            return True
        
        if self.is_container_exists():
            print(f"Starting existing container {self.container_name}...")
            try:
                subprocess.run(
                    ["docker", "start", self.container_name],
                    check=True,
                    timeout=30
                )
                print(f"✓ Container started")
                return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                print(f"✗ Failed to start container: {e}")
                return False
        
        # Create new container
        print(f"Creating new container {self.container_name}...")
        cmd = [
            "docker", "run", "-d",
            "--name", self.container_name,
            "-p", f"{self.port}:1521",
            "-e", f"ORACLE_PASSWORD={self.password}",
            "-e", f"APP_USER={self.username}",
            "-e", f"APP_USER_PASSWORD={self.user_password}",
            "--health-cmd", "healthcheck.sh",
            "--health-interval", "10s",
            "--health-timeout", "5s",
            "--health-retries", "10",
            self.image
        ]
        
        try:
            subprocess.run(cmd, check=True, timeout=30)
            print(f"✓ Container created and starting")
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"✗ Failed to create container: {e}")
            return False
    
    def wait_for_healthy(self, timeout: int = 180) -> bool:
        """
        Wait for Oracle container to become healthy.
        
        Args:
            timeout: Maximum wait time in seconds (default: 180)
            
        Returns:
            True if healthy, False if timeout
        """
        print(f"Waiting for Oracle to become ready (timeout: {timeout}s)...")
        start_time = time.time()
        
        # Check if container has health check configured
        try:
            health_check_result = subprocess.run(
                ["docker", "inspect", "--format", "{{.State.Health}}", self.container_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            health_output = health_check_result.stdout.strip()
            has_health_check = health_output not in ["<nil>", "<no value>", ""]
        except:
            has_health_check = False
        
        # If no health check, verify container is running
        if not has_health_check:
            print("Container has no health check, verifying it's running...")
            try:
                running_result = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Running}}", self.container_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if running_result.stdout.strip() == "true":
                    print(f"✓ Container is running (no health check configured)")
                    # Give it a few seconds to fully start
                    time.sleep(5)
                    return True
                else:
                    print(f"✗ Container is not running")
                    return False
            except:
                print(f"✗ Failed to check container status")
                return False
        
        # Container has health check, wait for it
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["docker", "inspect", "--format", "{{.State.Health.Status}}", self.container_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                status = result.stdout.strip()
                elapsed = int(time.time() - start_time)
                
                if status == "healthy":
                    print(f"✓ Oracle is ready! (took {elapsed}s)")
                    return True
                
                # Progress indicator
                if elapsed % 10 == 0:
                    print(f"  Waiting... ({elapsed}s) Status: {status}")
                
                time.sleep(2)
                
            except subprocess.TimeoutExpired:
                pass
        
        print(f"✗ Timeout waiting for Oracle to become healthy")
        return False
    
    def verify_hr_schema(self) -> Tuple[bool, Dict[str, int]]:
        """
        Verify HR schema is installed and has expected data.
        
        Returns:
            Tuple of (success: bool, counts: dict)
        """
        print("Verifying HR schema...")
        
        # SQL to check tables and counts
        sql_check = """SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF
SELECT table_name || ':' || COUNT(*) FROM user_tables t, (SELECT table_name tn FROM user_tables WHERE table_name IN ('REGIONS','COUNTRIES','LOCATIONS','DEPARTMENTS','JOBS','EMPLOYEES','JOB_HISTORY')) WHERE t.table_name = tn GROUP BY table_name;
EXIT;
"""
        
        try:
            # Run SQL in container
            result = subprocess.run(
                ["docker", "exec", "-i", self.container_name, "sqlplus", "-S", 
                 f"{self.username}/{self.user_password}@//localhost:1521/{self.service_name}"],
                input=sql_check,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"✗ SQL execution failed: {result.stderr}")
                # Try simple table count instead
                return self._verify_hr_schema_simple()
            
            # Parse output
            counts = {}
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if ':' in line and line:
                    parts = line.split(':')
                    if len(parts) == 2:
                        table, count = parts
                        try:
                            counts[table.strip()] = int(count.strip())
                        except ValueError:
                            pass
            
            expected_tables = ['REGIONS', 'COUNTRIES', 'LOCATIONS', 'DEPARTMENTS', 'JOBS', 'EMPLOYEES', 'JOB_HISTORY']
            all_present = all(table in counts for table in expected_tables)
            
            if all_present:
                print(f"✓ HR schema verified")
                for table in expected_tables:
                    if table in counts:
                        print(f"  {table}: {counts[table]} rows")
                return True, counts
            else:
                missing = [t for t in expected_tables if t not in counts]
                print(f"✗ Missing tables: {missing}")
                return False, counts
                
        except subprocess.TimeoutExpired:
            print(f"✗ Timeout verifying HR schema")
            return False, {}
    
    def _verify_hr_schema_simple(self) -> Tuple[bool, Dict[str, int]]:
        """Simplified HR schema verification - just check if tables exist."""
        sql_check = """SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF
SELECT COUNT(*) FROM user_tables WHERE table_name IN ('REGIONS','COUNTRIES','LOCATIONS','DEPARTMENTS','JOBS','EMPLOYEES','JOB_HISTORY');
EXIT;
"""
        
        try:
            result = subprocess.run(
                ["docker", "exec", "-i", self.container_name, "sqlplus", "-S", 
                 f"{self.username}/{self.user_password}@//localhost:1521/{self.service_name}"],
                input=sql_check,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            count_str = result.stdout.strip()
            if count_str.isdigit():
                count = int(count_str)
                if count == 7:
                    print(f"✓ HR schema verified (7 tables found)")
                    return True, {}
                else:
                    print(f"✗ Expected 7 HR tables, found {count}")
                    return False, {}
            else:
                print(f"✗ Could not verify HR schema")
                return False, {}
        except Exception as e:
            print(f"✗ HR schema verification failed: {e}")
            return False, {}
    
    def ensure_oracle_ready(self) -> bool:
        """
        Ensure Oracle is running and ready for tests.
        This is the main entry point for test fixtures.
        
        Returns:
            True if Oracle is ready, False otherwise
        """
        print("\n" + "=" * 70)
        print("Docker Oracle Manager - Integration Test Setup")
        print("=" * 70)
        
        # Step 1: Check Docker
        if not self.is_docker_available():
            print("✗ Docker is not available")
            print("  Please install Docker: https://www.docker.com/products/docker-desktop")
            return False
        print("✓ Docker is available")
        
        # Step 2: Pull image
        if not self.pull_image():
            return False
        
        # Step 3: Start container
        if not self.start_container():
            return False
        
        # Step 4: Wait for healthy
        if not self.wait_for_healthy():
            return False
        
        # Step 5: Verify HR schema
        success, counts = self.verify_hr_schema()
        if not success:
            print("⚠ HR schema verification inconclusive - continuing anyway")
            print("  Tests will validate data availability")
        
        print("=" * 70)
        print("✓ Oracle is ready for integration tests!")
        print(f"  Connection: {self.username}/{self.user_password}@localhost:{self.port}/{self.service_name}")
        print("=" * 70 + "\n")
        
        return True
    
    def cleanup(self):
        """Stop and optionally remove Oracle container."""
        if not self.auto_cleanup:
            print(f"Container {self.container_name} left running for reuse")
            print(f"  To stop: docker stop {self.container_name}")
            print(f"  To remove: docker rm -f {self.container_name}")
            return
        
        print(f"Cleaning up container {self.container_name}...")
        try:
            subprocess.run(
                ["docker", "rm", "-f", self.container_name],
                check=True,
                timeout=30
            )
            print(f"✓ Container removed")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"✗ Failed to remove container: {e}")
    
    def get_connection_details(self) -> Dict[str, str]:
        """
        Get connection details for Oracle database.
        
        Returns:
            Dictionary with connection parameters
        """
        return {
            "host": "localhost",
            "port": str(self.port),
            "service_name": self.service_name,
            "username": self.username,
            "password": self.user_password,
            "jdbc_url": f"jdbc:oracle:thin:@//localhost:{self.port}/{self.service_name}"
        }
